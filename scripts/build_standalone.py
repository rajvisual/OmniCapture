#!/usr/bin/env python3
"""
OmniCapture Standalone Portable Executable Builder
Uses PyInstaller to generate zero-install Windows binary distribution.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SPEC_FILE = BASE_DIR / "OmniCapture.spec"
DIST_DIR = BASE_DIR / "dist" / "OmniCapture"

def main():
    print("=" * 70)
    print("  🔨 OMNICAPTURE STANDALONE PORTABLE BUNDLE BUILDER")
    print("=" * 70)
    print(f"Base Directory: {BASE_DIR}")
    print(f"Spec File:      {SPEC_FILE}")
    print(f"Target Output:  {DIST_DIR}\n")

    if not SPEC_FILE.exists():
        print(f"[!] Error: Spec file not found at {SPEC_FILE}")
        sys.exit(1)

    # Clean previous build artifacts
    build_dir = BASE_DIR / "build"
    if build_dir.exists():
        print("[*] Cleaning build/ directory...")
        shutil.rmtree(build_dir, ignore_errors=True)

    print("[*] Running PyInstaller build...")
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        str(SPEC_FILE)
    ]

    res = subprocess.run(cmd, cwd=str(BASE_DIR))
    if res.returncode != 0:
        print(f"\n[!] PyInstaller build failed with exit code {res.returncode}")
        sys.exit(res.returncode)

    # Post-build setup
    print("\n[*] Post-build packaging setup...")
    rec_dir = DIST_DIR / "recordings"
    rec_dir.mkdir(parents=True, exist_ok=True)
    (rec_dir / ".gitkeep").write_text("", encoding="utf-8")

    # Copy config example if not already present
    cfg_src = BASE_DIR / "config.example.json"
    cfg_dst = DIST_DIR / "config.json"
    if cfg_src.exists() and not cfg_dst.exists():
        shutil.copy2(cfg_src, cfg_dst)
        print("  [✓] Default config.json copied to portable bundle")

    exe_path = DIST_DIR / "OmniCapture.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 70)
        print("  ✅ PORTABLE BUNDLE BUILT SUCCESSFULLY!")
        print(f"  Binary Location: {exe_path}")
        print(f"  Executable Size: {size_mb:.2f} MB")
        print("  Status: Zero-install portable bundle ready for distribution.")
        print("=" * 70 + "\n")
    else:
        print("[!] Warning: OmniCapture.exe was not found in dist directory.")
        sys.exit(1)

if __name__ == "__main__":
    main()
