import customtkinter as ctk

class OmniTheme:
    """
    Refined, minimalist design system for OmniCapture.
    Eliminates decorative visual noise in favor of content clarity, clean whitespace, and typography.
    """
    # Neutral Surfaces
    BG_ROOT = "#121214"
    BG_CARD = "#18181B"
    BG_CARD_HOVER = "#232326"
    BG_CARD_BORDER = "#27272A"
    BG_INPUT = "#1F2024"

    # Restrained Primary Interactive Accent
    ACCENT_PRIMARY = "#2563EB"
    ACCENT_PRIMARY_HOVER = "#1D4ED8"

    # Functional Semantic Colors (Only used for true state feedback)
    STATUS_CONNECTED = "#10B981"
    STATUS_DISCONNECTED = "#71717A"
    STATUS_WARNING = "#F59E0B"
    STATUS_RECORDING = "#EF4444"
    STATUS_RECORDING_HOVER = "#DC2626"

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
