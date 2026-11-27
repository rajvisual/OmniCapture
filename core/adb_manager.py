import os
import re
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

class ADBManager:
    def __init__(self, scrcpy_dir: str):
        self.scrcpy_dir = Path(scrcpy_dir)
        self.adb_path = self._resolve_adb_path()

    def _resolve_adb_path(self) -> Path:
        """Find adb.exe inside local project bin/ or configured path."""
        base_bin = Path(__file__).resolve().parent.parent / "bin" / "adb.exe"
        candidates = [
            base_bin,
            self.scrcpy_dir / "adb.exe",
            self.scrcpy_dir / "scrcpy-win64-v3.3.4" / "adb.exe",
            self.scrcpy_dir.parent / "adb.exe",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        # Fallback to system adb
        return Path("adb.exe")

    def _run_cmd(self, args: List[str], timeout: int = 10) -> Tuple[int, str, str]:
        """Execute ADB command and return (exit_code, stdout, stderr)."""
        cmd = [str(self.adb_path)] + args
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                encoding="utf-8",
                errors="replace"
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except FileNotFoundError:
            return -1, "", f"ADB binary not found at: {self.adb_path}"
        except Exception as e:
            return -1, "", str(e)

    def is_available(self) -> bool:
        """Check if adb executable exists and can run."""
        if not self.adb_path.is_file() and self.adb_path.name == "adb.exe":
            # Check if system adb can be invoked
            code, _, _ = self._run_cmd(["version"], timeout=3)
            return code == 0
        return self.adb_path.is_file()

    def get_adb_version(self) -> Optional[str]:
        """Get the ADB version string."""
        code, out, _ = self._run_cmd(["version"], timeout=5)
        if code == 0 and out:
            first_line = out.splitlines()[0].strip()
            return first_line
        return None

    def list_devices(self) -> List[Dict[str, Any]]:
        """List all connected ADB devices with detailed info."""
        code, out, _ = self._run_cmd(["devices", "-l"])
        if code != 0 or not out:
            return []

        devices = []
        lines = out.splitlines()
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                dev_id = parts[0]
                state = parts[1]
                model = "Unknown"
                model_match = re.search(r"model:([^\s]+)", line)
                if model_match:
                    model = model_match.group(1).replace("_", " ")

                is_wireless = ":" in dev_id
                devices.append({
                    "id": dev_id,
                    "state": state,
                    "model": model,
                    "is_wireless": is_wireless,
                    "raw": line
                })
        return devices

    def get_device_properties(self, device_id: Optional[str] = None) -> Dict[str, str]:
        """Query detailed system properties from an Android device."""
        props = {
            "android_version": "Unknown",
            "sdk_version": "Unknown",
            "model": "Unknown",
            "manufacturer": "Unknown",
            "brand": "Unknown"
        }
        if not device_id:
            return props

        args = ["-s", device_id, "shell", "getprop"]
        code, out, _ = self._run_cmd(args, timeout=5)
        if code == 0 and out:
            for line in out.splitlines():
                if "[ro.build.version.release]:" in line:
                    match = re.search(r":\s*\[([^\]]+)\]", line)
                    if match:
                        props["android_version"] = match.group(1)
                elif "[ro.build.version.sdk]:" in line:
                    match = re.search(r":\s*\[([^\]]+)\]", line)
                    if match:
                        props["sdk_version"] = match.group(1)
                elif "[ro.product.model]:" in line:
                    match = re.search(r":\s*\[([^\]]+)\]", line)
                    if match:
                        props["model"] = match.group(1)
                elif "[ro.product.manufacturer]:" in line:
                    match = re.search(r":\s*\[([^\]]+)\]", line)
                    if match:
                        props["manufacturer"] = match.group(1)
                elif "[ro.product.brand]:" in line:
                    match = re.search(r":\s*\[([^\]]+)\]", line)
                    if match:
                        props["brand"] = match.group(1)
        return props

    def preflight_check(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Comprehensive preflight diagnostic check before launching any Android operation.
        Returns state dictionary:
          - status: 'DEVICE CONNECTED' | 'DEVICE UNAUTHORIZED' | 'DEVICE OFFLINE' | 'NO DEVICE FOUND' | 'ADB NOT FOUND'
          - adb_path: Path
          - adb_version: str
          - device_id: Optional[str]
          - state: Optional[str]
          - properties: Dict[str, str]
          - is_wireless: bool
          - devices: List[Dict[str, Any]]
          - message: str
        """
        # 1. Verify ADB binary
        if not self.is_available():
            return {
                "status": "ADB NOT FOUND",
                "adb_path": self.adb_path,
                "adb_version": None,
                "device_id": None,
                "state": None,
                "properties": {},
                "is_wireless": False,
                "devices": [],
                "message": f"ADB executable not found at {self.adb_path}."
            }

        adb_ver = self.get_adb_version() or "Unknown ADB Version"
        devices = self.list_devices()

        # 2. Check device list
        if not devices:
            return {
                "status": "NO DEVICE FOUND",
                "adb_path": self.adb_path,
                "adb_version": adb_ver,
                "device_id": None,
                "state": None,
                "properties": {},
                "is_wireless": False,
                "devices": [],
                "message": "No Android devices detected by ADB. Connect your device via USB with USB Debugging enabled."
            }

        # 3. Resolve target device
        target = None
        if device_id:
            for d in devices:
                if d["id"] == device_id:
                    target = d
                    break
        if not target:
            # Auto-prioritize authorized USB devices
            ready_usb = [d for d in devices if not d["is_wireless"] and d["state"] == "device"]
            if ready_usb:
                target = ready_usb[0]
            else:
                # Any ready device
                ready_any = [d for d in devices if d["state"] == "device"]
                if ready_any:
                    target = ready_any[0]
                else:
                    # Pick first device (unauthorized or offline)
                    target = devices[0]

        target_id = target["id"]
        target_state = target["state"]
        is_wireless = target.get("is_wireless", ":" in target_id)

        # 4. Determine status based on device state
        if target_state == "unauthorized":
            return {
                "status": "DEVICE UNAUTHORIZED",
                "adb_path": self.adb_path,
                "adb_version": adb_ver,
                "device_id": target_id,
                "state": target_state,
                "properties": {},
                "is_wireless": is_wireless,
                "devices": devices,
                "message": f"Device [{target_id}] is connected but UNAUTHORIZED. Unlock phone and tap 'Allow USB Debugging'."
            }
        elif target_state == "offline":
            return {
                "status": "DEVICE OFFLINE",
                "adb_path": self.adb_path,
                "adb_version": adb_ver,
                "device_id": target_id,
                "state": target_state,
                "properties": {},
                "is_wireless": is_wireless,
                "devices": devices,
                "message": f"Device [{target_id}] is OFFLINE. Re-plug USB cable or restart device."
            }
        elif target_state != "device":
            return {
                "status": "NO DEVICE FOUND",
                "adb_path": self.adb_path,
                "adb_version": adb_ver,
                "device_id": target_id,
                "state": target_state,
                "properties": {},
                "is_wireless": is_wireless,
                "devices": devices,
                "message": f"Device [{target_id}] is in unexpected state: '{target_state}'."
            }

        # Device is connected and authorized
        props = self.get_device_properties(target_id)
        return {
            "status": "DEVICE CONNECTED",
            "adb_path": self.adb_path,
            "adb_version": adb_ver,
            "device_id": target_id,
            "state": target_state,
            "properties": props,
            "is_wireless": is_wireless,
            "devices": devices,
            "message": f"Device [{target_id}] is connected and authorized."
        }

    def print_preflight_card(self, check: Dict[str, Any]):
        """Format and print an informative preflight diagnostic card."""
        status = check.get("status", "UNKNOWN")
        if status == "DEVICE CONNECTED":
            props = check.get("properties", {})
            model = props.get("model") or "Android Device"
            brand = props.get("brand") or ""
            os_ver = props.get("android_version", "N/A")
            conn = "Wi-Fi (TCP/IP)" if check.get("is_wireless") else "USB Cable"
            print(f"\033[1;32m[✓] PREFLIGHT OK: {brand.upper()} {model} | Android {os_ver} | {conn} ({check.get('device_id')})\033[0m")
        elif status == "DEVICE UNAUTHORIZED":
            print("\n\033[1;33m" + "=" * 70)
            print("  ⚠️  PREFLIGHT WARNING: ANDROID DEVICE UNAUTHORIZED")
            print("=" * 70 + "\033[0m")
            print(f"  Device Serial:  \033[1m{check.get('device_id')}\033[0m")
            print(f"  ADB Binary:     {check.get('adb_path')}")
            print("\n  \033[1mACTION REQUIRED ON PHONE SCREEN:\033[0m")
            print("  1. Unlock your phone screen.")
            print("  2. Look for the prompt: \033[1;36m'Allow USB debugging?'\033[0m")
            print("  3. Check \033[1m'Always allow from this computer'\033[0m and tap \033[1;32m'Allow'\033[0m.")
            print("\033[1;33m" + "=" * 70 + "\033[0m\n")
        elif status == "NO DEVICE FOUND":
            print("\n\033[1;31m" + "=" * 70)
            print("  ❌ PREFLIGHT ERROR: NO ANDROID DEVICE DETECTED")
            print("=" * 70 + "\033[0m")
            print(f"  ADB Binary:  {check.get('adb_path')}")
            print(f"  ADB Version: {check.get('adb_version')}")
            print("\n  \033[1mPLEASE CHECK:\033[0m")
            print("  1. Is your phone connected to this PC using a USB data cable?")
            print("  2. Is \033[1;36mDeveloper Options\033[0m enabled on the phone?")
            print("  3. Is \033[1;36mUSB Debugging\033[0m turned ON in Developer Options?")
            print("  4. If using Wi-Fi ADB, run option [9] or 'python omni.py wireless'.")
            print("\033[1;31m" + "=" * 70 + "\033[0m\n")
        elif status == "ADB NOT FOUND":
            print("\n\033[1;31m" + "=" * 70)
            print("  ❌ PREFLIGHT ERROR: ADB EXECUTABLE MISSING")
            print("=" * 70 + "\033[0m")
            print(f"  Expected Path: {check.get('adb_path')}")
            print("  Please ensure bin/adb.exe exists or install platform-tools.")
            print("\033[1;31m" + "=" * 70 + "\033[0m\n")
        else:
            print(f"\n\033[1;31m[!] Preflight Issue: {check.get('message')}\033[0m\n")

    def get_battery_info(self, device_id: Optional[str] = None) -> Dict[str, str]:
        """Fetch device battery percentage and status."""
        args = ["shell", "dumpsys", "battery"]
        if device_id:
            args = ["-s", device_id] + args
        code, out, _ = self._run_cmd(args)
        if code != 0 or not out:
            return {"level": "Unknown", "status": "Unknown", "powered": "Unknown"}

        info = {}
        for line in out.splitlines():
            line = line.strip()
            if "level:" in line:
                info["level"] = line.split(":", 1)[1].strip() + "%"
            elif "status:" in line:
                # 2: charging, 3: discharging, 4: not charging, 5: full
                st_code = line.split(":", 1)[1].strip()
                st_map = {"2": "Charging", "3": "Discharging", "4": "Not Charging", "5": "Full"}
                info["status"] = st_map.get(st_code, "Unknown")
            elif "AC powered:" in line or "USB powered:" in line or "Wireless powered:" in line:
                if "true" in line:
                    info["powered"] = line.split(":", 1)[0].replace("powered", "").strip()

        return {
            "level": info.get("level", "N/A"),
            "status": info.get("status", "N/A"),
            "powered": info.get("powered", "Battery")
        }

    def get_wifi_ip(self, device_id: Optional[str] = None) -> Optional[str]:
        """Detect the Android device's local Wi-Fi IP address."""
        # Try ip route first
        args = ["shell", "ip", "route"]
        if device_id:
            args = ["-s", device_id] + args
        code, out, _ = self._run_cmd(args)
        if code == 0 and out:
            for line in out.splitlines():
                if "wlan0" in line and "src" in line:
                    parts = line.split()
                    try:
                        idx = parts.index("src")
                        return parts[idx + 1]
                    except (ValueError, IndexError):
                        pass

        # Fallback to ip addr show wlan0
        args2 = ["shell", "ip", "-f", "inet", "addr", "show", "wlan0"]
        if device_id:
            args2 = ["-s", device_id] + args2
        code, out2, _ = self._run_cmd(args2)
        if code == 0 and out2:
            match = re.search(r"inet\s+([0-9\.]+)/\d+", out2)
            if match:
                return match.group(1)

        return None

    def enable_wireless(self, device_id: Optional[str] = None, port: int = 5555) -> Tuple[bool, str]:
        """
        Switch connected USB device to TCP/IP mode and connect wirelessly.
        Returns (success, message).
        """
        ip = self.get_wifi_ip(device_id)
        if not ip:
            return False, "Could not detect device Wi-Fi IP. Ensure phone is connected to same Wi-Fi network."

        tcpip_args = ["tcpip", str(port)]
        if device_id:
            tcpip_args = ["-s", device_id] + tcpip_args
        code, out, err = self._run_cmd(tcpip_args)
        if code != 0:
            return False, f"Failed to restart ADB in TCP mode: {err or out}"

        time.sleep(1.5)
        connect_args = ["connect", f"{ip}:{port}"]
        code, out, err = self._run_cmd(connect_args, timeout=15)
        if "connected to" in out.lower():
            return True, f"Successfully connected wirelessly to {ip}:{port}! You can now unplug USB cable."
        return False, f"Connection attempt output: {out or err}"

    def release_camera_lock(self, device_id: Optional[str] = None):
        """
        Force-stop camera apps (MIUI Camera, Google Camera, etc.)
        that may hold an exclusive lock on the Camera2 physical sensor.
        """
        packages = [
            "com.android.camera",
            "com.google.android.GoogleCamera",
            "com.sec.android.app.camera"
        ]
        for pkg in packages:
            args = ["shell", "am", "force-stop", pkg]
            if device_id:
                args = ["-s", device_id] + args
            self._run_cmd(args)

    def turn_screen_off(self, device_id: Optional[str] = None):
        """Put device display to sleep using KEYCODE_SLEEP (223)."""
        args = ["shell", "input", "keyevent", "223"]
        if device_id:
            args = ["-s", device_id] + args
        self._run_cmd(args)

    def wake_screen(self, device_id: Optional[str] = None):
        """Wake device display using KEYCODE_WAKEUP (224)."""
        args = ["shell", "input", "keyevent", "224"]
        if device_id:
            args = ["-s", device_id] + args
        self._run_cmd(args)
