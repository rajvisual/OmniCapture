# OmniCapture Developer Guide

Welcome to the **OmniCapture** developer and contributor guide. This document provides an in-depth breakdown of the architecture, codebase organization, development workflow, testing procedures, and guidelines for contributing new features or bug fixes.

---

## 1. Architectural Overview

OmniCapture is built with a modular, decoupling-first architecture. It wraps low-level command-line utilities (`scrcpy` and `adb`) into strongly-typed, cross-platform Python abstractions and pairs them with an interactive terminal UI (TUI) and cloud synchronization engines.

### Architecture Diagram

```mermaid
graph TD
    User([User / Shell]) --> CLI[omni.py CLI Dispatcher / TUI]
    CLI --> Config[Configuration Manager (config.json)]
    CLI --> ADBMgr[ADB Manager (core/adb_manager.py)]
    CLI --> Engine[Scrcpy Engine (core/scrcpy_engine.py)]
    CLI --> Recorder[Recorder Engine (core/recorder.py)]
    
    ADBMgr --> ADBBin[bin/adb.exe]
    ADBBin --> AndroidDev[(Android Device via USB / Wi-Fi)]
    
    Engine --> ScrcpyBin[bin/scrcpy.exe]
    ScrcpyBin --> AndroidDev
    
    Recorder --> Engine
    Recorder --> DriveUp[Drive Uploader (core/drive_uploader.py)]
    DriveUp --> LocalSync[Option A: Google Drive Desktop Virtual Drive]
    DriveUp --> CloudAPI[Option B: Google Drive REST API v3]
```

### Module Breakdown

| Module | Location | Primary Responsibilities |
| :--- | :--- | :--- |
| **CLI / TUI Entrypoint** | `omni.py` | Argument parsing (`argparse`), ANSI color/banner rendering, interactive keyboard menus, device auto-resolution, and command dispatching. |
| **ADB Manager** | `core/adb_manager.py` | High-level wrapper over `adb.exe`: device enumeration (`devices -l`), battery diagnostics (`dumpsys battery`), Wi-Fi IP discovery (`ip route`), wireless mode initialization (`tcpip 5555`), and stealth screen sleep (`input keyevent 223`). |
| **Scrcpy Engine** | `core/scrcpy_engine.py` | Command builder and process manager for `scrcpy.exe`. Translates Python options (resolution, bitrate, FPS, audio source, camera selection, UHID input) into safe scrcpy CLI flags. Enforces camera-mode constraint validations. |
| **Recorder Engine** | `core/recorder.py` | Coordinates direct-to-PC MP4/MKV recording sessions. Generates ISO-formatted filenames, displays live status HUDs and keyboard shortcut references, calculates file metrics upon completion, and invokes cloud uploads. |
| **Drive Uploader** | `core/drive_uploader.py` | Handles hybrid cloud synchronization: fast filesystem copies to mounted Google Drive desktop virtual paths (`G:\My Drive\...`) with automatic fallback to OAuth2-authenticated Google Drive REST API v3 chunked uploads. |

---

## 2. Development Setup

### Prerequisites
- **Operating System**: Windows 10 or Windows 11 (64-bit).
- **Python**: Version 3.10 or higher.
- **Git**: Installed and available in PATH.
- **Android Device**: Android 5.0+ (Lollipop) for screen mirroring; Android 12+ recommended for camera and audio support.

### Setting Up a Local Environment

1. **Clone the repository**:
   ```powershell
   git clone https://github.com/rajvisual/OmniCapture.git
   cd OmniCapture
   ```

2. **Create a virtual environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install optional cloud dependencies**:
   The core screen mirroring and recording functionalities have **zero external Python dependencies** (standard library only). If you are testing Google Drive API features:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Verify the installation**:
   ```powershell
   python omni.py info
   ```

---

## 3. Bundled Binaries & Runtime

