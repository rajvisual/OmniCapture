from typing import Dict, Any, Callable, Optional, List
import customtkinter as ctk
from PIL import Image

from gui.theme import OmniTheme, ThemeTokens
from gui.components.menu_dropdown import MenuDropdown
from core.resource_path import resolve_resource

class UnifiedTopBar(ctk.CTkFrame):
    """
    Unified Fluent Window Top Bar.
    Replaces the white native Win32 menu bar with an integrated top bar:
    - App icon, title, and version
    - In-app styled menu items (File, Capture, Tools, View, Settings, Help)
    - Full Alt-key mnemonic support (Alt+F, Alt+C, Alt+T, Alt+V, Alt+S, Alt+H)
    - Centered command / status search pill
    - Quick actions: Theme toggle (☀ / 🌙), Refresh (F5), Release Lock
    """

    def __init__(
        self,
        parent,
        menu_handlers: Dict[str, Callable],
        on_open_palette: Callable,
        on_refresh: Callable,
        on_release_lock: Callable,
        on_toggle_theme: Callable,
        **kwargs
    ):
        tokens = OmniTheme.get_tokens()
        super().__init__(
            parent,
            fg_color=tokens.bg_header,
            border_width=1,
            border_color=tokens.border_subtle,
            corner_radius=0,
            height=46,
            **kwargs
        )
        self.pack_propagate(False)

        self.menu_handlers = menu_handlers
        self.on_open_palette = on_open_palette
        self.on_refresh = on_refresh
        self.on_release_lock = on_release_lock
        self.on_toggle_theme = on_toggle_theme
        self.menu_button_map: Dict[str, ctk.CTkButton] = {}
        self.active_dropdown: Optional[MenuDropdown] = None

        self._build_ui(tokens)

    def _build_ui(self, tokens: ThemeTokens):
        # ---------------------------------------------------------------------
        # LEFT: App Brand + In-App Menus
        # ---------------------------------------------------------------------
        self.left_box = ctk.CTkFrame(self, fg_color="transparent")
        self.left_box.pack(side="left", padx=12, pady=6)

        # App Icon
        logo_path = resolve_resource("assets/logo/omnicapture-icon.png")
        if logo_path.is_file():
            try:
                pil_img = Image.open(str(logo_path)).resize((20, 20), Image.Resampling.LANCZOS)
                self.logo_ctk = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(20, 20))
                ctk.CTkLabel(self.left_box, image=self.logo_ctk, text="").pack(side="left", padx=(0, 8))
            except Exception:
                pass

        # App Title
        self.title_lbl = ctk.CTkLabel(
            self.left_box,
            text="OmniCapture",
            font=OmniTheme.font_body_bold(),
            text_color=tokens.text_primary
        )
        self.title_lbl.pack(side="left", padx=(0, 4))

        # Version Pill
        self.ver_lbl = ctk.CTkLabel(
            self.left_box,
            text="v1.4.0-dev",
            font=OmniTheme.font_caption(),
            text_color=tokens.text_dim
        )
        self.ver_lbl.pack(side="left", padx=(0, 8))

        # Simulated Device Mode Indicator Badge (Dev-only, hidden in real hardware mode)
        self.sim_badge = ctk.CTkLabel(
            self.left_box,
            text="SIMULATED DEVICE",
            font=OmniTheme.font_mono(9),
            fg_color=tokens.status_warning,
            text_color="#FFFFFF",
            corner_radius=4,
            padx=6,
            pady=1
        )
        # Not packed by default; shown via set_simulated_mode(True)

        # In-App Menu Items
        self._build_menu_buttons(self.left_box, tokens)

        # ---------------------------------------------------------------------
        # CENTER: Command & Device Status Pill
        # ---------------------------------------------------------------------
        self.center_box = ctk.CTkFrame(self, fg_color="transparent")
        self.center_box.pack(side="left", expand=True)

        self.center_pill = ctk.CTkButton(
            self.center_box,
            text="🔍  Search commands, scenes, devices (Ctrl+P)",
            width=280,
            height=28,
            font=OmniTheme.font_caption(),
            fg_color=tokens.bg_input,
            hover_color=tokens.bg_hover,
            text_color=tokens.text_muted,
            border_width=1,
            border_color=tokens.border_subtle,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self.on_open_palette
        )
        self.center_pill.pack()

        # ---------------------------------------------------------------------
        # RIGHT: Quick Action Buttons & Theme Switcher
        # ---------------------------------------------------------------------
        self.right_box = ctk.CTkFrame(self, fg_color="transparent")
        self.right_box.pack(side="right", padx=12, pady=6)

        # 1. Theme Switcher (☀ / 🌙)
        theme_icon = "☀ Light" if tokens.is_dark else "🌙 Dark"
        self.btn_theme = ctk.CTkButton(
            self.right_box,
            text=theme_icon,
            width=68,
            height=28,
            font=OmniTheme.font_caption(),
            fg_color=tokens.bg_input,
            hover_color=tokens.bg_hover,
            text_color=tokens.text_secondary,
            border_width=1,
            border_color=tokens.border_subtle,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self.on_toggle_theme
        )
        self.btn_theme.pack(side="left", padx=3)

        # 2. Refresh Devices (F5)
        self.btn_refresh = ctk.CTkButton(
            self.right_box,
            text="Refresh",
            width=65,
            height=28,
            font=OmniTheme.font_caption(),
            fg_color=tokens.bg_input,
            hover_color=tokens.bg_hover,
            text_color=tokens.text_secondary,
            border_width=1,
            border_color=tokens.border_subtle,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self.on_refresh
        )
        self.btn_refresh.pack(side="left", padx=3)

        # 3. Release Camera Lock
        self.btn_lock = ctk.CTkButton(
            self.right_box,
            text="Release Lock",
            width=88,
            height=28,
            font=OmniTheme.font_caption(),
            fg_color=tokens.bg_input,
            hover_color=tokens.bg_hover,
            text_color=tokens.text_muted,
            border_width=1,
            border_color=tokens.border_subtle,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self.on_release_lock
        )
        self.btn_lock.pack(side="left", padx=3)

    def _build_menu_buttons(self, parent, tokens: ThemeTokens):
        self.menu_buttons = []
        self.menu_button_map.clear()
        menus = [
            ("File", self._get_file_menu_items()),
            ("Capture", self._get_capture_menu_items()),
            ("Tools", self._get_tools_menu_items()),
            ("View", self._get_view_menu_items()),
            ("Settings", self._get_settings_menu_items()),
            ("Help", self._get_help_menu_items()),
        ]

        for label, items in menus:
            btn = ctk.CTkButton(
                parent,
                text=label,
                width=42,
                height=26,
                font=OmniTheme.font_caption(),
                fg_color="transparent",
                hover_color=tokens.bg_hover,
                text_color=tokens.text_secondary,
                corner_radius=4
            )
            btn.configure(command=lambda b=btn, it=items: self._open_dropdown(b, it))
            btn.pack(side="left", padx=1)
            self.menu_buttons.append(btn)
            self.menu_button_map[label] = btn

    def open_menu_by_name(self, name: str):
        """Programmatically open a menu dropdown by its name or initial mnemonic."""
        target = name.lower()
        menus = {
            "file": self._get_file_menu_items,
            "capture": self._get_capture_menu_items,
            "tools": self._get_tools_menu_items,
            "view": self._get_view_menu_items,
            "settings": self._get_settings_menu_items,
            "help": self._get_help_menu_items,
        }
        for label, btn in self.menu_button_map.items():
            if label.lower() == target or label.lower().startswith(target):
                getter = menus.get(label.lower())
                if getter:
                    self._open_dropdown(btn, getter())
                break

    def set_device_status(self, text: str):
        """Update center command & device status readout."""
        try:
            self.center_pill.configure(text=text)
        except Exception:
            pass

    def _open_dropdown(self, button: ctk.CTkButton, items: List[Dict[str, Any]]):
        if self.active_dropdown:
            try:
                self.active_dropdown.close()
            except Exception:
                pass
            self.active_dropdown = None

        x = button.winfo_rootx()
        y = button.winfo_rooty() + button.winfo_height() + 2
        self.active_dropdown = MenuDropdown(self.winfo_toplevel(), items, x, y)

    def _get_file_menu_items(self) -> list:
        h = self.menu_handlers
        return [
            {"label": "Open Recordings Folder", "accelerator": "Ctrl+Alt+R", "command": h.get("open_recordings_folder")},
            {"label": "Media Library Gallery...", "command": h.get("open_recordings_gallery")},
            {"separator": True},
            {"label": "Preferences...", "accelerator": "Ctrl+,", "command": h.get("open_settings")},
            {"separator": True},
            {"label": "Minimize to Tray", "accelerator": "Ctrl+W", "command": h.get("minimize_to_tray")},
            {"label": "Exit Studio", "accelerator": "Ctrl+Q", "command": h.get("exit_app")},
        ]

    def _get_capture_menu_items(self) -> list:
        h = self.menu_handlers
        return [
            {"label": "Start Dual Recording", "accelerator": "Ctrl+Alt+D", "command": h.get("start_dual_record")},
            {"label": "Launch Screen Mirror", "accelerator": "Ctrl+Alt+M", "command": h.get("launch_mirror")},
            {"label": "Camera Sensor Viewfinder", "accelerator": "Ctrl+Alt+C", "command": h.get("launch_camera")},
            {"label": "Mobile Screen Record", "command": h.get("start_screen_record")},
            {"separator": True},
            {"label": "Stop Active Capture", "accelerator": "Esc", "command": h.get("stop_active_recording")},
        ]

    def _get_tools_menu_items(self) -> list:
        h = self.menu_handlers
        return [
            {"label": "Command Palette...", "accelerator": "Ctrl+P", "command": h.get("open_command_palette")},
            {"separator": True},
            {"label": "Release Camera Lock", "accelerator": "Ctrl+Shift+L", "command": h.get("release_camera_lock")},
            {"label": "Switch to Wi-Fi ADB", "command": h.get("switch_wireless_adb")},
            {"label": "Refresh Devices", "accelerator": "F5", "command": h.get("refresh_devices")},
            {"separator": True},
            {"label": "Hardware Diagnostics...", "command": h.get("open_diagnostics")},
            {"separator": True},
            {"label": "Developer: Simulated Device...", "command": h.get("open_simulated_device")},
            {"label": "Developer: Component Gallery...", "command": h.get("open_gallery")},
        ]

    def _get_view_menu_items(self) -> list:
        h = self.menu_handlers
        return [
            {"label": "Dual Stream (PC + Phone)", "accelerator": "1", "command": lambda: h.get("switch_scene")("dual")},
            {"label": "Screen Mirror", "accelerator": "2", "command": lambda: h.get("switch_scene")("mirror")},
            {"label": "Camera Feed", "accelerator": "3", "command": lambda: h.get("switch_scene")("camera")},
            {"label": "Screen Record", "accelerator": "4", "command": lambda: h.get("switch_scene")("screen")},
            {"separator": True},
            {"label": "Switch Theme (Light / Dark)", "command": self.on_toggle_theme},
            {"label": "Reset Window Size", "command": h.get("reset_window_size")},
        ]

    def _get_settings_menu_items(self) -> list:
        h = self.menu_handlers
        return [
            {"label": "Studio Preferences...", "accelerator": "Ctrl+,", "command": h.get("open_settings")},
            {"label": "Hardware Diagnostics...", "command": h.get("open_diagnostics")},
            {"separator": True},
            {"label": "Developer: Component Gallery...", "command": h.get("open_gallery")},
            {"separator": True},
            {"label": "Keyboard Shortcuts Guide", "command": h.get("open_hotkeys_guide")},
        ]

    def _get_help_menu_items(self) -> list:
        h = self.menu_handlers
        return [
            {"label": "Getting Started Checklist...", "command": h.get("open_onboarding")},
            {"separator": True},
            {"label": "Keyboard Shortcuts", "accelerator": "Ctrl+/", "command": h.get("open_hotkeys_guide")},
            {"label": "Hardware Diagnostics", "command": h.get("open_diagnostics")},
            {"separator": True},
            {"label": "About OmniCapture Studio", "command": h.get("open_about")},
        ]

    def apply_tokens(self, tokens: ThemeTokens):
        """Update TopBar widget colors dynamically on theme switch."""
        self.configure(fg_color=tokens.bg_header, border_color=tokens.border_subtle)
        self.title_lbl.configure(text_color=tokens.text_primary)
        self.ver_lbl.configure(text_color=tokens.text_dim)

        for btn in self.menu_buttons:
            btn.configure(hover_color=tokens.bg_hover, text_color=tokens.text_secondary)

        self.center_pill.configure(
            fg_color=tokens.bg_input,
            hover_color=tokens.bg_hover,
            text_color=tokens.text_muted,
            border_color=tokens.border_subtle
        )

        theme_text = "☀ Light" if tokens.is_dark else "🌙 Dark"
        self.btn_theme.configure(
            text=theme_text,
            fg_color=tokens.bg_input,
            hover_color=tokens.bg_hover,
            text_color=tokens.text_secondary,
            border_color=tokens.border_subtle
        )
        self.btn_refresh.configure(
            fg_color=tokens.bg_input,
            hover_color=tokens.bg_hover,
            text_color=tokens.text_secondary,
            border_color=tokens.border_subtle
        )
        self.btn_lock.configure(
            fg_color=tokens.bg_input,
            hover_color=tokens.bg_hover,
            text_color=tokens.text_muted,
            border_color=tokens.border_subtle
        )

    def set_simulated_mode(self, active: bool):
        """Toggle prominent developer-only Simulated Device Mode badge."""
        if active:
            if not self.sim_badge.winfo_ismapped():
                self.sim_badge.pack(side="left", padx=(0, 10), after=self.ver_lbl)
        else:
            if self.sim_badge.winfo_ismapped():
                self.sim_badge.pack_forget()
