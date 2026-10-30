# Configuration Guide

OmniCapture stores application preferences and cloud sync settings in a local JSON configuration file named `config.json`.

A template with safe defaults is provided as `config.example.json`.

---

## ⚙️ Configuration Schema (`config.json`)

```json
{
  "scrcpy_dir": "bin",
  "recordings_dir": "recordings",
  "default_record_format": "mp4",
  "default_camera_facing": "back",
  "default_camera_fps": 30,
  "default_camera_size": "",
  "max_size": 1200,
  "video_bit_rate": "8M",
  "max_fps": 60,
  "screen_off_during_capture": true,
  "stay_awake": false,
  "audio_source": "mic",
  "google_drive": {
    "enabled": false,
    "method": "desktop",
    "folder_id": "",
    "credentials_file": "client_secrets.json",
    "token_file": "drive_token.json",
    "desktop_sync_path": ""
  }
}
```

---

## 📖 Parameter Reference

### General Engine Settings

| Setting | Type | Default | Description |
|---|---|---|---|
| `scrcpy_dir` | string | `"bin"` | Directory containing `adb.exe`, `scrcpy.exe`, and server binaries. Relative paths are resolved against the project root. |
| `recordings_dir` | string | `"recordings"` | Local folder where finished video recordings are stored. |
| `default_record_format` | string | `"mp4"` | Default container format for recordings (`"mp4"` or `"mkv"`). |
| `max_size` | integer | `1200` | Maximum dimension (width or height) for display encoding. `1200` provides an optimal balance of crisp quality and 60 FPS zero-lag encoding on mobile processors. |
| `video_bit_rate` | string | `"8M"` | Video encoder bitrate (e.g. `"8M"` = 8 Mbps, `"16M"` = 16 Mbps). |
| `max_fps` | integer | `60` | Target framerate limit. Set to `60` or `30`. |
| `screen_off_during_capture` | boolean | `true` | When `true`, automatically sends a sleep keyevent (`KEYCODE_SLEEP`) via ADB to keep the physical phone screen dark during camera capture. |
| `stay_awake` | boolean | `false` | Keeps device awake when plugged in. Set to `false` on Xiaomi/MIUI to avoid `WRITE_SECURE_SETTINGS` permission warnings. |
| `audio_source` | string | `"mic"` | Audio capture source for recordings. Options: `"mic"` (captures microphone) or `"playback"` (captures device system audio, Android 13+ only). |

### Camera Settings

| Setting | Type | Default | Description |
|---|---|---|---|
| `default_camera_facing` | string | `"back"` | Default camera sensor (`"back"`, `"front"`, or `"external"`). |
| `default_camera_fps` | integer | `30` | Default capture framerate for camera streaming. |
| `default_camera_size` | string | `""` | Explicit capture resolution (e.g. `"1920x1080"`, `"3840x2160"`). Leave blank to use sensor native resolution. |

---

## ☁️ Google Drive Cloud Settings

OmniCapture supports two cloud sync methods:

### Method 1: Google Drive for Desktop Sync (`"method": "desktop"`)
The fastest and simplest integration. When the official Google Drive for Desktop application is running on Windows, it mounts a virtual drive letter (such as `G:\My Drive` or `H:\My Drive`).

- `desktop_sync_path`: Leave empty to allow OmniCapture to auto-detect your virtual drive, or specify an exact path:
  ```json
  "desktop_sync_path": "G:\\My Drive\\OmniCapture"
  ```
- As soon as a recording completes, OmniCapture copies the file into this folder, and Google Drive handles the cloud upload in the background.

### Method 2: Direct Google Drive API (`"method": "api"`)
Direct cloud uploads over HTTPS using Google's Drive v3 REST API.

- `credentials_file`: Path to your Google Cloud OAuth 2.0 client secret JSON (default: `client_secrets.json`).
- `token_file`: Location where the authenticated user token is cached (default: `drive_token.json`).
- `folder_id`: Optional Google Drive folder ID. If omitted, OmniCapture automatically searches for or creates an `OmniCapture Recordings` folder in your root drive.

---

## 🔒 Security Best Practices

1. **Never commit personal paths or credentials**: Always keep `client_secrets.json` and `drive_token.json` in your local project folder. They are automatically ignored by `.gitignore`.
2. **Use `config.example.json` for commits**: If you add new configuration keys, document them in `config.example.json` with safe, generic placeholder values.
