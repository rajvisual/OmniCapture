# OmniCapture Studio — Official Desktop Application Guide & Architecture

---

## 1. Executive Summary

**OmniCapture Studio** is a professional, hardware-accelerated Windows 11 desktop broadcast and recording suite. It synchronizes **PC screen capture** and **Android mobile camera / display streaming** into a unified, low-latency workflow. 

Engineered with architectural inspiration from industry-standard creative tools (**OBS Studio**, **DaVinci Resolve**, **Adobe Premiere Pro**, and **Visual Studio Code**), OmniCapture Studio replaces clashing web-like panels and classic white Win32 menus with a custom Fluent titlebar, Windows 11 DWM Mica/Acrylic backdrop synchronization, a 3-tier surface hierarchy, a Digital Audio Workstation (DAW) mixer, and an instant Command Palette.

---

## 2. Technical Stack & Core Architecture

OmniCapture Studio is built on a decoupled, asynchronous Python desktop architecture:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                              │
│  CustomTkinter  ·  Win32 DWM Engine  ·  Theme Tokens  ·  Fluent UIs    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ thread-safe signals & callbacks
┌───────────────────────────────────▼────────────────────────────────────┐
│                        APPLICATION CONTROLLER                          │
│         gui/controller.py (GUIController & Background Poller)          │
└───────────┬───────────────────────┼───────────────────────┬────────────┘
            │                       │                       │
┌───────────▼───────────┐ ┌─────────▼───────────┐ ┌─────────▼────────────┐
│     ScrcpyEngine      │ │     PCRecorder      │ │      ADBManager      │
│  Direct3D 11 Pipeline │ │   FFmpeg Loopback   │ │ USB/Wi-Fi Telemetry  │
│  Camera2 Sensor Stream│ │ DirectShow Capture  │ │ Camera Lock Release  │
│  Linux /dev/uhid HID  │ │ Hardware NVENC/QSV  │ │ Battery & IP Polling │
└───────────────────────┘ └─────────────────────┘ └──────────────────────┘
                                    │
                        ┌───────────▼───────────┐
                        │     DriveUploader     │
                        │ Local Virtual Drive   │
                        │ OAuth2 REST API v3    │
                        └───────────────────────┘
