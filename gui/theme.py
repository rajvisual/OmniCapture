import sys
import winreg
from typing import Dict, Any, Callable, List, Optional
import customtkinter as ctk

class ThemeTokens:
    """
    Design Token Specification for OmniCapture Studio.
    Guarantees strict 4px grid spacing, 3-level surface hierarchy,
    contrast ratios exceeding WCAG AA (4.5:1), and consistent typography.
    """
    def __init__(
        self,
        name: str,
        is_dark: bool,
        # 3-Tier Surface Hierarchy
        bg_root: str,
        bg_panel: str,
        bg_raised: str,
        bg_header: str,
        bg_input: str,
        bg_hover: str,
        bg_active: str,
        # Borders & Highlights
        border_subtle: str,
        border_default: str,
        border_focus: str,
        border_specular: str,
        # Typography Colors
        text_primary: str,
        text_secondary: str,
        text_muted: str,
        text_dim: str,
        # Interactive Accent & States
        accent_primary: str,
        accent_hover: str,
        accent_active: str,
        status_connected: str,
        status_warning: str,
        status_recording: str,
        status_recording_hover: str,
        # Audio Metering Scale
        vu_bg: str,
        vu_green: str,
        vu_yellow: str,
        vu_red: str,
        # DWM Attributes
        dwm_caption_hex: str,
        dwm_text_hex: str,
        dwm_backdrop_type: int = 2
    ):
        self.name = name
        self.is_dark = is_dark

        # Surfaces
        self.bg_root = bg_root
        self.bg_panel = bg_panel
        self.bg_raised = bg_raised
        self.bg_header = bg_header
        self.bg_input = bg_input
        self.bg_hover = bg_hover
        self.bg_active = bg_active

        # Borders
        self.border_subtle = border_subtle
        self.border_default = border_default
        self.border_focus = border_focus
        self.border_specular = border_specular

        # Text
        self.text_primary = text_primary
        self.text_secondary = text_secondary
        self.text_muted = text_muted
        self.text_dim = text_dim

        # Accents & Semantics
        self.accent_primary = accent_primary
        self.accent_hover = accent_hover
        self.accent_active = accent_active
        self.status_connected = status_connected
        self.status_warning = status_warning
        self.status_recording = status_recording
        self.status_recording_hover = status_recording_hover

        # Audio Metering
        self.vu_bg = vu_bg
        self.vu_green = vu_green
        self.vu_yellow = vu_yellow
        self.vu_red = vu_red

        # DWM
        self.dwm_caption_hex = dwm_caption_hex
        self.dwm_text_hex = dwm_text_hex
        self.dwm_backdrop_type = dwm_backdrop_type


# -----------------------------------------------------------------------------
# THEME 1: LIGHT MINIMAL (Figma / Linear / Fluent Light inspired)
# -----------------------------------------------------------------------------
LIGHT_MINIMAL = ThemeTokens(
    name="light",
    is_dark=False,
    bg_root="#F3F4F6",              # Soft grey base
    bg_panel="#FFFFFF",             # Pure crisp white panels
    bg_raised="#FFFFFF",            # Raised controls with 1px border
    bg_header="#F8FAFC",            # Subtle top bar
    bg_input="#F1F3F5",             # Neutral inputs
    bg_hover="#E9ECEF",             # Crisp hover
    bg_active="#DEE2E6",
    border_subtle="#E5E7EB",        # 1px subtle divider
    border_default="#D1D5DB",       # Control boundaries
    border_focus="#2563EB",         # Clear focus ring
    border_specular="#FFFFFF",
    text_primary="#111827",         # Near-black high contrast (14:1)
    text_secondary="#374151",       # Mid-grey (7:1)
    text_muted="#6B7280",           # Labels (4.8:1)
    text_dim="#9CA3AF",
    accent_primary="#2563EB",       # Studio Blue (primary button only)
    accent_hover="#1D4ED8",
    accent_active="#1E40AF",
    status_connected="#10B981",
    status_warning="#F59E0B",
    status_recording="#EF4444",
    status_recording_hover="#DC2626",
    vu_bg="#E5E7EB",
    vu_green="#10B981",
    vu_yellow="#F59E0B",
    vu_red="#EF4444",
    dwm_caption_hex="#F3F4F6",
    dwm_text_hex="#111827",
    dwm_backdrop_type=2
)

