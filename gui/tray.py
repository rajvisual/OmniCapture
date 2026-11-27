import sys
import threading
from pathlib import Path
from typing import Optional, Callable
from PIL import Image, ImageDraw

import pystray
from core.resource_path import resolve_resource

class SystemTrayManager:
    """
    Manages OmniCapture's Windows system tray icon, background notifications, and tray menu.
    Supports idle and recording icon variants, dynamic state tooltips, and Windows toasts.
    """

    def __init__(
        self,
        on_show: Callable[[], None],
        on_exit: Callable[[], None],
        on_dual_record: Optional[Callable[[], None]] = None,
        on_mirror: Optional[Callable[[], None]] = None,
        on_camera: Optional[Callable[[], None]] = None,
        on_open_recordings: Optional[Callable[[], None]] = None,
        on_open_gallery: Optional[Callable[[], None]] = None
    ):
        self.on_show = on_show
        self.on_exit = on_exit
        self.on_dual_record = on_dual_record
        self.on_mirror = on_mirror
        self.on_camera = on_camera
        self.on_open_recordings = on_open_recordings
        self.on_open_gallery = on_open_gallery

        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None
        self._is_recording = False
        self._idle_image = None
        self._rec_image = None

    def _load_icon_image(self, recording: bool = False) -> Image.Image:
        """Load brand icon from assets, or generate a crisp vector-like fallback."""
        icon_path = resolve_resource("assets/logo/omnicapture-icon.png")
        if not icon_path.is_file():
            icon_path = resolve_resource("assets/logo/omnicapture.ico")

        if icon_path.is_file():
            try:
                base_img = Image.open(str(icon_path)).convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
                if recording:
                    # Draw bright red recording dot on bottom-right
                    draw = ImageDraw.Draw(base_img)
                    draw.ellipse([40, 40, 60, 60], fill="#DC2626", outline="#FFFFFF", width=2)
                return base_img
            except Exception:
                pass

        # Fallback dynamic icon
        img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        fill_col = "#DC2626" if recording else "#2563EB"
        draw.rounded_rectangle([2, 2, 62, 62], radius=14, fill="#111218", outline=fill_col, width=3)
        draw.ellipse([22, 22, 42, 42], fill=fill_col)
        return img

    def _build_menu(self) -> pystray.Menu:
        record_label = "⏹ Stop Active Recording" if self._is_recording else "🎬 Start Recording (Ctrl+Alt+D)"

        items = [
            pystray.MenuItem("Show Studio Console", lambda icon, item: self.on_show(), default=True),
            pystray.Menu.SEPARATOR,
        ]

        if self.on_dual_record:
            items.append(pystray.MenuItem(record_label, lambda icon, item: self.on_dual_record()))
        if self.on_mirror:
            items.append(pystray.MenuItem("📱 Launch Screen Mirror (Ctrl+Alt+M)", lambda icon, item: self.on_mirror()))
        if self.on_camera:
            items.append(pystray.MenuItem("📷 Camera Sensor Viewfinder (Ctrl+Alt+C)", lambda icon, item: self.on_camera()))
        if self.on_open_gallery:
            items.append(pystray.MenuItem("🎞 Media Library Gallery", lambda icon, item: self.on_open_gallery()))
        if self.on_open_recordings:
            items.append(pystray.MenuItem("📁 Open Recordings Folder (Ctrl+Alt+R)", lambda icon, item: self.on_open_recordings()))

        items.extend([
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit Studio", lambda icon, item: self.on_exit())
        ])

        return pystray.Menu(*items)

    def set_recording_state(self, is_recording: bool, elapsed_str: str = "00:00:00"):
        """Update tray icon image and tooltip when recording status changes."""
        self._is_recording = is_recording
        if not self._icon:
            return

        try:
            if is_recording:
                if not self._rec_image:
                    self._rec_image = self._load_icon_image(recording=True)
                self._icon.icon = self._rec_image
                self._icon.title = f"OmniCapture Studio — REC [{elapsed_str}]"
            else:
                if not self._idle_image:
                    self._idle_image = self._load_icon_image(recording=False)
                self._icon.icon = self._idle_image
                self._icon.title = "OmniCapture Studio — Studio Ready"

            # Re-generate menu with updated Start/Stop label
            self._icon.menu = self._build_menu()
        except Exception:
            pass

    def start(self):
        """Start the system tray icon in a dedicated daemon thread."""
        if self._icon is not None:
            return

        self._idle_image = self._load_icon_image(recording=False)
        self._rec_image = self._load_icon_image(recording=True)
        menu = self._build_menu()

        self._icon = pystray.Icon(
            name="OmniCapture",
            icon=self._idle_image,
            title="OmniCapture Studio — Studio Ready",
            menu=menu
        )

        def _run():
            try:
                self._icon.run()
            except Exception:
                pass

        self._thread = threading.Thread(target=_run, daemon=True, name="OmniTrayWorker")
        self._thread.start()

    def notify(self, title: str, message: str):
        """Display a Windows native notification balloon from the system tray."""
        if self._icon:
            try:
                self._icon.notify(message, title)
            except Exception:
                pass

    def stop(self):
        """Stop and remove system tray icon."""
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None