```

### Core Subsystems:
1. **Frontend UI Engine**: CustomTkinter enhanced with `ctypes.windll.dwmapi` for native Windows 11 DWM titlebar color synchronization, rounded corners (`DWMWCP_ROUND`), and Mica backdrops.
2. **`ScrcpyEngine` ([`core/scrcpy_engine.py`](../core/scrcpy_engine.py))**: Handles low-latency Direct3D 11 mobile display streaming, raw Android Camera2 sensor captures (with mobile screen powered off), and kernel-level `/dev/uhid` mouse touch emulation.
3. **`PCRecorder` ([`core/pc_recorder.py`](../core/pc_recorder.py))**: Manages multi-threaded FFmpeg DirectShow and GDI screen captures synchronized at 30 or 60 FPS.
4. **`ADBManager` ([`core/adb_manager.py`](../core/adb_manager.py))**: Asynchronous hardware poller tracking USB attachments, battery levels, Wi-Fi IP discovery, TCP/IP 5555 switching, and automated Camera2 sensor lock release.
5. **`DriveUploader` ([`core/drive_uploader.py`](../core/drive_uploader.py))**: Zero-overhead local filesystem synchronization to Google Drive for Desktop virtual paths (`G:\My Drive\OmniCapture`) with automatic fallback to OAuth2 Google Drive REST API v3 chunked uploads.

---

## 3. Workspace Layout & Interface Anatomy

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  OmniCapture Studio v1.3.0  │  [File] [Capture] [Tools] [View] [Help]  │ ☀ Light [Scan]│ (Top Bar)
├──────────────────────────────────────────────────────┬─────────────────────────────────┤
│                                                      │  Properties                     │
│  Preview: Dual Recording                             │                                 │
│  ┌────────────────────────────────────────────────┐  │  Camera sensor:  [Back] [Front] │
│  │ Safe Area Guides                              │  │  Frame rate:     [30fps] [60fps]│
│  │                                                │  │  Container:      [MP4]  [MKV]   │
│  │        PC Primary Display (Direct3D 11)        │  │  Touch mode:     [Touch] [UHID] │
│  │               1920x1080 @ 60 FPS               │  │  [✓] Show preview window        │
│  │                                  ┌───────────┐ │  │  [✓] Turn mobile screen off     │
│  │                                  │Camera2 PiP│ │  │  [ ] Auto-upload to Drive       │
│  │                                  └───────────┘ │  │  [Switch to Wi-Fi ADB]          │
│  └────────────────────────────────────────────────┘  │                                 │
├─────────────────┬─────────────────┬──────────────────┴───────────────┬─────────────────┤
│ Scenes          │ Sources         │ Audio mixer                      │ Controls        │
│ [Dual Stream]   │ [✓] PC Display  │ Phone mic [Mute] [Gain] [VU ▃▅█] │ [Start Record]  │
│ [Screen Mirror] │ [✓] Camera2     │ PC audio  [Mute] [Gain] [VU ▃▅ ] │ [Launch Mirror] │
│ [Camera Feed]   │ [ ] UHID Mouse  │                                  │ [Media Library] │
│ [Screen Record] │                 │                                  │ [Preferences]   │
├─────────────────┴─────────────────┴──────────────────────────────────┴─────────────────┤
│  ● STUDIO READY │  REC: 00:00:00  │  FPS: 60.0  │  BITRATE: 8.0M  │  DISK: 142.4 GB free│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1. Unified Custom Top Bar
* **Brand Identity**: 20px vector app icon, product name, and version badge.
* **In-App Menu Bar**: Fluent popup dropdown menus (`File`, `Capture`, `Tools`, `View`, `Settings`, `Help`) with 8px radius, hover states, and keyboard shortcut legends. Replaces the legacy clashing white Win32 menu bar.
* **Centered Command Pill**: Quick launch bar for the fuzzy-search Command Palette (`Ctrl+P`) and real-time hardware status text (`● POCO M3 (USB Direct · 82% ⚡)`).
* **Quick Tools**: Instant theme toggle button (`☀ Light` / `🌙 Dark`), device refresh (`F5`), and sensor lock release.

### 2. Live Canvas Viewport (Center Stage)
* **16:9 Viewport**: High-contrast broadcast preview box with configurable aspect ratio switcher (`16:9`, `9:16` phone portrait, `Fit`).
* **Visual Guides**: Centered crosshair marker and safe-area guide framing.
* **Dynamic Scene Representation**:
  * *Dual Stream*: PC primary display canvas with an interactive PiP camera sensor viewfinder.
  * *Screen Mirror*: Low-latency mobile display reflection.
  * *Camera Viewfinder*: Direct Camera2 raw sensor capture.
  * *Screen Record*: Dedicated display capture layout.
* **Designed Canvas Empty State**: Clean smartphone wireframe icon, descriptive instructions, and a 1-click "Scan for Devices" action button when no phone is connected.
* **Active Tally HUD**: Floats at top of canvas during recording, showing active timer (`● REC 00:02:14`) and parallel stream byte counters.

### 3. Properties Inspector (Right Panel)
* Contextual properties adhering to 32px control heights:
  * Camera Facing: `Back` (Standard/Wide) vs. `Front` (Selfie).
  * Frame Rate: `30 fps` vs. `60 fps`.
  * Container Format: `MP4` (universal playback) vs. `MKV` (crash-safe stream recording).
  * Touch Input Mode: `Standard Touch` vs. `Hardware (UHID)` (kernel-level mouse emulation for Xiaomi/POCO devices).
  * Operational Switches: Show preview window, Turn mobile screen off, Auto-upload to Google Drive.
  * 1-Click Wi-Fi ADB switcher.

### 4. Modular Production Dock (Bottom)
* **Scenes (Presets)**: 1-click scene selector with number hotkeys `1`, `2`, `3`, `4`.
* **Sources**: Active capture stream checkboxes with visibility state (`PC Display`, `Phone Camera Sensor`, `UHID Mouse`).
* **Audio Mixer**: DAW-style channel strips for **Phone Microphone** and **Desktop Playback**:
  * Decibel numerical readouts (`-inf` to `0.0 dB`).
  * Mute button with active crimson red visual state.
  * Real-time VU level meters with dynamic color shifting: **Green** (<= -12 dB), **Yellow** (-12 to -3 dB), and **Red** clipping (>-3 dB).
* **Master Controls**:
  * Primary Action Button: 44px height with subtle breathing pulse animation during recording.
  * Secondary Actions: `Launch Mirror`, `Media Library`, `Preferences`.

### 5. Broadcast Status Strip
* Live telemetry bar displaying hardware status chip (`STUDIO READY` / `RECORDING`), recording timer, live FPS, active bitrate, and real-time free disk space calculation (`DISK: 142.4 GB free`).

---

## 4. Visual Design System & Design Tokens

OmniCapture Studio strictly adheres to a **4px grid spacing system**, a **3-tier surface hierarchy**, and **WCAG AA contrast ratios (>= 4.5:1)**.

### Design Token Specification ([`gui/theme.py`](../gui/theme.py))

| Token Name | Light Minimal | Dark Liquid Glass | Description & Purpose |
| :--- | :--- | :--- | :--- |
| **`bg_root`** | `#F3F4F6` | `#0B0C10` | Tier 1: Deep foundation background canvas |
| **`bg_panel`** | `#FFFFFF` | `#111218` | Tier 2: Studio panels (Canvas, Inspector, Dock) |
| **`bg_raised`** | `#FFFFFF` | `#181922` | Tier 3: Elevated cards, empty state, inputs |
| **`bg_header`** | `#F8FAFC` | `#13141D` | Top bar, dock headers, and status footer |
| **`bg_input`** | `#F1F3F5` | `#1A1B26` | Form inputs, segmented controls, inactive buttons |
| **`bg_hover`** | `#E9ECEF` | `#232534` | Hover highlight on interactive elements |
| **`border_subtle`**| `#E5E7EB` | `#222432` | 1px low-contrast panel separation |
| **`border_default`**| `#D1D5DB` | `#2C2F42` | Control boundaries and outline strokes |
| **`border_focus`** | `#2563EB` | `#3B82F6` | Keyboard focus ring & active indicator |
| **`border_specular`**| `#FFFFFF` | `#3D4158` | Top-edge specular glass highlight |
| **`text_primary`** | `#111827` (14:1) | `#F9FAFB` (15:1) | High-contrast headers and primary text |
| **`text_secondary`**| `#374151` (7:1) | `#D1D5DB` (8:1) | Secondary body reading text |
| **`text_muted`** | `#6B7280` (4.8:1) | `#9CA3AF` (5:1) | Meta descriptions and secondary labels |
| **`text_dim`** | `#9CA3AF` | `#6B7280` | Placeholders, disabled states, hotkey hints |
| **`accent_primary`**| `#2563EB` | `#2563EB` | Dedicated primary action (Start Recording only) |
| **`status_recording`**| `#EF4444` | `#EF4444` | Live recording tally, active mute button |
| **`status_connected`**| `#10B981` | `#10B981` | Live hardware ready / connected state |
| **`vu_bg`** | `#E5E7EB` | `#0D1017` | Digital audio level meter track background |

