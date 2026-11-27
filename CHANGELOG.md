# Changelog

All notable changes to the **OmniCapture** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-11-27

### Added
- **Phase 0 Forensic Audit & Benchmark Engine**:
  - Measured cold start, working set memory (71.15 MB), active recording overhead (< 1.8% CPU), and verified Windows 11 Per-Monitor v2 DPI scaling (100% to 200%).
  - Identified and eliminated idle CPU churn in audio meter simulation loop, slashing idle CPU from 8.44% to 0.77%.
- **Liquid Glass & Light Minimal Token System (`gui/theme.py`)**:
  - Extended `ThemeTokens` with alpha-based glass tokens: `surface_glass`, `glass_stroke`, `glass_highlight`, `glass_shadow`, `blur_radius`, `noise_opacity`, and per-state alphas (`alpha_surface_idle` through `alpha_surface_disabled`).
  - Implemented mathematical WCAG AA relative luminance contrast verification methods directly on tokens.
  - Tuned `status_recording` to `#DC2626` (4.83:1 contrast on white text), `text_dim` to `#52525B` (7.73:1), and `status_connected` to `#059669` (3.42:1 on root).
- **Automated Token Contrast Verification Test Suite (`tests/test_gui.py`)**:
  - Added `test_wcag_aa_contrast_all_token_pairs` and `test_theme_switching_and_tokens`.
  - 100% passing across 42 automated tests.
- **Design System Polish & Fluent Formatting (`gui/dashboard.py`, `gui/components/audio_meter.py`)**:
  - Refactored all uppercase labels to clean sentence case (`Studio Ready`, `Rec: 00:00:00`, `60.0 fps`, `8.0 Mbps`, `Muted`).
  - Standardized font factories to `OmniTheme.font_*()`.

## [1.2.0] - 2026-11-27

### Added
- **Modern Windows 11 Dark Mode GUI Dashboard (`gui/dashboard.py`)**:
  - Full-featured, responsive desktop GUI powered by `customtkinter` with Windows 11 Fluent dark aesthetics.
  - Live Header: Device connection pill (`● Connected: Model [USB/Wi-Fi]`), live battery indicator, quick refresh, and camera lock release.
  - Hero Card for **Dual Simultaneous Recording**: 1-click synchronized PC screen and mobile camera capture with live elapsed timer, real-time file size counters, and instant stop/finalize.
  - Dedicated tabs for Display Mirror & PC Touch Controller (UHID / touch mode), Stealth Camera Stream Viewfinder, Direct-to-PC Recording, Wireless ADB Switch, Hardware Camera Diagnostics, Recordings Gallery, and Google Drive Cloud Settings.
  - Recordings Gallery: Visual browser of past recordings with 1-click playback in Windows default player, folder open, and cloud upload.
- **System Tray Integration (`gui/tray.py`)**:
  - Background system tray icon using `pystray` and brand icons.
  - Minimize to system tray on window close, keeping OmniCapture running smoothly in the background.
  - System tray context menu: Quick Dashboard launch, Quick Dual Recording, Quick Mirror, Quick Camera Stream, Open Recordings Folder, and Exit.
  - Native Windows tray notification toasts for recording status and device events.
- **Global Windows Hotkeys (`gui/hotkeys.py`)**:
  - Native Windows Win32 global hotkeys (`RegisterHotKey`) operating across the entire OS with zero CPU overhead:
    - `Ctrl + Alt + D`: Quick Dual Simultaneous Recording start/stop.
    - `Ctrl + Alt + M`: Quick Display Mirror & PC Controller.
    - `Ctrl + Alt + C`: Quick Stealth Camera Stream.
    - `Ctrl + Alt + R`: Open Recordings Folder in Windows Explorer.
- **Standalone Portable `.exe` Bundle (Zero-Install)**:
  - Added `OmniCapture.spec` and `scripts/build_standalone.py` to compile self-contained, portable Windows distribution.
  - Bundles Python runtime, `customtkinter`, `pillow`, `pystray`, `scrcpy`, `adb`, and asset libraries into `dist/OmniCapture/`.
- **Launchers & CLI Integration**:
  - Added CLI command `python omni.py gui` and `--gui` flag.
  - Added option `[G]` in interactive terminal dashboard menu to jump straight into the GUI.
  - Added `omni-gui.bat` and `omni-gui.vbs` root launchers for seamless 1-click startup from Windows Explorer.
- **Resource Path Resolver (`core/resource_path.py`)**:
  - Centralized path resolution supporting both standard Python script execution and PyInstaller bundled execution (`sys._MEIPASS`).
