import tkinter as tk
import webbrowser
from typing import Dict, Any, Callable, Optional

class DesktopMenuBar:
    """
    True Windows 11 Native Desktop Menu Bar.
    Renders directly in the OS window frame with complete Alt-mnemonic navigation (Alt+F, Alt+C, etc.),
    keyboard accelerators, and clean separation of concerns.
    """

    @classmethod
    def attach(cls, root: tk.Tk, handlers: Dict[str, Callable]):
        menubar = tk.Menu(root)

        # ---------------------------------------------------------------------
        # 1. FILE MENU (Alt + F)
        # ---------------------------------------------------------------------
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(
            label="Open Recordings Folder",
            accelerator="Ctrl+Alt+R",
            command=handlers.get("open_recordings_folder")
        )
        file_menu.add_command(
            label="Change Output Directory...",
            command=handlers.get("change_output_dir")
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Recordings Gallery...",
            command=handlers.get("open_recordings_gallery")
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Minimize to System Tray",
            accelerator="Ctrl+W",
            command=handlers.get("minimize_to_tray")
        )
        file_menu.add_command(
            label="Exit Studio",
            accelerator="Ctrl+Q",
            command=handlers.get("exit_app")
        )
        menubar.add_cascade(label="File", menu=file_menu, underline=0)

        # ---------------------------------------------------------------------
        # 2. CAPTURE MENU (Alt + C)
        # ---------------------------------------------------------------------
        capture_menu = tk.Menu(menubar, tearoff=0)
        capture_menu.add_command(
            label="Start Dual Recording (PC + Camera)",
            accelerator="Ctrl+Alt+D",
            command=handlers.get("start_dual_record")
        )
        capture_menu.add_command(
            label="Launch Screen Mirror",
            accelerator="Ctrl+Alt+M",
            command=handlers.get("launch_mirror")
        )
        capture_menu.add_command(
            label="Start Camera Viewfinder",
            accelerator="Ctrl+Alt+C",
            command=handlers.get("launch_camera")
        )
        capture_menu.add_command(
            label="Start Mobile Screen Record",
            command=handlers.get("start_screen_record")
        )
        capture_menu.add_separator()
        capture_menu.add_command(
            label="Stop Active Recording / Stream",
            accelerator="Esc",
            command=handlers.get("stop_active_recording")
        )
        menubar.add_cascade(label="Capture", menu=capture_menu, underline=0)

        # ---------------------------------------------------------------------
        # 3. TOOLS MENU (Alt + T)
        # ---------------------------------------------------------------------
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(
            label="Command Palette...",
            accelerator="Ctrl+Shift+P",
            command=handlers.get("open_command_palette")
        )
        tools_menu.add_separator()
        tools_menu.add_command(
            label="Release Camera Hardware Lock",
            accelerator="Ctrl+Shift+L",
            command=handlers.get("release_camera_lock")
        )
        tools_menu.add_command(
            label="Switch to Wireless ADB (Wi-Fi)",
            command=handlers.get("switch_wireless_adb")
        )
        tools_menu.add_command(
            label="Refresh Connected Devices",
            accelerator="F5",
            command=handlers.get("refresh_devices")
        )
        tools_menu.add_separator()
        tools_menu.add_command(
            label="System & Device Diagnostics...",
            command=handlers.get("open_diagnostics")
        )
        menubar.add_cascade(label="Tools", menu=tools_menu, underline=0)

        # ---------------------------------------------------------------------
        # 4. VIEW / SCENES MENU (Alt + V)
        # ---------------------------------------------------------------------
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(
            label="Scene: Dual Stream (PC + Phone)",
            accelerator="1",
            command=lambda: handlers.get("switch_scene", lambda s: None)("dual")
        )
        view_menu.add_command(
            label="Scene: Screen Mirror",
            accelerator="2",
            command=lambda: handlers.get("switch_scene", lambda s: None)("mirror")
        )
        view_menu.add_command(
            label="Scene: Camera Sensor Viewfinder",
            accelerator="3",
            command=lambda: handlers.get("switch_scene", lambda s: None)("camera")
        )
        view_menu.add_command(
            label="Scene: Screen Recorder",
            accelerator="4",
            command=lambda: handlers.get("switch_scene", lambda s: None)("screen")
        )
        view_menu.add_separator()
        view_menu.add_command(
            label="Reset Window Size to Default",
            command=handlers.get("reset_window_size")
        )
        menubar.add_cascade(label="View", menu=view_menu, underline=0)

        # ---------------------------------------------------------------------
        # 5. SETTINGS MENU
        # ---------------------------------------------------------------------
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(
            label="Studio Settings...",
            accelerator="Ctrl+,",
            command=handlers.get("open_settings")
        )
        menubar.add_cascade(label="Settings", menu=edit_menu)

        # ---------------------------------------------------------------------
        # 6. HELP MENU (Alt + H)
        # ---------------------------------------------------------------------
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(
            label="Keyboard Shortcuts",
            command=handlers.get("open_hotkeys_guide")
        )
        help_menu.add_command(
            label="Online Documentation",
            command=lambda: webbrowser.open("https://github.com/rajvisual/OmniCapture")
        )
        help_menu.add_separator()
        help_menu.add_command(
            label="About OmniCapture Studio",
            command=handlers.get("open_about")
        )
        menubar.add_cascade(label="Help", menu=help_menu, underline=0)

        # Attach to root window
        root.configure(menu=menubar)
        return menubar