### Typography Scale:
* **Font Family**: Segoe UI Variable (with Segoe UI / Inter fallback)
* **Title / Modal Header**: 20px semibold
* **Headline**: 15px bold
* **Section / Dock Title**: 13px bold (sentence-case)
* **Body Text**: 12px regular / bold
* **Caption & Meta**: 11px regular / bold
* **Monospace Telemetry**: Consolas 10–11px (tabular numbers for timer, FPS, bitrate, dB)

---

## 5. Keyboard Shortcuts & Command Palette

OmniCapture Studio provides full keyboard accessibility:

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| **`Ctrl + P`** or **`Ctrl + Shift + P`** | **Command Palette** | Opens instant fuzzy-search dialog for all actions |
| **`Ctrl + Alt + D`** | **Start / Stop Dual Record** | Toggles parallel PC Screen + Camera recording |
| **`Ctrl + Alt + M`** | **Launch Screen Mirror** | Starts low-latency interactive phone display mirror |
| **`Ctrl + Alt + C`** | **Camera Viewfinder** | Opens raw Camera2 viewfinder on desktop |
| **`Ctrl + Alt + R`** | **Open Recordings** | Reveals `recordings/` directory in Windows Explorer |
| **`Ctrl + Shift + L`** | **Release Camera Lock** | Force-stops background camera apps on phone |
| **`F5`** | **Refresh Devices** | Triggers ADB hardware re-scan |
| **`1` / `2` / `3` / `4`** | **Switch Scene** | Switches between Dual, Mirror, Camera, and Screen |
| **`Ctrl + ,`** | **Preferences** | Opens Studio Settings dialog |
| **`Ctrl + W`** | **Minimize to Tray** | Minimizes window to Windows notification area |
| **`Ctrl + Q`** | **Exit Application** | Performs safe shutdown and finalizes recordings |

