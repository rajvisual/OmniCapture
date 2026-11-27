# Third-Party Software Notices and Attributions

OmniCapture bundles or links with several open-source libraries and utilities. We gratefully acknowledge the creators and maintainers of these projects:

---

### 1. scrcpy
- **Source**: https://github.com/Genymobile/scrcpy
- **Authors**: Genymobile and contributors
- **License**: Apache License 2.0
- **Usage**: Low-latency Direct3D 11 Android display mirroring, Camera2 stream capture, and UHID touch emulation.

### 2. Android Debug Bridge (ADB) / Platform-Tools
- **Source**: https://developer.android.com/tools/adb
- **Authors**: Google LLC
- **License**: Apache License 2.0
- **Usage**: Device discovery, USB/Wi-Fi transport layer, hardware telemetry polling, and camera lock release.

### 3. CustomTkinter
- **Source**: https://github.com/TomSchimansky/CustomTkinter
- **Author**: Tom Schimansky
- **License**: MIT License / Creative Commons Zero
- **Usage**: Presentation layer, dark/light theme tokens, and custom UI components.

### 4. Pillow (PIL Fork)
- **Source**: https://github.com/python-pillow/Pillow
- **Authors**: Jeffrey A. Clark (Alex) and contributors
- **License**: HPND License (Historical Permission Notice and Disclaimer)
- **Usage**: Image loading, icon rasterization, and frosted glass snapshot processing.

### 5. pystray
- **Source**: https://github.com/moses-palmer/pystray
- **Author**: Moses Palmer
- **License**: GNU Lesser General Public License v3.0 (LGPL-3.0)
- **Usage**: Windows system tray notification area icon, background execution, and tray context menus.

### 6. FFmpeg (External Dependency)
- **Source**: https://ffmpeg.org
- **License**: GNU Lesser General Public License (LGPL) / GNU General Public License (GPL)
- **Notice**: FFmpeg is **NOT** bundled inside the OmniCapture repository. It is an optional external dependency installed by the user (e.g. via `winget install Gyan.FFmpeg`) or placed inside `bin/ffmpeg.exe`. OmniCapture invokes FFmpeg as an independent subprocess via command-line arguments without static or dynamic code linkage.
