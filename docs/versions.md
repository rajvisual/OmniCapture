# OmniCapture Version Catalog & Evolution Guide

Welcome to the **OmniCapture Version Catalog**. Every release of OmniCapture is engineered with a distinct purpose, unique capabilities, and standalone portability.

Whether you prefer a lightweight terminal-based CLI for automated scripts or a full-fledged broadcast workstation inspired by OBS Studio and DaVinci Resolve, you can choose and run the version that fits your workflow.

---

## 1. Version Comparison Matrix

| Capability / Feature | v1.0.0 (Stealth Foundation) | v1.1.0 (Dual Recording Engine) | v1.2.0 (Modern GUI & Tray) | v1.3.0 (Broadcast Studio & Glass) |
| :--- | :---: | :---: | :---: | :---: |
| **Primary Interface** | Interactive Terminal CLI | Interactive Terminal CLI | Fluent Dark Dashboard | Pro Broadcast Studio Console |
| **Android Mirroring (D3D11)** | ✅ | ✅ | ✅ | ✅ |
| **Direct-to-PC Camera Stream** | ✅ | ✅ | ✅ | ✅ |
| **UHID Hardware Touch Input** | ✅ | ✅ | ✅ | ✅ |
| **Wireless ADB (TCP/IP)** | ✅ | ✅ | ✅ | ✅ |
| **Dual Simultaneous Recording** | ❌ | ✅ (CLI Option `[7]`) | ✅ (Hero Card) | ✅ (Scene 1 Preset) |
| **Synchronized Stop (`Enter`)** | ❌ | ✅ | ✅ | ✅ (Esc / Space / GUI) |
| **Google Drive Virtual Path Upload** | ❌ | ✅ | ✅ | ✅ |
| **Windows System Tray Service** | ❌ | ❌ | ✅ | ✅ |
| **Global Windows Hotkeys** | ❌ | ❌ | ✅ (`Ctrl+Alt+D/M/C/R`) | ✅ (`Ctrl+Alt+D/M/C/R`) |
| **In-App Top Bar & Custom Menus** | ❌ | ❌ | ❌ | ✅ |
| **Windows 11 DWM Mica/Acrylic** | ❌ | ❌ | ❌ | ✅ (`DwmSetWindowAttribute`) |
| **DAW Audio Mixer & VU Meters** | ❌ | ❌ | ❌ | ✅ (dB scale & ballistics) |
| **Command Palette (`Ctrl+P`)** | ❌ | ❌ | ❌ | ✅ (Fuzzy Search) |
| **Two Complete Themes** | ❌ | ❌ | Dark Mode Only | Light Minimal & Dark Liquid Glass |
| **WCAG AA Contrast Verified** | ❌ | ❌ | ❌ | ✅ (100% compliant) |
| **Standalone Portable Size** | Script / CLI | Script / CLI | ~5.1 MB Portable | ~5.1 MB Portable |

---

## 2. Version Deep Dives: What Makes Each Release Unique

### [v1.3.0] — Broadcast Studio & Liquid Glass Architecture
* **Tag**: [`v1.3.0`](https://github.com/rajvisual/OmniCapture/releases/tag/v1.3.0)
* **Release Date**: November 2026
* **Target Audience**: Content creators, livestreamers, educators, and power users who need an OBS-tier production workstation.
* **Why This Version Exists**:
  - Eliminates clashing white Win32 title bars with a unified in-app Fluent top bar and DWM caption synchronization (`#0B0C10` / `#F3F4F6`, rounded corners, Mica backdrop).
  - Introduces professional DAW-style audio mixer channel strips with dB scale readouts (`-inf` to `0.0 dB`), volume sliders, and responsive VU level meters.
  - Adds two complete, contrast-verified themes: **Light Minimal** (solid, quiet, crisp surfaces with 16:1 text contrast) and **Dark Liquid Glass** (deep dark base with specular alpha highlights and DWM Mica).
  - Built-in Raycast/VSCode style Command Palette (`Ctrl+P`) for keyboard-first navigation.
  - Idle CPU usage optimized to **$< 0.8\%$** with zero recording frame drops.

---

### [v1.2.0] — Modern Windows 11 GUI Dashboard & System Tray
* **Tag**: [`v1.2.0`](https://github.com/rajvisual/OmniCapture/releases/tag/v1.2.0)
* **Release Date**: November 2026
* **Target Audience**: Desktop users wanting a simple, graphical point-and-click interface.
* **Why This Version Exists**:
  - The first graphical version of OmniCapture, powered by `customtkinter`.
  - Introduces the background System Tray icon with quick actions: start dual recording, launch mirror, open recordings folder, and exit.
  - Introduces system-wide global hotkeys (`Ctrl+Alt+D`, `Ctrl+Alt+M`, `Ctrl+Alt+C`, `Ctrl+Alt+R`).
  - First version packaged as a self-contained portable Windows `.exe` bundle (~5.1 MB).

---

### [v1.1.0] — Dual Simultaneous Recording Engine
* **Tag**: [`v1.1.0`](https://github.com/rajvisual/OmniCapture/releases/tag/v1.1.0)
* **Release Date**: November 2026
* **Target Audience**: Developers, educators, and automation engineers needing synchronized PC screen and mobile camera capture.
* **Why This Version Exists**:
  - Added world-first parallel recording of Windows PC screen (`gdigrab`) and Android camera sensor (`scrcpy`) into two independent, synchronized 60 FPS video files (`REC_PC_SCREEN_*.mp4` and `REC_MOBILE_CAMERA_*.mp4`).
  - Single keypress synchronized finalization (`Enter` or `Ctrl+C`).
  - Added ADB preflight diagnostics and automatic Camera2 hardware lock release.
  - Integrated Google Drive OAuth2 virtual path cloud uploader.

---

### [v1.0.0] — The Stealth Foundation
* **Tag**: [`v1.0.0`](https://github.com/rajvisual/OmniCapture/releases/tag/v1.0.0)
* **Release Date**: November 2026
* **Target Audience**: Minimalists, terminal lovers, and low-spec systems.
* **Why This Version Exists**:
  - Ultra-fast, lightweight CLI toolkit for direct Android screen mirroring and camera streaming.
  - Direct3D 11 rendering with sub-50ms latency.
  - Hardware UHID touch emulation without root.
  - Terminal interactive menu with zero GUI overhead.

---

## 3. How to Download & Run Any Version

### Portable Zero-Install Windows Package (Recommended)
1. Go to the [OmniCapture Releases Page on GitHub](https://github.com/rajvisual/OmniCapture/releases).
2. Choose the version you want (e.g. `v1.3.0` for the Broadcast Studio, or `v1.2.0` for the simpler dashboard).
3. Under **Assets**, download the portable zip:
   - `OmniCapture-v1.3.0-Windows-x64-Portable.zip`
4. Extract the folder anywhere on your PC (e.g. `C:\Tools\OmniCapture` or your Desktop).
5. Double-click `OmniCapture.exe` to launch immediately. No Python or dependencies required!

### Developer & Source Code Installation
If you prefer running from source or customizing the code:
```bash
# Clone the repository
git clone https://github.com/rajvisual/OmniCapture.git
cd OmniCapture

# Checkout the specific version tag you want to inspect
git checkout v1.3.0

# Install dependencies
pip install -r requirements.txt

# Run the studio interface
python omni.py gui
```
