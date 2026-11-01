# Changelog

All notable changes to the **OmniCapture** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-11-01

### Added
- **Dual Simultaneous Recording (PC Screen + Mobile Camera)**:
  - Added concurrent recording of the Windows PC desktop and Android camera sensor into **two separate, independent video files** (`REC_PC_SCREEN_*.mp4` and `REC_MOBILE_CAMERA_*.mp4`).
  - Added `core/pc_recorder.py`: Windows desktop capture engine leveraging FFmpeg's `gdigrab` with mouse cursor tracking and low-CPU `libx264` encoding.
  - Added `record_dual_pc_and_mobile_camera()` coordinator in `core/recorder.py` for single-keypress synchronized stop (`Enter` / `Ctrl+C`).
  - Added CLI command `python omni.py dual-record` with `--facing`, `--pc-fps`, `--camera-fps`, `--format`, `--no-camera-playback`, and `--upload` arguments.
  - Added option `[7]` to interactive terminal dashboard menu for one-click setup.
  - Automated dual upload: automatically queues both separate recording files to Google Drive when cloud sync is enabled.
- **Unit Tests**:
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
