import time
from typing import Optional, List
import customtkinter as ctk

from gui.theme import OmniTheme

class ToastNotification(ctk.CTkFrame):
    """
    Individual non-blocking desktop toast banner.
    Rendered with crisp desktop typography, semantic accent stripe, and dismiss button.
    """

    def __init__(
        self,
        parent,
        title: str,
        message: str,
        level: str = "info",
        duration_ms: int = 4000,
        on_dismiss: Optional[callable] = None,
        **kwargs
    ):
        super().__init__(
            parent,
            fg_color=OmniTheme.BG_CARD,
            border_width=1,
            border_color=OmniTheme.BORDER_DEFAULT,
            corner_radius=OmniTheme.RADIUS_POPUP,
            **kwargs
        )

        self.duration_ms = duration_ms
        self.on_dismiss = on_dismiss
        self._dismiss_job = None

        # Determine accent color based on level
        if level == "success":
            accent = OmniTheme.STATUS_CONNECTED
            symbol = "✓"
        elif level == "warning":
            accent = OmniTheme.STATUS_WARNING
            symbol = "⚠"
        elif level == "error":
            accent = OmniTheme.STATUS_RECORDING
            symbol = "✕"
        else:
            accent = OmniTheme.ACCENT_PRIMARY
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
            text_color=OmniTheme.TEXT_MAIN,
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
            hover_color=OmniTheme.BG_INPUT,
            text_color=OmniTheme.TEXT_MUTED,
            command=self.dismiss
        )
        close_btn.pack(side="right", padx=(0, 6), pady=6, anchor="n")

        # Message body
        if message:
            msg_lbl = ctk.CTkLabel(
                content,
                text=message,
                font=OmniTheme.font_label(),
                text_color=OmniTheme.TEXT_BODY,
                anchor="w",
                justify="left",
                wraplength=280
            )
            msg_lbl.pack(fill="x", pady=(2, 0))

        # Schedule auto-dismiss
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
    Positions banners neatly in the top-right corner with zero impact on main workflow.
    """

    def __init__(self, root_window: ctk.CTk):
        self.root = root_window
        self.active_toasts: List[ToastNotification] = []

    def show(self, title: str, message: str = "", level: str = "info", duration_ms: int = 3800):
        """Display an in-app non-blocking toast."""
        # Ensure executed on the Tkinter GUI thread
        self.root.after(0, lambda: self._create_toast(title, message, level, duration_ms))

    def _create_toast(self, title: str, message: str, level: str, duration_ms: int):
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
        # Stack from top-right corner downward
        top_offset = 54
        for toast in self.active_toasts:
            try:
                toast.place(relx=0.985, y=top_offset, anchor="ne")
                toast.lift()
                top_offset += 72
            except Exception:
                pass
