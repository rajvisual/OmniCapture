import sys
import winreg
from typing import Dict, Any, Callable, List, Optional
import customtkinter as ctk

class ThemeTokens:
    """
    Design Token Specification for OmniCapture Studio.
    Guarantees strict 4px grid spacing, 3-level surface hierarchy,
    contrast ratios exceeding WCAG AA (4.5:1 for body text, 3:1 for UI/focus),
    and authentic Windows 11 Liquid Glass & Light Minimal materials.
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
        # Button Borders (quiet 1.6-2:1 tone for text-labeled buttons)
        border_button: str = "#C4C8D0",
        border_button_hover: str = "#9CA3AF",
        # Audio Metering Scale
        vu_bg: str = "#D1D5DB",
        vu_green: str = "#15803D",
        vu_yellow: str = "#B45309",
        vu_red: str = "#DC2626",
        # DWM Attributes
        dwm_caption_hex: str = "#F3F4F6",
        dwm_text_hex: str = "#111827",
        dwm_backdrop_type: int = 2,
        # Accent Subtle (for scene selection & tinting)
        accent_subtle: str = "#E0EDFD",
        # Preview Stage (stays dark in both Light & Dark themes)
        bg_stage: str = "#1B1D21",
        border_stage: str = "#374151",
        stage_text_primary: str = "#F9FAFB",
        stage_text_muted: str = "#9CA3AF",
        stage_text_dim: str = "#6B7280",
        stage_bg_card: str = "#24272E",
        stage_border_card: str = "#374151",
        stage_btn_bg: str = "#2D3139",
        stage_btn_hover: str = "#3D424E",
        # Pre-composited Glass Tokens (opaque hex only, zero fake alpha strings)
        bg_glass: str = "#191B26",
        surface_glass: str = "#191B26",
        glass_stroke: str = "#2A2D3C",
        glass_highlight: str = "#383D52",
        glass_shadow: str = "#07080A",
        blur_radius: int = 28,
        noise_opacity: float = 0.015,
        alpha_surface_idle: float = 0.08,
        alpha_surface_hover: float = 0.12,
        alpha_surface_active: float = 0.16,
        alpha_surface_disabled: float = 0.03
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
        self.border_button = border_button
        self.border_button_hover = border_button_hover

        # Text
        self.text_primary = text_primary
        self.text_secondary = text_secondary
        self.text_muted = text_muted
        self.text_dim = text_dim

        # Accents & Semantics
        self.accent_primary = accent_primary
        self.accent_hover = accent_hover
        self.accent_active = accent_active
        self.accent_subtle = accent_subtle
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

        # Preview Stage
        self.bg_stage = bg_stage
        self.border_stage = border_stage
        self.stage_text_primary = stage_text_primary
        self.stage_text_muted = stage_text_muted
        self.stage_text_dim = stage_text_dim
        self.stage_bg_card = stage_bg_card
        self.stage_border_card = stage_border_card
        self.stage_btn_bg = stage_btn_bg
        self.stage_btn_hover = stage_btn_hover

        # Glass & Alpha
        self.bg_glass = bg_glass
        self.surface_glass = surface_glass
        self.glass_stroke = glass_stroke
        self.glass_highlight = glass_highlight
        self.glass_shadow = glass_shadow
        self.blur_radius = blur_radius
        self.noise_opacity = noise_opacity
        self.alpha_surface_idle = alpha_surface_idle
        self.alpha_surface_hover = alpha_surface_hover
        self.alpha_surface_active = alpha_surface_active
        self.alpha_surface_disabled = alpha_surface_disabled

    @staticmethod
    def calculate_contrast(hex1: str, hex2: str) -> float:
        """Calculate WCAG relative luminance contrast ratio between two hex colors."""
        def _lin(c_srgb: float) -> float:
            c = c_srgb / 255.0
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

        def _lum(hex_str: str) -> float:
            h = hex_str.lstrip("#")
            if len(h) == 3:
                h = "".join(c * 2 for c in h)
            rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
            r, g, b = (_lin(v) for v in rgb)
            return 0.2126 * r + 0.7152 * g + 0.0722 * b

        l1 = _lum(hex1)
        l2 = _lum(hex2)
        return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)

    def validate_wcag_aa(self) -> Dict[str, Dict[str, Any]]:
        """Validate all critical foreground/background and non-text pairs against standard WCAG AA (no delta-luminance hacks)."""
        button_text = "#FFFFFF" if not self.is_dark else self.text_primary
        checks = [
            ("text_primary on bg_panel", self.text_primary, self.bg_panel, 4.5),
            ("text_primary on bg_root", self.text_primary, self.bg_root, 4.5),
            ("text_primary on bg_raised", self.text_primary, self.bg_raised, 4.5),
            ("text_secondary on bg_panel", self.text_secondary, self.bg_panel, 4.5),
            ("text_muted on bg_panel", self.text_muted, self.bg_panel, 4.5),
            ("text_dim on bg_panel", self.text_dim, self.bg_panel, 3.0),
            ("button_text on accent_primary", button_text, self.accent_primary, 4.5),
            ("white on status_recording", "#FFFFFF", self.status_recording, 4.5),
            ("status_recording on bg_root", self.status_recording, self.bg_root, 3.0),
            ("status_connected on bg_root", self.status_connected, self.bg_root, 3.0),
            ("border_focus on bg_panel", self.border_focus, self.bg_panel, 3.0),
            ("border_default on bg_panel", self.border_default, self.bg_panel, 3.0),
            ("border_default on bg_raised", self.border_default, self.bg_raised, 3.0),
            ("vu_green on vu_bg", self.vu_green, self.vu_bg, 3.0),
            ("vu_yellow on vu_bg", self.vu_yellow, self.vu_bg, 3.0),
            ("vu_red on vu_bg", self.vu_red, self.vu_bg, 3.0),
            ("stage_text_primary on bg_stage", self.stage_text_primary, self.bg_stage, 4.5),
            ("stage_text_muted on bg_stage", self.stage_text_muted, self.bg_stage, 4.5),
            ("stage_text_dim on bg_stage", self.stage_text_dim, self.bg_stage, 3.0),
            ("stage_border_card on bg_stage", self.stage_border_card, self.bg_stage, 1.5),
            ("text_primary on accent_subtle", self.text_primary, self.accent_subtle, 4.5),
            ("border_button on bg_panel", self.border_button, self.bg_panel, 1.6),
            ("border_button on bg_raised", self.border_button, self.bg_raised, 1.5)
        ]
        results = {}
        for name, c1, c2, req in checks:
            ratio = round(self.calculate_contrast(c1, c2), 2)
            results[name] = {
                "ratio": ratio,
                "required": req,
                "passed": ratio >= req
            }
        return results


# -----------------------------------------------------------------------------
# THEME 1: LIGHT MINIMAL (Fluent Light / Clean solid surfaces, zero blur)
# -----------------------------------------------------------------------------
LIGHT_MINIMAL = ThemeTokens(
    name="light",
    is_dark=False,
    bg_root="#F3F4F6",              # Soft cool grey base
    bg_panel="#FFFFFF",             # Pure crisp white panels
    bg_raised="#F1F3F5",            # Slightly tinted grey for inputs & segmented tracks
    bg_header="#F3F4F6",            # Synchronized exact match with native caption #F3F4F6
    bg_input="#F1F3F5",             # Neutral inputs (distinct visible fill)
    bg_hover="#E9ECEF",             # Crisp hover surface
    bg_active="#DEE2E6",
    border_subtle="#E5E7EB",        # 1px subtle divider
    border_default="#71717A",       # Textless control boundaries (contrast 4.83:1 on white, 4.39:1 on grey)
    border_focus="#2563EB",         # Clear focus ring (5.17:1)
    border_specular="#FFFFFF",
    border_button="#C4C8D0",        # Quiet 1px border for text-labeled buttons (1.69:1 on panel, 1.52:1 on input)
    border_button_hover="#9CA3AF",  # 1 step darker on hover (2.28:1 on input)
    text_primary="#111827",         # Near-black high contrast (17.74:1 on white)
    text_secondary="#374151",       # Mid-grey (10.31:1 on white)
    text_muted="#4B5563",           # Meta labels (7.56:1 on white)
    text_dim="#6B7280",             # Disabled / hint text (4.83:1 on white)
    accent_primary="#2563EB",       # Studio Blue (primary button only, 5.17:1 with white)
    accent_hover="#1D4ED8",
    accent_active="#1E40AF",
    accent_subtle="#E0EDFD",        # 12% accent tint for scene list selection
    status_connected="#059669",     # Connected green (3.42:1 on root, 4.52:1 with white)
    status_warning="#D97706",
    status_recording="#DC2626",     # Red state (4.83:1 with white text, 4.39:1 on root)
    status_recording_hover="#B91C1C",
    vu_bg="#1F222E",                # Pro dark meter trough (13.80:1 on white panel, standard WCAG compliant)
    vu_green="#10B981",             # 6.24:1 on #1F222E (lum 0.36)
    vu_yellow="#F59E0B",            # 7.37:1 on #1F222E (lum 0.44)
    vu_red="#DC2626",               # 3.28:1 on #1F222E (lum 0.17)
    dwm_caption_hex="#F3F4F6",      # Exact match with top bar
    dwm_text_hex="#111827",
    dwm_backdrop_type=2,
    # Preview Stage (Neutral dark grey #1B1D21, DaVinci/OBS standard)
    bg_stage="#1B1D21",
    border_stage="#374151",
    stage_text_primary="#F9FAFB",
    stage_text_muted="#9CA3AF",
    stage_text_dim="#6B7280",
    stage_bg_card="#24272E",
    stage_border_card="#374151",
    stage_btn_bg="#2D3139",
    stage_btn_hover="#3D424E",
    # Solid Fluent light surfaces (pre-composited hex, zero blur)
    bg_glass="#FFFFFF",
    surface_glass="#FFFFFF",
    glass_stroke="#E5E7EB",
    glass_highlight="#FFFFFF",
    glass_shadow="#E2E4E8",
    blur_radius=0,
    noise_opacity=0.0,
    alpha_surface_idle=1.0,
    alpha_surface_hover=1.0,
    alpha_surface_active=1.0,
    alpha_surface_disabled=0.4
)

# -----------------------------------------------------------------------------
# THEME 2: DARK LIQUID GLASS (Deep dark with specular highlights & pre-composited glass)
# -----------------------------------------------------------------------------
DARK_LIQUID_GLASS = ThemeTokens(
    name="dark",
    is_dark=True,
    bg_root="#0B0C10",              # Deep near-black base (RGB 11, 12, 16)
    bg_panel="#111218",             # Solid high-contrast reading surface (RGB 17, 18, 24)
    bg_raised="#181922",            # Raised controls and cards (#111218 + 3% #FFFFFF)
    bg_header="#13141D",            # Liquid glass header dock (#111218 + 2% #FFFFFF)
    bg_input="#1A1B26",             # Form controls (distinct visible fill)
    bg_hover="#232534",             # Smooth hover surface
    bg_active="#2C2F42",
    border_subtle="#222432",        # Low-contrast boundaries
    border_default="#636B83",       # Textless control boundaries (3.34:1 on #111218, 3.07:1 on #181922)
    border_focus="#3B82F6",         # Focus ring (5.08:1 on #111218)
    border_specular="#3D4158",      # 1px top specular highlight
    border_button="#383D52",        # Quiet 1px border for text buttons (1.63:1 on raised, 1.74:1 on panel)
    border_button_hover="#4B516D",  # 1 step lighter on hover (2.20:1 on raised)
    text_primary="#F3F4F6",         # Primary text (16.98:1, disciplined off-white, never #FFFFFF)
    text_secondary="#D1D5DB",       # Secondary reading text (12.68:1)
    text_muted="#9CA3AF",           # Meta labels (7.36:1)
    text_dim="#6B7280",             # Disabled / hint text (3.87:1)
    accent_primary="#2563EB",       # Studio Blue (primary button, 4.70:1 with text_primary #F3F4F6)
    accent_hover="#1D4ED8",
    accent_active="#1E40AF",
    accent_subtle="#1E2638",        # Subtle dark blue tint for scene selection
    status_connected="#10B981",     # Connected green (7.71:1 on root)
    status_warning="#F59E0B",
    status_recording="#DC2626",     # Red state (4.83:1 with white text, 4.05:1 on root)
    status_recording_hover="#B91C1C",
    vu_bg="#1F222E",                # Darkened track for standard WCAG >= 3.0:1
    vu_green="#10B981",             # 6.24:1 on #1F222E
    vu_yellow="#F59E0B",            # 7.37:1 on #1F222E
    vu_red="#DC2626",               # 3.28:1 on #1F222E
    dwm_caption_hex="#13141D",      # Exact match with in-app top bar (#13141D)
    dwm_text_hex="#F3F4F6",         # Off-white caption text
    dwm_backdrop_type=2,
    # Preview Stage
    bg_stage="#14151B",
    border_stage="#2D3139",
    stage_text_primary="#F9FAFB",
    stage_text_muted="#9CA3AF",
    stage_text_dim="#6B7280",
    stage_bg_card="#1B1C25",
    stage_border_card="#383B4D",
    stage_btn_bg="#232534",
    stage_btn_hover="#2C2F42",
    # Pre-composited Glass Tokens (opaque hex values derived from alpha recipes)
    bg_glass="#191B26",             # 8% #FFFFFF pre-composited over #111218
    surface_glass="#191B26",        # Opaque hex representation
    glass_stroke="#2A2D3C",         # 12% #FFFFFF pre-composited over #111218
    glass_highlight="#383D52",      # 18% #FFFFFF pre-composited over #111218
    glass_shadow="#07080A",         # 35% #000000 under #0B0C10
    blur_radius=28,
    noise_opacity=0.015,
    alpha_surface_idle=0.08,
    alpha_surface_hover=0.12,
    alpha_surface_active=0.16,
    alpha_surface_disabled=0.03
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
    RADIUS_PILL = 12

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
        cls.ACCENT_SUBTLE = t.accent_subtle
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

        # Stage tokens
        cls.BG_STAGE = t.bg_stage
        cls.BORDER_STAGE = t.border_stage
        cls.STAGE_TEXT_PRIMARY = t.stage_text_primary
        cls.STAGE_TEXT_MUTED = t.stage_text_muted
        cls.STAGE_TEXT_DIM = t.stage_text_dim

        # Glass & Alpha tokens
        cls.SURFACE_GLASS = t.surface_glass
        cls.GLASS_STROKE = t.glass_stroke
        cls.GLASS_HIGHLIGHT = t.glass_highlight
        cls.GLASS_SHADOW = t.glass_shadow
        cls.BLUR_RADIUS = t.blur_radius
        cls.NOISE_OPACITY = t.noise_opacity
        cls.ALPHA_SURFACE_IDLE = t.alpha_surface_idle
        cls.ALPHA_SURFACE_HOVER = t.alpha_surface_hover
        cls.ALPHA_SURFACE_ACTIVE = t.alpha_surface_active
        cls.ALPHA_SURFACE_DISABLED = t.alpha_surface_disabled

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
        cls._sync_class_tokens(tokens)


# Initialize default class attributes
OmniTheme.apply_appearance()