---

## 6. Dialog Subsystems

### 1. Media Library & Recordings Gallery ([`gui/dialogs/recordings.py`](../gui/dialogs/recordings.py))
* Instant search filter for recordings by filename or mode tag (`DUAL_PC`, `DUAL_CAM`, `SCREEN`, `CAMERA`).
* Real-time calculation of total stored video size.
* Actions per recording:
  * `Play`: Opens video in Windows default media player.
  * `Explorer`: Selects and highlights the file inside Windows Explorer.
  * `Upload`: Triggers instant Google Drive cloud sync.
  * `Delete`: Prompts confirmation dialog to safely remove media.

### 2. Studio Preferences ([`gui/dialogs/settings.py`](../gui/dialogs/settings.py))
* **Capture Defaults**: Set default video container (`MP4` / `MKV`) and target FPS (`30` / `60`).
* **Output Storage**: Native Windows folder picker (`filedialog.askdirectory()`) to customize where video files are saved.
* **Appearance**: Switch between `Dark Liquid Glass` and `Light Minimal` themes.
* **System Integration**: Toggles for minimizing to tray on close and enabling global system hotkeys.

### 3. System & Hardware Diagnostics ([`gui/dialogs/diagnostics.py`](../gui/dialogs/diagnostics.py))
* **Binary Telemetry**: Inspects ADB, Scrcpy, and FFmpeg installation paths, versions, and hardware acceleration status.
* **Device Telemetry**: Inspects serial IDs, battery levels, and Wi-Fi IP.
* **Camera2 Sensor Explorer**: Dumps raw hardware camera characteristics, supported resolutions, and frame rates.
* **1-Click Repair Tools**: `Restart ADB Server`, `Release Camera Lock`, and `Copy Report to Clipboard`.

---

## 7. Step-by-Step User Workflows

### Workflow 1: Dual Simultaneous Recording (PC Screen + Phone Camera)
1. Plug your Android phone into your PC using a USB data cable.
2. Ensure **USB Debugging** is enabled in Developer Options.
3. Launch OmniCapture Studio (`omni-gui.bat` or `python omni.py gui`).
4. The canvas will detect the device and switch from the empty state to the 16:9 Dual preview.
5. In the Properties panel on the right, select:
   * Camera: `Back` (Standard) or `Front` (Selfie).
   * Frame Rate: `60 fps`.
   * Format: `MP4` or `MKV`.
6. Click **`Start Recording`** (or press `Ctrl+Alt+D`).
   * The recording tally HUD appears on the canvas.
   * The master button turns red with a breathing pulse.
   * Two independent video files (`REC_DUAL_PC_...` and `REC_DUAL_CAM_...`) record in parallel.
7. Click **`Stop Recording`** when finished. The videos are saved and ready in the **Media Library**.

### Workflow 2: Display Mirror with Hardware Mouse Touch
1. Select the **`Screen Mirror`** scene (or press `2`).
2. In the right Inspector under *Touch input mode*, choose **`Hardware (UHID)`**.
3. Click **`Launch Mirror`** (or press `Ctrl+Alt+M`).
4. An interactive window displays your phone’s screen with full mouse and keyboard control, bypassing Xiaomi/POCO developer account restrictions.

### Workflow 3: Switching Themes at Runtime
* Click **`☀ Light`** or **`🌙 Dark`** in the top bar.
* The application surfaces, borders, text, audio meters, and native Windows 11 DWM titlebar synchronize instantly with zero layout shift.

---

## 8. Distribution & Build Guide

### Running from Source
```bash
# 1. Activate virtual environment
.venv\Scripts\activate

# 2. Launch GUI Studio directly
python omni.py gui

# 3. Or launch via 1-click batch launcher
omni-gui.bat
```

### Building Zero-Install Standalone Executable
```bash
# Run the standalone PyInstaller packaging script
python scripts/build_standalone.py
```
The compiled bundle is located at:
```text
dist/OmniCapture/OmniCapture.exe
```
This self-contained executable includes all runtime binaries (`adb.exe`, `scrcpy.exe`, `SDL2.dll`, `avcodec-61.dll`), default configuration files, and assets without requiring Python on target machines.
