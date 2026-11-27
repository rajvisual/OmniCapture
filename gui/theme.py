import customtkinter as ctk

class OmniTheme:
    """
    Windows 11 Fluent Dark Palette & Typography for OmniCapture.
    """
    # Backgrounds
    BG_ROOT = "#0D0F17"          # Deep obsidian black
    BG_CARD = "#171A24"          # Card background
    BG_CARD_HOVER = "#1E2230"    # Hover surface
    BG_CARD_BORDER = "#282C3D"   # Subtle divider border
    BG_INPUT = "#1F2332"         # Input & dropdown background

    # Accent Colors
    ACCENT_CYAN = "#00D2FF"      # Electric cyan (Primary)
    ACCENT_CYAN_HOVER = "#00B4DB"# Cyan hover
    ACCENT_GREEN = "#00E676"     # Emerald neon (Connected / Success)
    ACCENT_GREEN_HOVER = "#00C853"
    ACCENT_RED = "#FF3366"       # Crimson red (Recording / Stop / Error)
    ACCENT_RED_HOVER = "#E02856"
    ACCENT_AMBER = "#FFB300"     # Amber gold (Warning / Battery)
    ACCENT_PURPLE = "#7C4DFF"    # Deep violet (Special / Dual Hero)
    ACCENT_PURPLE_HOVER = "#651FFF"

    # Typography / Text Colors
    TEXT_MAIN = "#FFFFFF"        # Primary headers & bold text
    TEXT_BODY = "#E2E8F0"        # Standard body text
    TEXT_MUTED = "#94A3B8"       # Secondary captions & hints
    TEXT_DIM = "#64748B"         # Dimmed indicators

    # Status Colors
    STATUS_CONNECTED = "#00E676"
    STATUS_DISCONNECTED = "#FFB300"
    STATUS_RECORDING = "#FF3366"
    STATUS_OFFLINE = "#EF4444"

    @classmethod
    def apply_appearance(cls):
        """Configure global CustomTkinter appearance settings."""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