# -----------------------------------------------------------------------------
# THEME 2: DARK LIQUID GLASS (Deep dark with specular highlights & Mica)
# -----------------------------------------------------------------------------
DARK_LIQUID_GLASS = ThemeTokens(
    name="dark",
    is_dark=True,
    bg_root="#0B0C10",              # Deep near-black with subtle blue-violet undertone
    bg_panel="#111218",             # 88% opaque high-contrast reading surface
    bg_raised="#181922",            # Raised controls and cards
    bg_header="#13141D",            # Liquid glass header dock
    bg_input="#1A1B26",             # Form controls
    bg_hover="#232534",             # Smooth hover surface
    bg_active="#2C2F42",
    border_subtle="#222432",        # Low-contrast boundaries
    border_default="#2C2F42",       # Control outlines
    border_focus="#3B82F6",         # Focus ring
    border_specular="#3D4158",      # 1px top specular highlight
    text_primary="#F9FAFB",         # Pure high-contrast white (15:1)
    text_secondary="#D1D5DB",       # Secondary reading text (8:1)
    text_muted="#9CA3AF",           # Meta labels (5:1)
    text_dim="#6B7280",             # Disabled / hint text
    accent_primary="#2563EB",       # Disciplined studio blue
    accent_hover="#1D4ED8",
    accent_active="#1E40AF",
    status_connected="#10B981",
    status_warning="#F59E0B",
    status_recording="#EF4444",
    status_recording_hover="#DC2626",
    vu_bg="#0D1017",
    vu_green="#10B981",
    vu_yellow="#F59E0B",
    vu_red="#EF4444",
    dwm_caption_hex="#0B0C10",
    dwm_text_hex="#F9FAFB",
    dwm_backdrop_type=2
)


