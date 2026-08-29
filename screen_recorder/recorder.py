from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from mss import mss


class RecorderState(str, Enum):
    IDLE = "idle"
    STARTING = "starting"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPING = "stopping"
    FINISHED = "finished"
    ERROR = "error"


@dataclass(slots=True)
class RecorderConfig:
    output_dir: Path
    filename: str = "recording"
    fps: int = 30
    monitor_index: int = 1
    codec: str = "mp4v"
    prefer_lossless: bool = False


class ScreenRecorder:
    """Threaded screen capture engine.

    Capture is performed on a worker thread so the Tkinter UI remains responsive.
    """

    def __init__(
        self,
        config: RecorderConfig,
        on_state_change: Callable[[RecorderState], None] | None = None,
    ) -> None:
        self.config = config
        self.on_state_change = on_state_change

        self.state = RecorderState.IDLE
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._writer: cv2.VideoWriter | None = None
        self._error: Exception | None = None
        self._output_path: Path | None = None
        self._started_at = 0.0
        self._paused_total = 0.0
        self._pause_started = 0.0
        self._elapsed = 0.0
        self._lock = threading.Lock()

    @property
    def is_recording(self) -> bool:
        return self.state in {
            RecorderState.STARTING,
            RecorderState.RECORDING,
            RecorderState.PAUSED,
            RecorderState.STOPPING,
        }

    @property
    def elapsed_seconds(self) -> float:
        with self._lock:
            if self.state == RecorderState.PAUSED and self._pause_started:
                paused_now = time.monotonic() - self._pause_started
            else:
                paused_now = 0.0

            if not self._started_at:
                return 0.0

            return max(
                0.0,
                time.monotonic()
                - self._started_at
                - self._paused_total
                - paused_now,
            )

    @property
    def output_path(self) -> Path | None:
        return self._output_path

    def start(self) -> None:
        if self.is_recording:
            raise RuntimeError("A recording is already active.")

        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        self._stop_event.clear()
        self._pause_event.clear()
        self._error = None
        self._output_path = None
        self._paused_total = 0.0
        self._pause_started = 0.0
        self._elapsed = 0.0

        self._set_state(RecorderState.STARTING)
        self._thread = threading.Thread(
            target=self._capture_loop,
            name="screen-recorder",
            daemon=True,
        )
        self._thread.start()

    def pause(self) -> None:
        if self.state != RecorderState.RECORDING:
            return

        with self._lock:
            self._pause_started = time.monotonic()
            self._pause_event.set()
        self._set_state(RecorderState.PAUSED)

    def resume(self) -> None:
        if self.state != RecorderState.PAUSED:
            return

        with self._lock:
            if self._pause_started:
                self._paused_total += time.monotonic() - self._pause_started
            self._pause_started = 0.0
            self._pause_event.clear()

        self._set_state(RecorderState.RECORDING)

    def stop(self) -> Path:
        if not self.is_recording:
            raise RuntimeError("No active recording.")

        self._set_state(RecorderState.STOPPING)
        self._stop_event.set()
        self._pause_event.clear()

        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=15)

        if self._error:
            raise RuntimeError(f"Recording failed: {self._error}") from self._error

        if not self._output_path:
            raise RuntimeError("Recorder stopped without producing a video.")

        self._set_state(RecorderState.FINISHED)
        return self._output_path

    def _capture_loop(self) -> None:
        try:
            with mss() as sct:
                monitor = self._get_monitor(sct)
                width = int(monitor["width"])
                height = int(monitor["height"])

                output_path = self._build_output_path()
                self._output_path = output_path

                codec = self.config.codec
                if self.config.prefer_lossless and codec == "mp4v":
                    # FFV1 is generally lossless but is more appropriate in an AVI container.
                    # Keep MP4 output as the default for portability.
                    codec = "mp4v"

                fourcc = cv2.VideoWriter_fourcc(*codec)
                writer = cv2.VideoWriter(
                    str(output_path),
                    fourcc,
                    float(self.config.fps),
                    (width, height),
                )

                if not writer.isOpened():
                    raise RuntimeError(
                        f"OpenCV could not open the video writer using codec '{codec}'. "
                        "Try codec 'mp4v' or install an OpenCV build with FFmpeg support."
                    )

                self._writer = writer
                self._started_at = time.monotonic()
                self._set_state(RecorderState.RECORDING)

                frame_interval = 1.0 / self.config.fps
                next_frame = time.perf_counter()

                while not self._stop_event.is_set():
                    if self._pause_event.is_set():
                        time.sleep(0.05)
                        next_frame = time.perf_counter()
                        continue

                    screenshot = sct.grab(monitor)
                    frame = np.asarray(screenshot)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                    writer.write(frame)

                    next_frame += frame_interval
                    delay = next_frame - time.perf_counter()
                    if delay > 0:
                        time.sleep(delay)
                    else:
                        # If the encoder fell behind, reset the schedule instead of
                        # building an ever-growing sleep debt.
                        next_frame = time.perf_counter()

                writer.release()
                self._writer = None

        except Exception as exc:
            self._error = exc
            self._set_state(RecorderState.ERROR)
            if self._writer is not None:
                self._writer.release()
                self._writer = None

    def _get_monitor(self, sct: mss) -> dict:
        # MSS returns monitor 0 as the virtual desktop and 1..N as real monitors.
        index = self.config.monitor_index
        if index < 1 or index >= len(sct.monitors):
            raise ValueError(
                f"Monitor {index} is unavailable. "
                f"Detected {max(0, len(sct.monitors) - 1)} monitor(s)."
            )
        return sct.monitors[index]

    def _build_output_path(self) -> Path:
        raw_name = self.config.filename.strip() or "recording"
        safe_name = "".join(
            char if char.isalnum() or char in "-_." else "_"
            for char in raw_name
        )

        if not safe_name.lower().endswith(".mp4"):
            safe_name += ".mp4"

        candidate = self.config.output_dir / safe_name
        if not candidate.exists():
            return candidate

        stem = candidate.stem
        suffix = candidate.suffix
        counter = 1

        while True:
            candidate = self.config.output_dir / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def _set_state(self, state: RecorderState) -> None:
        self.state = state
        if self.on_state_change:
            self.on_state_change(state)
