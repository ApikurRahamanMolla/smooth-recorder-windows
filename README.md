# Smooth Recorder (Windows)

An automated screen recorder for Windows built using Python, OpenCV, and Tkinter. It captures screen frames alongside global mouse click events to apply dynamic camera auto-zoom, exponential panning smoothing, and cursor ring highlights.

## Features
- **Auto-Zoom on Clicks:** Scales and centers the viewport dynamically around mouse clicks.
- **Cluster Click Detection:** Groups rapid multi-clicks into a steady camera focal point.
- **Liquid Camera Panning:** Uses exponential interpolation (Lerp) for smooth camera transitions.
- **Standalone GUI App:** Simple Tkinter interface with zero configuration.

## Requirements & Dependencies
- Python 3.x
- `opencv-python`
- `numpy`
- `mss`
- `pynput`

## How to Run

1. Clone this repository:
   ```bash
   git clone [https://github.com/ApikurRahamanMolla/smooth-recorder-windows.git](https://github.com/ApikurRahamanMolla/smooth-recorder-windows.git)
   cd smooth-recorder-windows
2.Install dependencies:

Bash
pip install opencv-python numpy mss pynput


3.Launch the application:

Bash
python app.py



Build Standalone Windows Executable (.exe)
To package the app into a single .exe file using PyInstaller:

Bash
pip install pyinstaller
pyinstaller --noconsole --onefile app.py