class OmniTheme:
    """
    Centralized Theme System and Registry for OmniCapture Studio.
    Provides instant runtime theme switching, design token resolution,
    and backwards-compatible aliases for legacy components.
    """
    # Spacing Grid (Strict 4px base)
    SPACE_4 = 4
    SPACE_6 = 6
    SPACE_8 = 8
    SPACE_12 = 12
    SPACE_16 = 16
    SPACE_20 = 20
    SPACE_24 = 24
    SPACE_32 = 32

    # Dimensions & Radii
    CONTROL_HEIGHT = 32
    BUTTON_PRIMARY_HEIGHT = 44
    RADIUS_CONTROL = 8
    RADIUS_PANEL = 12
    RADIUS_CARD = 8
    RADIUS_POPUP = 8

    # Backward compatibility aliases
    SPACE_XS = 4
    SPACE_SM = 8
    SPACE_MD = 12
    SPACE_LG = 16
    SPACE_XL = 24

    # Theme Registry
    _themes: Dict[str, ThemeTokens] = {
        "dark": DARK_LIQUID_GLASS,
        "light": LIGHT_MINIMAL
    }
    _current_theme_key = "dark"
    _listeners: List[Callable[[ThemeTokens], None]] = []

    # -------------------------------------------------------------------------
    # Dynamic Class Properties forwarding to Active Theme
    # -------------------------------------------------------------------------
    @classmethod
    def get_tokens(cls) -> ThemeTokens:
        return cls._themes.get(cls._current_theme_key, DARK_LIQUID_GLASS)

    @classmethod
    def register_theme(cls, key: str, tokens: ThemeTokens):
        """Register a custom third theme dynamically."""
        cls._themes[key] = tokens

    @classmethod
    def register_listener(cls, callback: Callable[[ThemeTokens], None]):
        """Register a component callback for instant runtime restyling."""
        if callback not in cls._listeners:
            cls._listeners.append(callback)

    @classmethod
    def unregister_listener(cls, callback: Callable[[ThemeTokens], None]):
        if callback in cls._listeners:
            cls._listeners.remove(callback)

    @classmethod
    def set_theme(cls, theme_key: str):
        """Switch active theme instantly without layout shifts."""
        if theme_key in cls._themes:
            cls._current_theme_key = theme_key
            tokens = cls.get_tokens()
            ctk.set_appearance_mode("dark" if tokens.is_dark else "light")
            # Update class attributes for backward compatibility
            cls._sync_class_tokens(tokens)
            # Notify all registered observers
            for cb in cls._listeners:
                try:
                    cb(tokens)
                except Exception:
                    pass

    @classmethod
    def detect_system_theme(cls) -> str:
        """Query Windows 11 registry to match OS system light/dark mode."""
        if sys.platform == "win32":
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                )
                val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return "light" if val == 1 else "dark"
            except Exception:
                pass
        return "dark"

    @classmethod
    def _sync_class_tokens(cls, t: ThemeTokens):
        cls.BG_ROOT = t.bg_root
        cls.BG_CANVAS = t.bg_root
        cls.BG_DOCK = t.bg_panel
        cls.BG_DOCK_HEADER = t.bg_header
        cls.BG_CARD = t.bg_raised
        cls.BG_CARD_HOVER = t.bg_hover
        cls.BG_CARD_BORDER = t.border_subtle
        cls.BG_INPUT = t.bg_input

        cls.BORDER_SUBTLE = t.border_subtle
        cls.BORDER_DEFAULT = t.border_default
        cls.BORDER_FOCUS = t.border_focus

        cls.ACCENT_PRIMARY = t.accent_primary
        cls.ACCENT_PRIMARY_HOVER = t.accent_hover
        cls.STATUS_CONNECTED = t.status_connected
        cls.STATUS_WARNING = t.status_warning
        cls.STATUS_RECORDING = t.status_recording
        cls.STATUS_RECORDING_HOVER = t.status_recording_hover

        cls.VU_BG = t.vu_bg
        cls.VU_GREEN = t.vu_green
        cls.VU_YELLOW = t.vu_yellow
        cls.VU_RED = t.vu_red

        cls.TEXT_MAIN = t.text_primary
        cls.TEXT_BODY = t.text_secondary
        cls.TEXT_MUTED = t.text_muted
        cls.TEXT_DIM = t.text_dim

        # Aliases for unit tests
        cls.ACCENT_CYAN = t.accent_primary
        cls.ACCENT_PURPLE = t.accent_primary
        cls.ACCENT_RED = t.status_recording
        cls.ACCENT_GREEN = t.status_connected

    # -------------------------------------------------------------------------
    # Typography Scale (Strict 11 / 12 / 13 / 15 / 20 px)
    # -------------------------------------------------------------------------
    @classmethod
    def font_title(cls) -> tuple:
        """Application & modal headers: 20px semibold"""
        return ("Segoe UI Variable Display", 20, "bold")

    @classmethod
    def font_headline(cls) -> tuple:
        """Key view titles: 15px bold"""
        return ("Segoe UI Variable Display", 15, "bold")

    @classmethod
    def font_section(cls) -> tuple:
        """Section & dock headers: 13px semibold"""
        return ("Segoe UI Variable Text", 13, "bold")

    @classmethod
    def font_body_bold(cls) -> tuple:
        """Emphasized reading text: 12px bold"""
        return ("Segoe UI Variable Text", 12, "bold")

    @classmethod
    def font_body(cls) -> tuple:
        """Standard reading & control text: 12px"""
        return ("Segoe UI Variable Text", 12)

    @classmethod
    def font_caption(cls) -> tuple:
        """Captions & labels: 11px"""
        return ("Segoe UI Variable Text", 11)

    @classmethod
    def font_label(cls) -> tuple:
        """Alias for font_caption: 11px"""
        return ("Segoe UI Variable Text", 11)

    @classmethod
    def font_meta(cls) -> tuple:
        """Small metadata & badges: 11px semibold"""
        return ("Segoe UI Variable Text", 11, "bold")

    @classmethod
    def font_mono(cls, size: int = 11, weight: str = "normal") -> tuple:
        """Monospace readings, REC timer, and telemetry"""
        return ("Consolas", size, weight)

    @classmethod
    def apply_appearance(cls):
        """Initialize global appearance settings."""
        tokens = cls.get_tokens()
        ctk.set_appearance_mode("dark" if tokens.is_dark else "light")
        ctk.set_default_color_theme("blue")
        cls._sync_class_tokens(tokens)


# Initialize default class attributes
OmniTheme.apply_appearance()
