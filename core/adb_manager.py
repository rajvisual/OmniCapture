import os
import re
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple

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

    def list_devices(self) -> List[Dict[str, str]]:
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

    def turn_screen_off(self, device_id: Optional[str] = None):
        """Put device display to sleep using KEYCODE_SLEEP (223)."""
        args = ["shell", "input", "keyevent", "223"]
        if device_id:
            args = ["-s", device_id] + args
        self._run_cmd(args)

