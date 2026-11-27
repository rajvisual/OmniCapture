import sys
import time
import threading
from typing import Optional, Callable

class NotificationManager:
    """
    Unified Notification Subsystem for OmniCapture Studio.
    Delivers:
    - Native Windows Action Center toasts (via tray icon NIM_MODIFY / Shell_NotifyIcon)
    - In-app glass toast notifications (via ToastNotificationManager)
    - Debouncing for recurring telemetry alerts (e.g. low disk space)
    """

    def __init__(self, in_app_toast_fn: Optional[Callable[[str, str, str], None]] = None, tray_notify_fn: Optional[Callable[[str, str], None]] = None):
        self.in_app_toast_fn = in_app_toast_fn
        self.tray_notify_fn = tray_notify_fn
        self._last_alert_times = {}

    def notify(
        self,
        title: str,
        message: str,
        level: str = "info", # "info" | "success" | "warning" | "error"
        native: bool = True,
        in_app: bool = True
    ):
        """Dispatch notification to both native Windows Action Center and in-app overlay."""
        # 1. In-app toast
        if in_app and self.in_app_toast_fn:
            try:
                self.in_app_toast_fn(title, message, level)
            except Exception:
                pass

        # 2. Native Windows notification (via tray icon)
        if native and self.tray_notify_fn and sys.platform == "win32":
            try:
                # Dispatch in background to avoid any blocking on Windows Shell
                threading.Thread(
                    target=self.tray_notify_fn,
                    args=(f"OmniCapture — {title}", message),
                    daemon=True,
                    name="NativeNotificationWorker"
                ).start()
            except Exception:
                pass

    def notify_device_event(self, connected: bool, device_name: str = "Android Device"):
        """Trigger notification for phone USB / Wi-Fi connection state change."""
        if connected:
            self.notify(
                "Device Connected",
                f"{device_name} is ready for low-latency capture",
                level="success"
            )
        else:
            self.notify(
                "Device Disconnected",
                "Mobile phone detached. Reconnect USB cable or verify Wi-Fi ADB.",
                level="warning"
            )

    def notify_recording_saved(self, path_str: str, duration_str: str = ""):
        """Trigger notification when a recording has safely finalised to disk."""
        msg = f"Capture finalised ({duration_str}): {path_str}" if duration_str else f"Saved: {path_str}"
        self.notify(
            "Recording Saved",
            msg,
            level="success"
        )

    def notify_upload_event(self, success: bool, filename: str, error_msg: str = ""):
        """Trigger notification when a cloud upload completes or fails."""
        if success:
            self.notify(
                "Google Drive Sync",
                f"Successfully uploaded {filename} to cloud storage",
                level="success"
            )
        else:
            self.notify(
                "Upload Failed",
                f"Could not upload {filename}: {error_msg or 'Network error'}",
                level="error"
            )

    def notify_low_disk(self, free_gb: float, threshold_gb: float = 5.0):
        """Trigger low disk warning with 60-second debounce to avoid notification floods."""
        now = time.time()
        last = self._last_alert_times.get("low_disk", 0)
        if now - last < 60:
            return
        self._last_alert_times["low_disk"] = now

        self.notify(
            "Low Disk Space",
            f"Only {free_gb:.1f} GB remaining on recording drive! Free up space soon.",
            level="warning"
        )
