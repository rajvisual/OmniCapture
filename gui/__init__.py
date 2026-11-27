"""
OmniCapture GUI Package
Modern Windows 11 Dark Mode Dashboard, System Tray, and Hotkeys
"""
from gui.theme import OmniTheme
from gui.controller import GUIController
from gui.tray import SystemTrayManager
from gui.hotkeys import GlobalHotkeyManager

__all__ = [
    "OmniTheme",
    "GUIController",
    "SystemTrayManager",
    "GlobalHotkeyManager",
]
