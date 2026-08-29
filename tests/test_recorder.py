from pathlib import Path

from screen_recorder.recorder import RecorderConfig, ScreenRecorder


def test_output_path_is_unique(tmp_path: Path) -> None:
    config = RecorderConfig(output_dir=tmp_path, filename="demo")
    recorder = ScreenRecorder(config)

    first = recorder._build_output_path()
    first.touch()

    second = recorder._build_output_path()

    assert first.name == "demo.mp4"
    assert second.name == "demo_1.mp4"


def test_filename_is_sanitized(tmp_path: Path) -> None:
    config = RecorderConfig(output_dir=tmp_path, filename="my recording?.mp4")
    recorder = ScreenRecorder(config)

    output = recorder._build_output_path()

    assert "?" not in output.name
    assert output.suffix == ".mp4"
