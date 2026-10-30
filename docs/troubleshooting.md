# Troubleshooting Guide

This guide covers common issues, error codes, and step-by-step solutions for **OmniCapture**.

---

## 🔍 Issue Matrix

| Symptom / Error | Cause | Resolution |
|---|---|---|
| **No devices detected** | USB Debugging disabled or bad cable | Enable USB debugging; check cable; run `python omni.py info` |
| **Device unauthorized** | RSA prompt not accepted on phone | Unlock phone screen and tap "Always allow from this computer" |
| **Touch clicks ignored on Xiaomi/POCO** | MIUI/HyperOS security block | Turn on `USB debugging (Security settings)` or run with `--uhid` |
| **`MediaCodec Error 0xfffffff4`** | Phone GPU encoder overwhelmed by high resolution | Use `--max-size=1200` (set as default in `config.json`) |
| **Audio playback disabled on Android 12** | Android system limitation | Audio playback capture requires Android 13+; use `--audio-source=mic` |
| **Google Drive virtual drive not found** | Google Drive for Desktop not running | Start Google Drive app or set custom sync path in `drive-setup` |
| **PowerShell script execution error** | ExecutionPolicy restriction | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` |

---

## 📱 Device Connection Issues

### 1. `adb: cannot connect to daemon` or No Device Found
- Ensure your phone is connected with a data-capable USB cable (some charging cables do not carry data).
- Ensure **USB Debugging** is turned ON in **Settings** > **Developer Options**.
- Try switching USB ports (use a direct motherboard port on PC rather than an unpowered USB hub).

### 2. Device Status Shows `unauthorized`
When running `python omni.py info`, if the device state shows `unauthorized`:
1. Disconnect the USB cable.
2. In your phone's **Developer Options**, tap **Revoke USB debugging authorizations**.
3. Reconnect the USB cable.
4. Unlock your phone and look at the screen.
5. Check the box **"Always allow from this computer"** and tap **OK**.

---

## 🖱️ Touch & Keyboard Input Issues

### 3. Mouse Clicks and Typing Do Not Respond on Phone
If the screen mirror displays on PC, but clicking with the mouse does not touch apps on the phone:

#### For Xiaomi, POCO, and Redmi Devices:
Xiaomi adds a secondary security lock in MIUI and HyperOS that specifically blocks touch injection over USB:
```text
java.lang.SecurityException: Injecting to another application requires INJECT_EVENTS permission
```

**Solution A (Permanent Phone Setting)**:
1. Open phone **Settings** > **Additional settings** > **Developer options**.
2. Under **Debugging**, turn **ON**:
   👉 **`USB debugging (Security settings)`** *(Allow granting permissions and simulating input via USB debugging)*.
3. Accept the 3 countdown security prompts (*Next ➔ Next ➔ Accept*).

**Solution B (Bypass Lock via Hardware HID Mode)**:
If you cannot toggle the phone setting (e.g. no SIM card installed), launch OmniCapture with the `--uhid` flag:
```powershell
python omni.py mirror --uhid
```
OmniCapture will simulate an actual hardware USB mouse directly at the Linux kernel level, bypassing Xiaomi's permission restriction.

---

## 🎥 Video Encoding & Performance Issues

### 4. Video Freezes or Stutters
1. **Reduce Resolution**: If your phone uses an entry-level processor (e.g. Snapdragon 600-series or MediaTek Helio), native 1080×2340 encoding can drop frames. Set `--max-size=1200` in `config.json` or pass `--size`:
   ```powershell
   python omni.py mirror --size 1200
   ```
2. **Wi-Fi Jitter**: If streaming over Wi-Fi, ensure your phone and PC are connected to a 5GHz Wi-Fi band, or switch to a direct USB cable for rock-solid performance.

### 5. `Cannot request to turn screen off if control is disabled`
This error occurs in stock scrcpy when `--turn-screen-off` is passed during camera mode (`--video-source=camera`). OmniCapture automatically filters out incompatible flags and handles stealth screen darkening via low-level ADB sleep keyevents (`KEYCODE_SLEEP`).

---

## ☁️ Cloud Sync Issues

### 6. `Google Drive Desktop virtual drive not detected`
- If you use Google Drive for Desktop, ensure the application is running in your Windows taskbar system tray.
- If your Google Drive is mapped to a drive letter other than `G:` (e.g. `H:` or a custom folder):
  1. Run:
     ```powershell
     python omni.py drive-setup
     ```
  2. Select `[2] Set Custom Google Drive / Sync Folder Path`.
  3. Enter your exact sync directory (e.g. `H:\My Drive\OmniCapture`).
