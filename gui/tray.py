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
    """

    def __init__(
        self,
        on_show: Callable[[], None],
        on_exit: Callable[[], None],
        on_dual_record: Optional[Callable[[], None]] = None,
        on_mirror: Optional[Callable[[], None]] = None,
        on_camera: Optional[Callable[[], None]] = None,
        on_open_recordings: Optional[Callable[[], None]] = None
    ):
        self.on_show = on_show
        self.on_exit = on_exit
        self.on_dual_record = on_dual_record
        self.on_mirror = on_mirror
        self.on_camera = on_camera
        self.on_open_recordings = on_open_recordings

        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def _load_icon_image(self) -> Image.Image:
        """Load brand icon from assets, or generate a crisp vector-like fallback."""
        icon_path = resolve_resource("assets/logo/omnicapture-icon.png")
        if not icon_path.is_file():
            icon_path = resolve_resource("assets/logo/omnicapture.ico")

        if icon_path.is_file():
            try:
                img = Image.open(str(icon_path))
                return img.convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
            except Exception:
                pass

        # Fallback dynamic icon (Neon cyan & purple badge)
        img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([2, 2, 62, 62], radius=14, fill="#0F111A", outline="#00D2FF", width=3)
        draw.ellipse([22, 22, 42, 42], fill="#FF3366")
        return img

    def _build_menu(self) -> pystray.Menu:
        items = [
            pystray.MenuItem("Open OmniCapture Dashboard", lambda icon, item: self.on_show(), default=True),
            pystray.Menu.SEPARATOR,
        ]

        if self.on_dual_record:
            items.append(pystray.MenuItem("🎬 Quick Dual Recording (Ctrl+Alt+D)", lambda icon, item: self.on_dual_record()))
        if self.on_mirror:
            items.append(pystray.MenuItem("📱 Quick Display Mirror (Ctrl+Alt+M)", lambda icon, item: self.on_mirror()))
        if self.on_camera:
            items.append(pystray.MenuItem("📷 Quick Stealth Camera (Ctrl+Alt+C)", lambda icon, item: self.on_camera()))
        if self.on_open_recordings:
            items.append(pystray.MenuItem("📁 Open Recordings Folder (Ctrl+Alt+R)", lambda icon, item: self.on_open_recordings()))

        items.extend([
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit OmniCapture", lambda icon, item: self.on_exit())
        ])

        return pystray.Menu(*items)

    def start(self):
        """Start the system tray icon in a dedicated daemon thread."""
        if self._icon is not None:
            return

        image = self._load_icon_image()
        menu = self._build_menu()

        self._icon = pystray.Icon(
            name="OmniCapture",
            icon=image,
            title="OmniCapture — High-Performance Android & PC Capture",
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
