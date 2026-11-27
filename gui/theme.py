import customtkinter as ctk

class OmniTheme:
    """
    Refined, minimalist design system for OmniCapture.
    Eliminates decorative visual noise in favor of content clarity, clean whitespace, and typography.
    """
    # Neutral Surfaces & OBS Studio Docks
    BG_ROOT = "#101116"
    BG_CANVAS = "#0B0C10"        # Center stage broadcast canvas
    BG_DOCK = "#15161D"          # Dock panels (Scenes, Sources, Mixer, Controls)
    BG_DOCK_HEADER = "#1C1D26"   # Dock header bar
    BG_CARD = "#181920"
    BG_CARD_HOVER = "#22232D"
    BG_CARD_BORDER = "#272935"
    BG_INPUT = "#1E202A"

    # Restrained Primary Interactive Accent
    ACCENT_PRIMARY = "#2563EB"
    ACCENT_PRIMARY_HOVER = "#1D4ED8"

    # Functional Semantic Colors & Audio VU Meters
    STATUS_CONNECTED = "#10B981"
    STATUS_DISCONNECTED = "#71717A"
    STATUS_WARNING = "#F59E0B"
    STATUS_RECORDING = "#EF4444"
    STATUS_RECORDING_HOVER = "#DC2626"
    VU_GREEN = "#10B981"
    VU_YELLOW = "#F59E0B"
    VU_RED = "#EF4444"

    # Typography
    TEXT_MAIN = "#F4F4F5"
    TEXT_BODY = "#D4D4D8"
    TEXT_MUTED = "#A1A1AA"
    TEXT_DIM = "#71717A"

    # Standard Control Corner Radius (Clean, consistent 6-8px; no exaggerated pills)
    RADIUS_CONTROL = 6
    RADIUS_CARD = 8

    # Backward compatibility aliases for existing references
    ACCENT_CYAN = ACCENT_PRIMARY
    ACCENT_CYAN_HOVER = ACCENT_PRIMARY_HOVER
    ACCENT_GREEN = STATUS_CONNECTED
    ACCENT_GREEN_HOVER = "#059669"
    ACCENT_RED = STATUS_RECORDING
    ACCENT_RED_HOVER = STATUS_RECORDING_HOVER
    ACCENT_AMBER = STATUS_WARNING
    ACCENT_PURPLE = ACCENT_PRIMARY
    ACCENT_PURPLE_HOVER = ACCENT_PRIMARY_HOVER
    STATUS_OFFLINE = "#EF4444"

    @classmethod
    def apply_appearance(cls):
        """Configure global CustomTkinter appearance settings."""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
