"""
OmniCapture Desktop Studio GUI Package.
Professional OBS Studio-inspired workspace, Windows 11 system integration,
and hardware-accelerated broadcast telemetry.
"""
from gui.theme import OmniTheme
from gui.controller import GUIController
from gui.tray import SystemTrayManager
from gui.hotkeys import GlobalHotkeyManager
from gui.dashboard import OmniCaptureApp
from gui.menu_bar import DesktopMenuBar
from gui.components.audio_meter import AudioChannelStrip
from gui.components.toast import ToastNotificationManager
from gui.components.command_palette import CommandPalette

__all__ = [
    "OmniTheme",
    "GUIController",
    "SystemTrayManager",
    "GlobalHotkeyManager",
    "OmniCaptureApp",
    "DesktopMenuBar",
    "AudioChannelStrip",
    "ToastNotificationManager",
    "CommandPalette",
]
