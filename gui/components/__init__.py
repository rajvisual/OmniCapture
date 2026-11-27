"""
OmniCapture Desktop Studio Components.
Native Fluent & OBS Studio desktop architecture.
"""
from gui.components.audio_meter import AudioChannelStrip
from gui.components.toast import ToastNotificationManager
from gui.components.command_palette import CommandPalette
from gui.components.status_chip import StatusChip
from gui.components.empty_state import CanvasEmptyState
from gui.components.menu_dropdown import MenuDropdown
from gui.components.top_bar import UnifiedTopBar

__all__ = [
    "AudioChannelStrip",
    "ToastNotificationManager",
    "CommandPalette",
    "StatusChip",
    "CanvasEmptyState",
    "MenuDropdown",
    "UnifiedTopBar",
]
