import sys
import ctypes
import threading
from typing import Dict, Callable, Optional

# Windows Hotkey Modifier Constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

class GlobalHotkeyManager:
    """
    Native Windows Global Hotkey Manager using Win32 RegisterHotKey API.
    Operates globally across the entire operating system with zero CPU overhead.
    """

    def __init__(self, root_window=None):
        self.root = root_window
        self._hotkeys: Dict[int, Callable[[], None]] = {}
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._running = False
        self._is_windows = (sys.platform == "win32")

    def register(self, hotkey_id: int, modifiers: int, vk_code: int, callback: Callable[[], None]):
        """
        Register a global shortcut key.
        Example: register(1, MOD_CONTROL | MOD_ALT, ord('D'), on_dual_record)
        """
        self._hotkeys[hotkey_id] = callback

    def start(self):
        """Start the Windows message pump thread to listen for registered hotkeys."""
        if not self._is_windows or self._running or not self._hotkeys:
            return

        self._running = True

        def _hotkey_loop():
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            self._thread_id = kernel32.GetCurrentThreadId()

            # Register hotkeys on this thread's message queue
            registered_ids = []
            for hid, (mods, vk) in self._get_key_mappings().items():
                res = user32.RegisterHotKey(None, hid, mods, vk)
                if res:
                    registered_ids.append(hid)

            # Win32 message loop
            msg = ctypes.wintypes.MSG()
            while self._running:
                res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if res == 0 or res == -1:
                    break

                if msg.message == WM_HOTKEY:
                    hid = msg.wParam
                    cb = self._hotkeys.get(hid)
                    if cb:
                        # Schedule execution safely on Tkinter main thread if root is provided
                        if self.root:
                            self.root.after(0, cb)
                        else:
                            cb()

                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

            # Unregister on exit
            for hid in registered_ids:
                user32.UnregisterHotKey(None, hid)

        self._thread = threading.Thread(target=_hotkey_loop, daemon=True, name="OmniHotkeyWorker")
        self._thread.start()

    def _get_key_mappings(self) -> Dict[int, tuple]:
        """Maps default hotkey IDs to modifier and keycode."""
        # Hotkey 1: Ctrl + Alt + D (Dual Recording)
        # Hotkey 2: Ctrl + Alt + M (Display Mirror)
        # Hotkey 3: Ctrl + Alt + C (Stealth Camera Stream)
        # Hotkey 4: Ctrl + Alt + R (Open Recordings Folder)
        return {
            1: (MOD_CONTROL | MOD_ALT, ord("D")),
            2: (MOD_CONTROL | MOD_ALT, ord("M")),
            3: (MOD_CONTROL | MOD_ALT, ord("C")),
            4: (MOD_CONTROL | MOD_ALT, ord("R")),
        }

    def stop(self):
        """Unregister all hotkeys and stop the background message loop."""
        if not self._is_windows or not self._running:
            return
        self._running = False
        if self._thread_id:
            try:
                ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
            except Exception:
                pass
        self._thread = None
        self._thread_id = None