- **Automated Tests**:
  - Added `tests/test_gui.py` covering theme colors, controller lifecycle, tray menu, hotkey registration, and resource path resolvers.
  - Extended `tests/test_cli.py` to cover `gui` command and `--gui` flag.

## [1.1.0] - 2026-11-01

### Added
- **Dual Simultaneous Recording (PC Screen + Mobile Camera)**:
  - Added concurrent recording of the Windows PC desktop and Android camera sensor into **two separate, independent video files** (`REC_PC_SCREEN_*.mp4` and `REC_MOBILE_CAMERA_*.mp4`).
  - Added `core/pc_recorder.py`: Windows desktop capture engine leveraging FFmpeg's `gdigrab` with mouse cursor tracking and low-CPU `libx264` encoding.
  - Added `record_dual_pc_and_mobile_camera()` coordinator in `core/recorder.py` for single-keypress synchronized stop (`Enter` / `Ctrl+C`).
  - Added CLI command `python omni.py dual-record` with `--facing`, `--pc-fps`, `--camera-fps`, `--format`, `--no-camera-playback`, and `--upload` arguments.
  - Added option `[7]` to interactive terminal dashboard menu for one-click setup.
  - Automated dual upload: automatically queues both separate recording files to Google Drive when cloud sync is enabled.
- **Hardware Preflight Verification & Healthchecks**:
  - Added strict preflight diagnostic guards ensuring ADB devices are connected and authorized before initiating mobile capture.
  - Independent stream status reporting (`SUCCESS`, `PARTIAL SUCCESS`, `FAILED`) to prevent false dual-recording success claims.
  - Added automatic camera sensor lock release to close conflicting background camera apps on phone before capture.
- **Unit Tests**:
  - Added `tests/test_audit_and_verification.py` verifying device preflight states, error handling, and 0-byte file cleanup.
  - Added `tests/test_pc_recorder.py` validating FFmpeg command flag construction and dual filename generation.
  - Extended `tests/test_cli.py` to cover `dual-record` and `record dual`.

## [1.0.0] - 2026-10-30

### Initial Release

#### Core Features
- **Display Mirroring & Remote Control**:
  - High-performance Direct3D 11 hardware-accelerated video mirroring with ultra-low latency (<35ms).
  - Full mouse touchscreen emulation: single taps, drag-to-swipe, long-press, back button (right-click), home button (middle-click), and mouse wheel scrolling.
  - Full physical PC keyboard forwarding with real-time keystroke injection and cross-device clipboard synchronization.
  - Hardware HID mode (`--uhid`) to emulate a physical USB mouse and keyboard directly at the Linux kernel level (`/dev/uhid`), bypassing Xiaomi MIUI/HyperOS `INJECT_EVENTS` security locks.

- **Background Stealth Camera Capture**:
  - Direct video and audio streaming from device camera sensors via Android Camera2 API (`--video-source=camera`).
  - Operates completely in the background without opening the native camera application or lighting up the screen.
  - Supports front, back, and external camera sensors with custom resolution (`--camera-size`), aspect ratios, and frame rate settings.
  - Native microphone audio capture (`--audio-source=mic`).

- **Unlimited Direct-to-PC Recording**:
  - Direct video and audio streaming straight to PC storage (`recordings/`), bypassing mobile storage limits and eliminating device thermal throttling.
  - Support for MP4 and crash-resilient MKV formats.
  - Automatic timestamped file naming and session duration/size calculations.

- **Keyboard Hotkeys & Controls**:
  - Interactive hotkey shortcuts using `Left-Alt`:
    - `Alt + Z`: Pause / freeze video stream.
    - `Alt + Shift + Z`: Resume video stream.
    - `Alt + O` / `Alt + Shift + O`: Turn physical phone screen off/on while keeping stream active.
    - `Alt + F`: Toggle fullscreen mode.
    - `Alt + H`, `Alt + B`, `Alt + S`: Home, Back, and Recent Apps controls.

- **Dual Mode (Picture-in-Picture)**:
  - Simultaneous dual-window execution running display mirror and camera feed side-by-side.

- **Automated Cloud Synchronization**:
  - Option A: Native detection and auto-syncing to Google Drive for Desktop virtual drives (`G:\My Drive\OmniCapture`).
  - Option B: Direct Google Drive API v3 upload using OAuth 2.0 with resumable 5MB chunked transfers and shareable link output.

- **Wireless Wi-Fi Connectivity**:
  - One-click transition from USB to TCP/IP wireless debugging (`adb tcpip 5555`) using automatic device Wi-Fi IP detection.

- **Diagnostics & Hardware Inspection**:
  - Automated detection of device models, battery levels, charging states, Wi-Fi IP addresses, camera sensor IDs, and supported resolution lists.
