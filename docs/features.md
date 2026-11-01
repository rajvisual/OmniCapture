# OmniCapture Feature Deep-Dive

This document provides a detailed technical and operational breakdown of all verified features in **OmniCapture**.

---

## 📱 1. Display Mirroring & Full Remote Control

### Overview
OmniCapture streams your Android device's screen to a low-latency, hardware-accelerated Direct3D 11 desktop window. It supports full bidirectional interaction: your PC mouse acts as a touchscreen, and your PC keyboard acts as a physical hardware keyboard.

### How It Works
- The server captures display compositor framebuffers via Android's internal `SurfaceControl` API.
- Frames are encoded in real-time by the mobile device's hardware `MediaCodec` encoder and transmitted over USB or Wi-Fi.
- On the PC, frames are decoded using `libavcodec` and rendered via `SDL2` and `Direct3D 11` with sub-35ms latency.

### Input Gestures
- **Tap**: Left-click on any app, icon, or button.
- **Swipe / Scroll**: Click and drag in any direction.
- **Smooth Scroll**: Vertical mouse scroll wheel natively scrolls lists, feeds, and chats.
- **Long Press**: Click and hold the left mouse button.
- **Back Button**: Right-click anywhere in the window.
- **Home Button**: Middle-click (press the mouse scroll wheel).
- **Recent Apps**: Press `[Alt + S]` or use secondary mouse side buttons.
- **Pinch-to-Zoom**: Hold `Ctrl` + Left-click and drag.
- **Typing**: Click into any text field and type directly using your PC keyboard.
- **Clipboard Sync**: `Ctrl + C` on PC ➔ `Ctrl + V` on phone.

### Hardware HID Mode (`--uhid`)
On devices with strict remote touch policies (such as Xiaomi MIUI and HyperOS), standard ADB touch injection can be blocked by the OS. OmniCapture includes a dedicated Hardware HID mode (`--uhid`):
- Communicates directly with the Linux kernel `/dev/uhid` character device.
- Emulates a physical USB mouse and keyboard at the hardware level.
- Bypasses Android's `INJECT_EVENTS` security permission restrictions.

---

## 📷 2. Stealth Background Camera Capture

### Overview
Streams high-definition video directly from your phone's camera sensors without opening the mobile camera application on the device.

### How It Works
- Traditional camera applications launch a heavy GUI Activity, inflate a camera viewfinder surface, and turn on the device display.
- OmniCapture accesses Android's low-level `android.hardware.camera2.CameraManager` API directly from a system shell context.
- Raw camera frames are piped straight into the mobile GPU's video encoder without rendering anything to the phone screen.
- **The phone screen remains off or locked.**
- **No camera app opens on screen.**
- **No recent app entry is created.**
- Microphone audio is captured simultaneously using `--audio-source=mic`.

### Sensor Selection
OmniCapture can target any hardware camera sensor on the device:
- Back Main Sensor (`--facing back`)
- Front Selfie Sensor (`--facing front`)
- Ultra-wide, macro, and auxiliary sensors via explicit ID (`--camera-id=...`). Run `python omni.py info` to view all available camera IDs on your phone.

---

## 🔴 3. Unlimited Direct-to-PC Recording

### Overview
Records hours of continuous screen or camera video without filling your phone's internal storage or causing thermal throttling.

### Key Benefits
- **Zero Phone Storage Usage**: Video data is written directly to your PC hard drive (`recordings/`).
- **Cooler Operation**: Eliminates device heat caused by writing heavy high-bitrate video files to mobile flash storage (eMMC/UFS).
- **Format Options**:
  - **MP4**: Maximum compatibility with web players, video editors, and mobile devices.
  - **MKV**: Crash-resilient container. If a cable is accidentally unplugged or power is interrupted mid-session, MKV files remain playable up to the last captured frame.

---

## ⌨️ 4. Keyboard Hotkeys

OmniCapture configures **`Left-Alt`** as the dedicated shortcut modifier across all active streaming and recording windows:

