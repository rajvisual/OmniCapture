import time
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

class SimulatedADBManager:
    """
    Developer-only Simulated Android Device Engine for OmniCapture Studio.
    Provides identical interface to ADBManager without requiring physical USB hardware.
    
    Supported Emulated States:
    - 'no_device': Disconnected state
    - 'scanning': ADB discovery polling
    - 'connecting': Handshake in progress
    - 'unauthorized': Phone prompting user with RSA fingerprint dialog
    - 'connected_usb': High-speed USB 3.0 DirectShow/Camera2 link (POCO X6 Pro)
    - 'connected_wifi': 5GHz Wi-Fi ADB connection (192.168.1.155:5555)
    - 'camera_locked': Camera2 sensor held by com.google.android.GoogleCamera
    - 'battery_low': Critical 12% battery alert
    - 'battery_good': Normal 88% charging state
    - 'unplugged_mid_recording': Sudden bus disconnect during active capture
    - 'slow_response': High latency simulation (1.5s delay)
    - 'failure': Simulated USB hub I/O error
    """

    STATES = [
        "no_device",
        "scanning",
        "connecting",
        "unauthorized",
        "connected_usb",
        "connected_wifi",
        "camera_locked",
        "battery_low",
        "battery_good",
        "unplugged_mid_recording",
        "slow_response",
        "failure",
        "upload_failed",
        "upload_done",
        "scrcpy_missing",
        "adb_missing",
        "engine_crashed"
    ]

    def __init__(self, initial_state: str = "connected_usb"):
        self.state = initial_state if initial_state in self.STATES else "connected_usb"
        self.is_simulated = True
        self.adb_path = Path("bin/adb.exe")
        self._camera_lock_active = (initial_state == "camera_locked")
        self._battery_level = 12 if initial_state == "battery_low" else 88
        self._on_state_change_cb = None

    def set_state_change_callback(self, cb):
        self._on_state_change_cb = cb

    def set_state(self, new_state: str):
        if new_state in self.STATES:
            self.state = new_state
            self._camera_lock_active = (new_state == "camera_locked")
            if new_state == "battery_low":
                self._battery_level = 12
            elif new_state in ("battery_good", "connected_usb", "connected_wifi"):
                self._battery_level = 88
            if self._on_state_change_cb:
                self._on_state_change_cb(new_state)

    def is_available(self) -> bool:
        return self.state not in ("failure", "adb_missing")

    def get_adb_version(self) -> Optional[str]:
        if self.state in ("failure", "adb_missing"):
            return None
        return "Android Debug Bridge version 1.0.41 (Simulated Device Engine v1.4.0)"

    def list_devices(self) -> List[Dict[str, Any]]:
        if self.state in ("no_device", "scanning", "failure", "unplugged_mid_recording", "adb_missing", "engine_crashed"):
            return []

        if self.state == "connecting":
            return [{
                "id": "SIM_DEVICE_01",
                "state": "connecting",
                "model": "POCO X6 Pro",
                "is_wireless": False,
                "raw": "SIM_DEVICE_01 connecting product:duchamp model:POCO_X6_Pro"
            }]

        if self.state == "unauthorized":
            return [{
                "id": "SIM_DEVICE_01",
                "state": "unauthorized",
                "model": "POCO X6 Pro (Unauthorized)",
                "is_wireless": False,
                "raw": "SIM_DEVICE_01 unauthorized usb:1-1"
            }]

        if self.state == "connected_wifi":
            return [{
                "id": "192.168.1.155:5555",
                "state": "device",
                "model": "POCO X6 Pro (Wi-Fi)",
                "is_wireless": True,
                "raw": "192.168.1.155:5555 device product:duchamp model:POCO_X6_Pro"
            }]

        # All other connected states (connected_usb, camera_locked, battery_low, battery_good, slow_response)
        return [{
            "id": "SIM_USB_DUCHAMP_01",
            "state": "device",
            "model": "POCO X6 Pro",
            "is_wireless": False,
            "raw": "SIM_USB_DUCHAMP_01 device product:duchamp model:POCO_X6_Pro device:duchamp transport_id:1"
        }]

    def get_device_properties(self, device_id: Optional[str] = None) -> Dict[str, str]:
        if self.state in ("no_device", "unauthorized", "failure"):
            return {
                "android_version": "Unknown",
                "sdk_version": "Unknown",
                "model": "Unknown",
                "manufacturer": "Unknown",
                "brand": "Unknown"
            }
        return {
            "android_version": "14 (HyperOS 1.0.8.0.UNLMIXM)",
            "sdk_version": "34",
            "model": "POCO X6 Pro",
            "manufacturer": "Xiaomi",
            "brand": "POCO"
        }

    def get_battery_info(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        if self.state in ("no_device", "failure"):
            return {"level": None, "scale": 100, "status": "Unknown", "ac_powered": False}
        is_charging = self.state != "battery_low" and self.state != "connected_wifi"
        return {
            "level": self._battery_level,
            "scale": 100,
            "status": "Charging" if is_charging else "Discharging",
            "ac_powered": is_charging
        }

    def get_wifi_ip(self, device_id: Optional[str] = None) -> Optional[str]:
        if self.state in ("connected_wifi", "connected_usb", "camera_locked", "battery_good"):
            return "192.168.1.155"
        return None

    def check_camera_lock(self, device_id: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        if self._camera_lock_active or self.state == "camera_locked":
            return True, "com.google.android.GoogleCamera (Camera2 Client PID 8412)"
        return False, None

    def release_camera_lock(self, device_id: Optional[str] = None) -> bool:
        self._camera_lock_active = False
        if self.state == "camera_locked":
            self.state = "connected_usb"
        return True

    def preflight_check(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        if self.state == "slow_response":
            time.sleep(1.2)

        if self.state == "scrcpy_missing":
            return {
                "ok": False,
                "error_type": "SCRCPY_MISSING",
                "message": "Scrcpy binary not found in system PATH or bin/ folder.",
                "remedy": "Ensure scrcpy.exe exists in bin/ or run the installer."
            }

        if self.state == "adb_missing":
            return {
                "ok": False,
                "error_type": "ADB_MISSING",
                "message": "ADB binary not found in system PATH or bin/ folder.",
                "remedy": "Install Android SDK Platform-Tools or copy adb.exe to bin/."
            }

        if self.state == "engine_crashed":
            return {
                "ok": False,
                "error_type": "ENGINE_CRASHED",
                "message": "Subprocess capture worker exited unexpectedly with code 0xC0000005.",
                "remedy": "Restart capture engine to re-initialize graphics pipeline."
            }

        if self.state == "failure":
            return {
                "ok": False,
                "error_type": "BUS_RESET_ERROR",
                "message": "Simulated hardware I/O bus reset error.",
                "remedy": "Disconnect and reconnect the USB data cable."
            }

        if self.state == "unauthorized":
            return {
                "ok": False,
                "error_type": "UNAUTHORIZED",
                "message": "Device unauthorized: RSA confirmation prompt pending on phone screen.",
                "remedy": "Unlock your phone and tap 'Allow USB Debugging' (check 'Always allow')."
            }

        if self.state in ("no_device", "scanning"):
            return {
                "ok": False,
                "error_type": "NO_DEVICE",
                "message": "No Android device detected on USB or Wi-Fi bus.",
                "remedy": "Connect phone via USB cable and ensure USB debugging is enabled."
            }

        if self._camera_lock_active:
            return {
                "ok": False,
                "error_type": "CAMERA_LOCKED",
                "message": "Mobile Camera2 hardware is held by com.google.android.GoogleCamera.",
                "remedy": "Close the camera app on your phone or click 'Release Camera Lock'."
            }

        return {
            "ok": True,
            "error_type": None,
            "message": "Simulated device ready for capture.",
            "remedy": None
        }

    def wake_screen(self, device_id: Optional[str] = None) -> bool:
        return True

    def enable_wireless(self, device_id: Optional[str] = None) -> Tuple[bool, str]:
        self.state = "connected_wifi"
        return True, "192.168.1.155:5555"

    def disconnect_wireless(self, ip_port: Optional[str] = None) -> Tuple[bool, str]:
        self.state = "connected_usb"
        return True, "Disconnected wireless ADB"
