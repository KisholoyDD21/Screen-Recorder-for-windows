from __future__ import annotations

import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .recorder import ScreenRecorder, RecorderConfig, RecorderState


class ScreenRecorderApp(tk.Tk):
    """Desktop GUI for the Python screen recorder."""

    def __init__(self) -> None:
        super().__init__()

        self.title("Python Screen Recorder")
        self.geometry("680x500")
        self.minsize(620, 450)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.output_dir = tk.StringVar(
            value=str(Path.home() / "Videos" / "PythonScreenRecorder")
        )
        self.filename = tk.StringVar(value="recording")
        self.fps = tk.IntVar(value=30)
        self.monitor = tk.IntVar(value=1)
        self.status = tk.StringVar(value="Ready")
        self.elapsed = tk.StringVar(value="00:00:00")
        self.resolution = tk.StringVar(value="Detecting...")
        self.codec = tk.StringVar(value="mp4v")
        self.use_lossless = tk.BooleanVar(value=False)

        self.recorder: ScreenRecorder | None = None
        self._build_style()
        self._build_ui()
        self._refresh_display_info()

        self.bind_all("<F9>", lambda _event: self._toggle_record())
        self.bind_all("<F10>", lambda _event: self._toggle_pause())
        self.bind_all("<F11>", lambda _event: self._stop_recording())

    def _build_style(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("Title.TLabel", font=("TkDefaultFont", 20, "bold"))
        style.configure("Muted.TLabel", foreground="#555")
        style.configure("Action.TButton", padding=(14, 8))
        style.configure("Record.TButton", padding=(14, 8))

    def _build_ui(self) -> None:
        container = ttk.Frame(self, padding=24)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="Python Screen Recorder",
            style="Title.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            container,
            text="Intermediate desktop recorder built with Python + MSS + OpenCV",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 20))

        # Output section
        output_box = ttk.LabelFrame(container, text="Output", padding=14)
        output_box.pack(fill="x", pady=(0, 12))

        ttk.Label(output_box, text="Folder").grid(row=0, column=0, sticky="w")
        ttk.Entry(output_box, textvariable=self.output_dir).grid(
            row=0, column=1, sticky="ew", padx=8
        )
        ttk.Button(
            output_box, text="Browse", command=self._choose_directory
        ).grid(row=0, column=2)
        output_box.columnconfigure(1, weight=1)

        ttk.Label(output_box, text="File name").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(output_box, textvariable=self.filename).grid(
            row=1, column=1, sticky="ew", padx=8, pady=(10, 0)
        )
        ttk.Label(output_box, text=".mp4").grid(row=1, column=2, pady=(10, 0))

        # Recording section
        settings_box = ttk.LabelFrame(container, text="Recording settings", padding=14)
        settings_box.pack(fill="x", pady=(0, 12))

        ttk.Label(settings_box, text="Monitor").grid(row=0, column=0, sticky="w")
        monitor_combo = ttk.Combobox(
            settings_box,
            textvariable=self.monitor,
            values=[1, 2, 3],
            width=8,
            state="readonly",
        )
        monitor_combo.grid(row=0, column=1, sticky="w", padx=8)

        ttk.Label(settings_box, text="FPS").grid(row=0, column=2, sticky="w", padx=(30, 0))
        ttk.Combobox(
            settings_box,
            textvariable=self.fps,
            values=[15, 24, 30, 45, 60],
            width=8,
            state="readonly",
        ).grid(row=0, column=3, sticky="w", padx=8)

        ttk.Label(settings_box, text="Codec").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Combobox(
            settings_box,
            textvariable=self.codec,
            values=["mp4v", "avc1"],
            width=8,
            state="readonly",
        ).grid(row=1, column=1, sticky="w", padx=8, pady=(10, 0))

        ttk.Checkbutton(
            settings_box,
            text="Prefer lossless frames (larger files)",
            variable=self.use_lossless,
        ).grid(row=1, column=2, columnspan=2, sticky="w", padx=(30, 0), pady=(10, 0))

        # Status section
        status_box = ttk.LabelFrame(container, text="Status", padding=14)
        status_box.pack(fill="x", pady=(0, 16))

        ttk.Label(status_box, textvariable=self.status).pack(anchor="w")
        ttk.Label(
            status_box,
            textvariable=self.elapsed,
            font=("TkDefaultFont", 24, "bold"),
        ).pack(anchor="w", pady=(5, 0))
        ttk.Label(status_box, textvariable=self.resolution, style="Muted.TLabel").pack(anchor="w")

        # Buttons
        button_row = ttk.Frame(container)
        button_row.pack(fill="x")

        self.record_button = ttk.Button(
            button_row,
            text="●  Start Recording   [F9]",
            command=self._toggle_record,
            style="Record.TButton",
        )
        self.record_button.pack(side="left")

        self.pause_button = ttk.Button(
            button_row,
            text="Ⅱ  Pause   [F10]",
            command=self._toggle_pause,
            state="disabled",
            style="Action.TButton",
        )
        self.pause_button.pack(side="left", padx=8)

        self.stop_button = ttk.Button(
            button_row,
            text="■  Stop   [F11]",
            command=self._stop_recording,
            state="disabled",
            style="Action.TButton",
        )
        self.stop_button.pack(side="left")

        ttk.Label(
            container,
            text="Hotkeys: F9 start/stop · F10 pause/resume · F11 stop",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(18, 0))

    def _refresh_display_info(self) -> None:
        if self.recorder and self.recorder.is_recording:
            return
        try:
            from mss import mss

            with mss() as sct:
                monitors = sct.monitors
                index = self.monitor.get()
                if 1 <= index < len(monitors):
                    monitor = monitors[index]
                    self.resolution.set(
                        f"Monitor {index}: {monitor['width']} × {monitor['height']} px"
                    )
                else:
                    self.resolution.set("Selected monitor not available")
        except Exception as exc:
            self.resolution.set(f"Display detection failed: {exc}")

    def _choose_directory(self) -> None:
        directory = filedialog.askdirectory(initialdir=self.output_dir.get())
        if directory:
            self.output_dir.set(directory)

    def _make_config(self) -> RecorderConfig:
        return RecorderConfig(
            output_dir=Path(self.output_dir.get()).expanduser(),
            filename=self.filename.get().strip() or "recording",
            fps=max(1, min(120, int(self.fps.get()))),
            monitor_index=int(self.monitor.get()),
            codec=self.codec.get(),
            prefer_lossless=self.use_lossless.get(),
        )

    def _toggle_record(self) -> None:
        if self.recorder and self.recorder.state in {
            RecorderState.RECORDING,
            RecorderState.PAUSED,
        }:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        if self.recorder and self.recorder.is_recording:
            return

        try:
            config = self._make_config()
            self.recorder = ScreenRecorder(config, on_state_change=self._handle_state_change)
            self.recorder.start()
            self.status.set("Starting recorder...")
            self._set_controls(recording=True)
            self._tick()
        except Exception as exc:
            self._set_controls(recording=False)
            messagebox.showerror("Unable to start recording", str(exc))
            self.status.set("Ready")

    def _toggle_pause(self) -> None:
        if not self.recorder:
            return

        try:
            if self.recorder.state == RecorderState.RECORDING:
                self.recorder.pause()
            elif self.recorder.state == RecorderState.PAUSED:
                self.recorder.resume()
        except Exception as exc:
            messagebox.showerror("Pause/resume failed", str(exc))

    def _stop_recording(self) -> None:
        recorder = self.recorder
        if not recorder:
            return

        try:
            output_path = recorder.stop()
            self.status.set("Saved")
            self._set_controls(recording=False)
            messagebox.showinfo(
                "Recording complete",
                f"Saved video to:\n{output_path}",
            )
        except Exception as exc:
            self._set_controls(recording=False)
            messagebox.showerror("Stop failed", str(exc))
            self.status.set("Ready")
        finally:
            self.recorder = None
            self.elapsed.set("00:00:00")
            self._refresh_display_info()

    def _handle_state_change(self, state: RecorderState) -> None:
        # Callback may run from worker thread; marshal back to Tk main thread.
        self.after(0, lambda: self._apply_state(state))

    def _apply_state(self, state: RecorderState) -> None:
        labels = {
            RecorderState.IDLE: "Ready",
            RecorderState.STARTING: "Starting...",
            RecorderState.RECORDING: "● Recording",
            RecorderState.PAUSED: "Ⅱ Paused",
            RecorderState.STOPPING: "Finalizing video...",
            RecorderState.FINISHED: "Saved",
            RecorderState.ERROR: "Error",
        }
        self.status.set(labels.get(state, state.value))

        if state == RecorderState.RECORDING:
            self.pause_button.configure(text="Ⅱ  Pause   [F10]")
        elif state == RecorderState.PAUSED:
            self.pause_button.configure(text="▶  Resume   [F10]")

    def _set_controls(self, recording: bool) -> None:
        if recording:
            self.record_button.configure(text="■  Stop Recording   [F9]")
            self.pause_button.configure(state="normal")
            self.stop_button.configure(state="normal")
        else:
            self.record_button.configure(text="●  Start Recording   [F9]")
            self.pause_button.configure(state="disabled", text="Ⅱ  Pause   [F10]")
            self.stop_button.configure(state="disabled")

    def _tick(self) -> None:
        if not self.recorder or not self.recorder.is_recording:
            return

        seconds = int(self.recorder.elapsed_seconds)
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        self.elapsed.set(f"{hours:02d}:{minutes:02d}:{secs:02d}")

        if self.recorder.state == RecorderState.RECORDING:
            self.status.set("● Recording")
        elif self.recorder.state == RecorderState.PAUSED:
            self.status.set("Ⅱ Paused")
        self.after(200, self._tick)

    def _on_close(self) -> None:
        if self.recorder and self.recorder.is_recording:
            confirmed = messagebox.askyesno(
                "Recording in progress",
                "Stop the current recording before closing?",
            )
            if not confirmed:
                return

            try:
                self.recorder.stop()
            except Exception:
                pass

        self.destroy()


def main() -> None:
    app = ScreenRecorderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