| Shortcut | Action | Description |
|---|---|---|
| **`[Alt + Z]`** | ⏸️ Pause Video | Pauses / freezes video stream transmission |
| **`[Alt + Shift + Z]`** | ▶️ Resume Video | Resumes real-time video transmission |
| **`[Alt + O]`** | 🌑 Turn Screen OFF | Turns physical phone display black while streaming continues |
| **`[Alt + Shift + O]`** | 💡 Turn Screen ON | Restores physical phone display |
| **`[Alt + F]`** | 🖥️ Fullscreen | Toggles borderless fullscreen mode |
| **`[Alt + H]`** | 🏠 Home | Simulates Android Home button |
| **`[Alt + B]`** | 🔙 Back | Simulates Android Back button |
| **`[Alt + S]`** | 📑 Recent Apps | Opens Android App Switcher |
| **`[Alt + P]`** | ⚡ Power Button | Toggles device sleep / wake state |
| **`[Alt + Up / Down]`** | 🔊 Volume Control | Adjusts device volume |
| **`[Alt + R]`** | 🔄 Rotate Screen | Rotates device display orientation |
| **`[Ctrl + C]` / Close** | 🛑 Stop Recording | Ends recording session and triggers cloud upload |

---

## 🔄 5. Dual Mode (Picture-in-Picture)

### Overview
Launches two synchronized, independent windows: one streaming the interactive phone display and the other streaming the live stealth camera feed.

### Common Use Cases
- Demonstration videos and tutorials.
- Mobile game streaming with facecam.
- Live testing and QA verification.

---

## 🔴 6. Dual Simultaneous Recording (PC Screen + Mobile Camera)

### Overview
Simultaneously records both your **Windows PC Screen** and your **Android Mobile Camera** concurrently, saving both streams into **two separate, independent video files** in real-time.

```text
OmniCapture Dual Recording Session
├── recordings/REC_PC_SCREEN_20261101_090000.mp4      (Full PC Desktop via FFmpeg)
└── recordings/REC_MOBILE_CAMERA_20261101_090000.mp4  (Stealth Android Camera via scrcpy)
```

### Key Advantages
- **Two Separate Raw Tracks**: Content creators, educators, and gamers can edit, reframe, crop, color-grade, and position their PC gameplay/work and webcam feed independently in editing software (Premiere Pro, DaVinci Resolve, CapCut).
- **Zero Loss from Picture-in-Picture Embedding**: Unlike standard screen recorders that bake the webcam into a fixed corner box, dual separate files retain 100% of the screen under the camera.
- **Synchronous Session Timing**: Both streams start and stop simultaneously via a single coordinated command (`Ctrl + C` or `Enter`), ensuring perfect audio/video timeline alignment.
- **Stealth Mobile Operation**: While recording, the phone screen powers off automatically (`KEYCODE_SLEEP`), preserving battery and preventing overheating.
- **Dual Cloud Auto-Upload**: If Google Drive synchronization is enabled, both files are queued and uploaded to Google Drive upon session completion.

### Usage
```powershell
# Interactive CLI launcher
python omni.py dual-record

# Custom frame rates and front selfie camera
python omni.py dual-record --facing front --pc-fps 60 --camera-fps 30

# Background silent camera capture with automatic Google Drive upload
python omni.py dual-record --no-camera-playback --upload
```

---

## ☁️ 7. Automated Cloud Synchronization

### Option A: Google Drive for Desktop Sync
- Inspects mounted drive letters (`G:`, `H:`, etc.) for `My Drive`.
- Automatically copies completed recordings into `G:\My Drive\OmniCapture\`.
- Windows handles background cloud synchronization without requiring API keys or authentication tokens.

### Option B: Google Drive REST API v3
- Authenticates using Google OAuth 2.0 with the `drive.file` scope.
- Implements a resumable 5MB chunked uploader with live terminal progress reporting.
- Creates an `OmniCapture Recordings` cloud folder automatically and outputs shareable web links.

---

## 📶 8. Wireless Wi-Fi ADB Mode

- Detects the local IP address assigned to your phone's Wi-Fi network interface (`wlan0`).
- Automatically restarts ADB in TCP mode (`adb tcpip 5555`) and establishes a TCP connection (`adb connect <ip>:5555`).
- Allows you to disconnect the USB cable and continue streaming or recording wirelessly.
