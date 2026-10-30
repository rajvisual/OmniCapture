# OmniCapture Screenshot Gallery

This directory contains the visual gallery assets referenced in the OmniCapture `README.md` and documentation suite.

## Image Manifest

| Filename | Description | Source / Capture Command |
| :--- | :--- | :--- |
| `01-terminal-dashboard.png` | Interactive ASCII terminal menu & device status | Run `omni.bat` or `python omni.py` in Windows Terminal |
| `02-device-diagnostics.png` | Camera2 API sensor diagnostics & battery details | Run `python omni.py info` |
| `03-screen-mirroring.png` | Live 60 FPS screen mirroring display window | Run `python omni.py mirror` |
| `04-stealth-camera.png` | Stealth camera stream with screen turned off | Run `python omni.py camera --turn-screen-off` |
| `05-recording-hud.png` | Direct-to-PC recording active session & hotkey HUD | Run `python omni.py record` |

---

## How to Update or Replace Screenshots

1. **Launch the feature** you wish to capture using the command listed in the manifest above.
2. **Capture the window**:
   - On Windows 10/11, press `Alt + PrintScreen` to capture only the active window, or `Win + Shift + S` to use the Snipping Tool.
3. **Save and Optimize**:
   - Crop cleanly to the window boundaries.
   - Save as PNG with the exact matching filename in this directory (`assets/screenshots/`).
   - GitHub's markdown will immediately render your updated screenshot.
