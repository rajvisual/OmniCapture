# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# In PyInstaller spec files, SPECPATH is the directory containing the spec file
BASE_DIR = Path(SPECPATH).resolve()

# Collect customtkinter themes, images, and modules
ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all("customtkinter")

# Bundled data files: assets, bin, and example config
datas = [
    (str(BASE_DIR / "assets" / "logo"), "assets/logo"),
    (str(BASE_DIR / "bin"), "bin"),
    (str(BASE_DIR / "config.example.json"), "."),
] + ctk_datas

binaries = [] + ctk_binaries

hiddenimports = [
    "PIL",
    "PIL.Image",
    "PIL.ImageTk",
    "pystray",
    "pystray._win32",
    "customtkinter",
    "googleapiclient",
    "google_auth_oauthlib",
    "core.version",
    "core.process_job",
    "core.accessibility",
    "core.simulated_device",
    "gui.dwm",
    "gui.components",
    "gui.components.audio_meter",
    "gui.components.toast",
    "gui.components.command_palette",
    "gui.components.status_chip",
    "gui.components.empty_state",
    "gui.components.menu_dropdown",
    "gui.components.top_bar",
    "gui.components.state_banner",
    "gui.components.frosted_glass",
    "gui.components.segmented_control",
    "gui.dialogs",
    "gui.dialogs.recordings",
    "gui.dialogs.settings",
    "gui.dialogs.diagnostics",
    "gui.dialogs.onboarding",
    "gui.dialogs.simulated_device",
    "gui.menu_bar",
] + ctk_hiddenimports

a = Analysis(
    [str(BASE_DIR / "omni.py")],
    pathex=[str(BASE_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter.test", "unittest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OmniCapture",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # Windowed GUI application (no console popup)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(BASE_DIR / "file_version_info.txt"),
    icon=str(BASE_DIR / "assets" / "logo" / "omnicapture.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="OmniCapture",
)
