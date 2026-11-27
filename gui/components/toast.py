import time
from typing import Optional, List
import customtkinter as ctk

from gui.theme import OmniTheme, ThemeTokens

class ToastNotification(ctk.CTkFrame):
    """
    Individual non-blocking desktop toast banner.
    Rendered with crisp desktop typography, semantic accent stripe, and dismiss button.
    Fully theme-aware and WCAG AA contrast compliant.
    """

    def __init__(
        self,
        parent,
        title: str,
        message: str,
        level: str = "info",
        duration_ms: int = 3500,
        action_text: Optional[str] = None,
        action_cmd: Optional[callable] = None,
        on_dismiss: Optional[callable] = None,
        **kwargs
    ):
        tokens = OmniTheme.get_tokens()
        super().__init__(
            parent,
            fg_color=tokens.bg_raised,
            border_width=1,
            border_color=tokens.border_default,
            corner_radius=OmniTheme.RADIUS_POPUP,
            **kwargs
        )

        # Rules: Errors persist until user dismisses (duration=0); others auto-dismiss 3.5s
        if level == "error":
            duration_ms = 0
        self.duration_ms = duration_ms
        self.on_dismiss = on_dismiss
        self._dismiss_job = None

        # Determine accent color based on level
        if level == "success":
            accent = tokens.status_connected
            symbol = "✓"
        elif level == "warning":
            accent = tokens.status_warning
            symbol = "⚠"
        elif level == "error":
            accent = tokens.status_recording
            symbol = "✕"
        else:
            accent = tokens.accent_primary
            symbol = "ℹ"

        # Accent border indicator on left
        stripe = ctk.CTkFrame(self, fg_color=accent, width=4, corner_radius=0)
        stripe.pack(side="left", fill="y")

        # Content column
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, padx=(10, 8), pady=8)

        # Header with symbol and title
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text=f"{symbol}  {title}",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=tokens.text_primary,
            anchor="w"
        ).pack(side="left")

        # Close button
        close_btn = ctk.CTkButton(
            self,
            text="×",
            width=20,
            height=20,
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            hover_color=tokens.bg_hover,
            text_color=tokens.text_muted,
            command=self.dismiss
        )
        close_btn.pack(side="right", padx=(0, 6), pady=6, anchor="n")

        # Message body
        if message:
            msg_lbl = ctk.CTkLabel(
                content,
                text=message,
                font=OmniTheme.font_label(),
                text_color=tokens.text_secondary,
                anchor="w",
                justify="left",
                wraplength=280
            )
            msg_lbl.pack(fill="x", pady=(2, 0))

        # Optional action button
        if action_text and action_cmd:
            act_btn = ctk.CTkButton(
                content,
                text=action_text,
                height=22,
                width=72,
                font=OmniTheme.font_caption(),
                fg_color=tokens.accent_primary,
                hover_color=tokens.accent_hover,
                text_color="#FFFFFF",
                corner_radius=OmniTheme.RADIUS_CONTROL,
                command=lambda: [action_cmd(), self.dismiss()]
            )
            act_btn.pack(anchor="w", pady=(4, 0))

        # Schedule auto-dismiss (strictly 3 seconds by default)
        if duration_ms > 0:
            self._dismiss_job = self.after(duration_ms, self.dismiss)

    def dismiss(self):
        if self._dismiss_job:
            try:
                self.after_cancel(self._dismiss_job)
            except Exception:
                pass
            self._dismiss_job = None

        if self.on_dismiss:
            self.on_dismiss(self)
        try:
            self.destroy()
        except Exception:
            pass


class ToastNotificationManager:
    """
    Manages in-app floating toast notifications inside the desktop window.
    Positions banners neatly in the bottom-right corner above the telemetry footer,
    stacking vertically upwards so primary controls are never obstructed.
    """

    def __init__(self, root_window: ctk.CTk):
        self.root = root_window
        self.active_toasts: List[ToastNotification] = []

    def show(
        self,
        title: str,
        message: str = "",
        level: str = "info",
        duration_ms: int = 3500,
        action_text: Optional[str] = None,
        action_cmd: Optional[callable] = None
    ):
        """Display an in-app non-blocking toast with 3.5s auto-dismiss (errors persist)."""
        # Ensure executed on the Tkinter GUI thread
        self.root.after(0, lambda: self._create_toast(title, message, level, duration_ms, action_text, action_cmd))

    def _create_toast(
        self,
        title: str,
        message: str,
        level: str,
        duration_ms: int,
        action_text: Optional[str] = None,
        action_cmd: Optional[callable] = None
    ):
        # Limit visible toasts to 3 to prevent clutter
        if len(self.active_toasts) >= 3:
            oldest = self.active_toasts.pop(0)
            oldest.dismiss()

        toast = ToastNotification(
            self.root,
            title=title,
            message=message,
            level=level,
            duration_ms=duration_ms,
            action_text=action_text,
            action_cmd=action_cmd,
            on_dismiss=self._on_toast_dismissed,
            width=320
        )
        self.active_toasts.append(toast)
        self._reposition_toasts()

    def _on_toast_dismissed(self, toast: ToastNotification):
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)
        self._reposition_toasts()

    def _reposition_toasts(self):
        # Position in bottom-right corner, stacked vertically upwards above 28px footer
        y_bottom_offset = 38
        for toast in reversed(self.active_toasts):
            try:
                toast.place(relx=0.985, rely=1.0, y=-y_bottom_offset, anchor="se")
                toast.lift()
                y_bottom_offset += 68
            except Exception:
                pass
