import sys
import time
import threading
from typing import Optional, Callable

def _is_focus_assist_quiet_hours() -> bool:
    """Check Windows Focus Assist / Do Not Disturb state via SHQueryUserNotificationState."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        state = ctypes.c_int()
        res = ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state))
        if res == 0:
            # QUNS_QUIET_TIME = 6, QUNS_PRESENTATION_MODE = 4, QUNS_RUNNING_D3D_FULL_SCREEN = 3
            return state.value in (3, 4, 6)
    except Exception:
        pass
    return False

class NotificationManager:
    """
    Unified Notification Subsystem for OmniCapture Studio.
    Delivers:
    - Native Windows Action Center toasts (dispatched ONLY when window is unfocused and DND is off)
    - In-app glass toast notifications with action buttons (via ToastNotificationManager)
    - Debouncing for recurring telemetry alerts (e.g. low disk space)
    - Action buttons on relevant notifications (e.g. Open in Explorer, Retry, Settings)
    """

    def __init__(
        self,
        in_app_toast_fn: Optional[Callable[..., None]] = None,
        tray_notify_fn: Optional[Callable[[str, str], None]] = None,
        is_window_focused_fn: Optional[Callable[[], bool]] = None
    ):
        self.in_app_toast_fn = in_app_toast_fn
        self.tray_notify_fn = tray_notify_fn
        self.is_window_focused_fn = is_window_focused_fn
        self._last_alert_times = {}

    def notify(
        self,
        title: str,
        message: str,
        level: str = "info", # "info" | "success" | "warning" | "error"
        action_text: Optional[str] = None,
        action_cmd: Optional[Callable[[], None]] = None,
        native: bool = True,
        in_app: bool = True
    ):
        """Dispatch notification to in-app overlay and/or native Windows Action Center."""
        # 1. In-app toast (always shown inside the app window)
        if in_app and self.in_app_toast_fn:
            try:
                duration = 0 if level == "error" else 3500
                self.in_app_toast_fn(
                    title=title,
                    message=message,
                    level=level,
                    duration_ms=duration,
                    action_text=action_text,
                    action_cmd=action_cmd
                )
            except Exception:
                pass

        # 2. Native Windows notification rules:
        # - ONLY dispatched when app window is not focused (or minimized)
        # - Respects Windows Focus Assist / Do Not Disturb
        is_focused = False
        if self.is_window_focused_fn:
            try:
                is_focused = self.is_window_focused_fn()
            except Exception:
                pass

        if native and not is_focused and self.tray_notify_fn and sys.platform == "win32":
            if not _is_focus_assist_quiet_hours():
                try:
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

    def notify_recording_saved(self, path_str: str, duration_str: str = "", on_open_cmd: Optional[Callable[[], None]] = None):
        """Trigger notification when a recording has safely finalised to disk."""
        from pathlib import Path
        name = Path(path_str).name
        msg = f"Capture finalised ({duration_str}): {name}" if duration_str else f"Saved: {name}"
        self.notify(
            "Recording Saved",
            msg,
            level="success",
            action_text="Show in Explorer" if on_open_cmd else None,
            action_cmd=on_open_cmd
        )

    def notify_upload_event(self, success: bool, filename: str, error_msg: str = "", retry_cmd: Optional[Callable[[], None]] = None):
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
                level="error",
                action_text="Retry" if retry_cmd else None,
                action_cmd=retry_cmd
            )

    def notify_low_disk(self, free_gb: float, threshold_gb: float = 5.0, settings_cmd: Optional[Callable[[], None]] = None):
        """Trigger low disk warning with 60-second debounce to avoid notification floods."""
        now = time.time()
        last = self._last_alert_times.get("low_disk", 0)
        if now - last < 60:
            return
        self._last_alert_times["low_disk"] = now

        self.notify(
            "Low Disk Space",
            f"Only {free_gb:.1f} GB remaining on recording drive! Free up space soon.",
            level="warning",
            action_text="Storage Settings" if settings_cmd else None,
            action_cmd=settings_cmd
        )
