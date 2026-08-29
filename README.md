# Python Screen Recorder

A GitHub-ready intermediate Python screen recorder with a simple desktop GUI.

It captures a selected monitor with **MSS**, encodes frames with **OpenCV**, and keeps the capture loop off the Tkinter UI thread so the interface stays responsive.

## Features

- Full-monitor screen capture
- Select monitor 1, 2, or 3
- 15 / 24 / 30 / 45 / 60 FPS
- MP4 output
- Automatic filename collision handling
- Pause / resume
- Recording timer
- Keyboard shortcuts:
  - `F9` — start/stop
  - `F10` — pause/resume
  - `F11` — stop
- Output directory picker
- Responsive GUI using a background capture thread
- Basic error handling and clean shutdown

## Project structure

```text
screen-recorder-python/
├── main.py
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── LICENSE
├── .gitignore
└── screen_recorder/
    ├── __init__.py
    ├── app.py
    └── recorder.py
```

## Requirements

- Python 3.10+
- Windows, Linux, or macOS
- A desktop environment with a monitor available for capture
- OpenCV with a working video writer backend

## Installation

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/YOUR_USERNAME/python-screen-recorder.git
cd python-screen-recorder

python -m venv .venv
```

Activate it:

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

### Windows CMD

```cmd
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## How it works

The application has two layers:

1. **GUI layer** — `screen_recorder/app.py`
   - Tkinter interface
   - User configuration
   - Buttons and hotkeys
   - Timer and status updates

2. **Recorder engine** — `screen_recorder/recorder.py`
   - MSS screenshot capture
   - BGRA → BGR frame conversion
   - OpenCV `VideoWriter`
   - Background thread
   - Pause/resume state handling
   - Automatic output filename generation

The general pipeline is:

```text
Monitor
   │
   ▼
MSS screenshot
   │
   ▼
NumPy array
   │
   ▼
BGRA → BGR
   │
   ▼
OpenCV VideoWriter
   │
   ▼
MP4 file
```

## Performance notes

Screen recording is CPU-, memory-bandwidth-, and disk-intensive.

For a laptop or lower-end machine, start with:

- 30 FPS
- One monitor
- A moderate screen resolution

Higher resolutions and 60 FPS increase the number of frames that must be captured and encoded per second.

If the recording appears choppy, reduce the FPS or close resource-heavy applications.

## Codec notes

The default codec is `mp4v` because it is broadly available in OpenCV installations.

The `avc1` option may work on systems whose OpenCV/FFmpeg build provides an H.264 encoder. Availability varies by platform and package build.

## Troubleshooting

### `ModuleNotFoundError`

Install dependencies again:

```bash
pip install -r requirements.txt
```

### The app starts but recording cannot be created

Try the `mp4v` codec first. Also verify that your OpenCV installation has a working FFmpeg/video backend:

```bash
python -c "import cv2; print(cv2.getBuildInformation())"
```

### Monitor not found

The recorder numbers real monitors starting at `1`. Monitor `0` is MSS's virtual desktop and is intentionally not exposed by the GUI.

### Linux capture issues

Desktop capture behavior can depend on your display server and desktop environment. If capture is unavailable under your setup, test with a standard X11 session or check your distribution's screen-capture permissions.

### macOS permissions

macOS may require Screen Recording permission for the Python interpreter or terminal/application launching the recorder.

## Development

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run a basic lint check:

```bash
ruff check .
```

Run tests (when test files are added):

```bash
pytest
```

## Future improvements

This project intentionally stays at an intermediate complexity level. Good next upgrades include:

- Region selection
- Webcam overlay
- Microphone/system-audio recording
- Recording pause/resume without timestamp gaps
- Hardware-accelerated H.264 encoding
- Custom bitrate / quality controls
- Recording hotkey customization
- Preview window
- System tray mode
- Installer/package generation
- Automated tests for recorder state transitions

## License

MIT — see `LICENSE`.