OmniCapture ships with a self-contained runtime directory in `bin/`:
- `adb.exe`, `AdbWinApi.dll`, `AdbWinUsbApi.dll`
- `scrcpy.exe`, `scrcpy-server`, `SDL2.dll`
- Codec libraries: `avcodec-61.dll`, `avformat-61.dll`, `avutil-59.dll`, `swresample-5.dll`

### Path Resolution Principle
Always resolve paths relative to `omni.py`'s directory (`BASE_DIR`) rather than the current working directory (`os.getcwd()`). This guarantees that launching `omni.py` from any terminal directory or shortcut will locate the bundled tools reliably:

```python
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_BIN_DIR = BASE_DIR / "bin"
DEFAULT_RECORDINGS_DIR = BASE_DIR / "recordings"
```

---

## 4. Coding Standards & Conventions

### Style & Formatting
- **PEP 8**: Follow standard Python naming conventions (snake_case for functions and variables, PascalCase for classes).
- **Type Annotations**: Provide type hints for public functions and classes where feasible:
  ```python
  def start_mirror(self, device_id: str | None = None, fullscreen: bool = False) -> subprocess.Popen:
  ```
- **Console Encoding**: Always ensure standard output uses UTF-8 to prevent `UnicodeEncodeError` on legacy Windows code pages:
  ```python
  if sys.platform == "win32":
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
  ```
- **Error Handling**: Catch specific exceptions (`FileNotFoundError`, `subprocess.SubprocessError`, `json.JSONDecodeError`). Avoid bare `except:`.

---

## 5. Scrcpy Parameter & Constraint Rules

When modifying or adding flags in `core/scrcpy_engine.py`, observe scrcpy's validation rules:

1. **Camera Mode Conflicts**:
   - In `--video-source=camera`, scrcpy does not accept `--turn-screen-off` or `--stay-awake`.
   - Control is disabled by default in camera mode unless explicitly configured.
   - Screen off during camera sessions must be accomplished via ADB (`turn_screen_off()`) instead of scrcpy CLI flags.
2. **Audio Capture Rules**:
   - `--audio-source=playback` requires Android 13+ and scrcpy 2.0+.
   - On Android 11/12, use `--audio-source=mic` or pass `--no-audio` to avoid demuxer stream stalls.
3. **UHID Control**:
   - For Xiaomi/HyperOS devices where ADB input injection is blocked, pass `--keyboard=uhid --mouse=uhid` to emulate Linux kernel HID devices.

---

## 6. Running the Test Suite

OmniCapture includes automated unit tests in `tests/` that do not require an active Android device or hardware connection.

Run all unit tests:
```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Check syntax and compile all source files:
```powershell
python -m py_compile omni.py core/*.py tests/*.py
```

---

## 7. Adding New Features

### Adding a New CLI Subcommand
1. Define the subcommand in `omni.py` inside `build_parser()`:
   ```python
   sub_new = subparsers.add_parser("myfeature", help="Description of feature")
   sub_new.add_argument("--my-flag", action="store_true", help="Flag description")
   ```
2. Add a corresponding dispatch handler in `main()`:
   ```python
   elif args.command == "myfeature":
       handle_my_feature(args, config)
   ```
3. If applicable, add a menu option in the interactive TUI menu loop in `run_interactive_menu()`.
4. Add unit test coverage in `tests/test_cli.py`.
5. Update `docs/features.md` and `README.md`.

---

## 8. Git Commit Guidelines

OmniCapture follows the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` A new feature or capability.
- `fix:` A bug fix.
- `docs:` Documentation-only changes.
- `style:` Formatting or whitespace changes (no code logic modification).
- `refactor:` Code restructuring that neither adds a feature nor fixes a bug.
- `test:` Adding or updating unit tests.
- `chore:` Maintenance tasks, dependency updates, or build scripts.

Example commit message:
```text
feat(scrcpy): add support for custom video encoder selection
fix(adb): handle unmounted drive letters gracefully in drive uploader
docs(features): document UHID mouse emulation for Xiaomi devices
```
