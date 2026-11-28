"""
Package OmniCapture Studio v2.0.0 and update SHA256SUMS.txt
"""
import hashlib
import os
import subprocess
import time
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = BASE_DIR / "dist"
DIST_DIR.mkdir(parents=True, exist_ok=True)

STUDIO_ZIP_NAME = "OmniCapture-Studio-v2.0.0-Windows-x64-Portable.zip"
CLASSIC_ZIP_NAME = "OmniCapture-Classic-v1.1.0-Windows-x64.zip"

STUDIO_ZIP = DIST_DIR / STUDIO_ZIP_NAME
CLASSIC_ZIP = DIST_DIR / CLASSIC_ZIP_NAME
SHA256_FILE = DIST_DIR / "SHA256SUMS.txt"


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def create_studio_zip():
    bundle_dir = DIST_DIR / "OmniCapture"
    if not bundle_dir.exists():
        raise RuntimeError(f"Bundle directory {bundle_dir} does not exist! Run build_standalone.py first.")

    print(f"[*] Packaging {STUDIO_ZIP_NAME} from {bundle_dir}...")
    file_count = 0
    with zipfile.ZipFile(STUDIO_ZIP, "w", zipfile.ZIP_DEFLATED) as zout:
        for root, dirs, files in os.walk(bundle_dir):
            for f in files:
                full_path = Path(root) / f
                rel_path = full_path.relative_to(DIST_DIR)
                zout.write(full_path, rel_path.as_posix())
                file_count += 1

    size_mb = STUDIO_ZIP.stat().st_size / (1024 * 1024)
    print(f"[✓] Created: {STUDIO_ZIP} ({size_mb:.2f} MB, {file_count} files)")


def update_checksums():
    print("[*] Computing SHA256 checksums for v2.0.0...")
    checksums = []

    if STUDIO_ZIP.exists():
        h = compute_sha256(STUDIO_ZIP)
        checksums.append(f"{h}  {STUDIO_ZIP_NAME}")
        print(f"  Studio v2.0.0:  {h}  {STUDIO_ZIP_NAME} ({STUDIO_ZIP.stat().st_size:,} bytes)")
    else:
        print(f"[!] Warning: {STUDIO_ZIP} does not exist!")

    if CLASSIC_ZIP.exists():
        h = compute_sha256(CLASSIC_ZIP)
        checksums.append(f"{h}  {CLASSIC_ZIP_NAME}")
        print(f"  Classic v1.1.0: {h}  {CLASSIC_ZIP_NAME} ({CLASSIC_ZIP.stat().st_size:,} bytes)")
    else:
        print(f"[!] Warning: {CLASSIC_ZIP} does not exist!")

    content = "\n".join(checksums) + "\n"
    with open(SHA256_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[✓] Written: {SHA256_FILE}")


if __name__ == "__main__":
    create_studio_zip()
    update_checksums()
