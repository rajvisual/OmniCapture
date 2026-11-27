"""
Package OmniCapture Classic v1.1.0 and generate SHA256SUMS.txt
"""
import hashlib
import os
import subprocess
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = BASE_DIR / "dist"
DIST_DIR.mkdir(parents=True, exist_ok=True)

CLASSIC_TAG = "v1.1.0"
STUDIO_ZIP_NAME = "OmniCapture-Studio-v1.4.0-Windows-x64-Portable.zip"
CLASSIC_ZIP_NAME = "OmniCapture-Classic-v1.1.0-Windows-x64.zip"

STUDIO_ZIP = DIST_DIR / STUDIO_ZIP_NAME
CLASSIC_ZIP = DIST_DIR / CLASSIC_ZIP_NAME
SHA256_FILE = DIST_DIR / "SHA256SUMS.txt"


def get_git_file(ref: str, path: str) -> bytes:
    res = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return res.stdout


def list_git_files(ref: str) -> list[str]:
    res = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ref],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return [line.strip() for line in res.stdout.splitlines() if line.strip()]


def create_classic_zip():
    print(f"[*] Packaging {CLASSIC_ZIP_NAME} from git tag {CLASSIC_TAG}...")
    files = list_git_files(CLASSIC_TAG)
    
    note = (
        "> [!NOTE]\n"
        "> **Looking for the modern Windows 11 GUI?**\n"
        "> You are viewing **OmniCapture Classic (Terminal Edition)** — the lightweight, keyboard-driven terminal version.\n"
        "> For the broadcast studio application featuring dual live previews, audio mixing, scene management, and a native Windows 11 Fluent UI, download **[OmniCapture Studio (Desktop GUI)](https://github.com/rajvisual/OmniCapture/releases/tag/v1.4.0)**.\n\n"
    ).encode("utf-8")

    with zipfile.ZipFile(CLASSIC_ZIP, "w", zipfile.ZIP_DEFLATED) as zout:
        for fpath in files:
            content = get_git_file(CLASSIC_TAG, fpath)
            if fpath == "README.md":
                content = note + content
            # Prefix archive with top-level directory for clean extraction
            arcname = f"OmniCapture-Classic-v1.1.0/{fpath}"
            zout.writestr(arcname, content)

    size_mb = CLASSIC_ZIP.stat().st_size / (1024 * 1024)
    print(f"[✓] Created: {CLASSIC_ZIP} ({size_mb:.2f} MB, {len(files)} files)")


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def write_checksums():
    print("[*] Computing SHA256 checksums...")
    checksums = []
    
    if STUDIO_ZIP.exists():
        h = compute_sha256(STUDIO_ZIP)
        checksums.append(f"{h}  {STUDIO_ZIP_NAME}")
        print(f"  Studio:  {h}  {STUDIO_ZIP_NAME} ({STUDIO_ZIP.stat().st_size:,} bytes)")
    else:
        print(f"[!] Warning: {STUDIO_ZIP} does not exist!")

    if CLASSIC_ZIP.exists():
        h = compute_sha256(CLASSIC_ZIP)
        checksums.append(f"{h}  {CLASSIC_ZIP_NAME}")
        print(f"  Classic: {h}  {CLASSIC_ZIP_NAME} ({CLASSIC_ZIP.stat().st_size:,} bytes)")
    else:
        print(f"[!] Warning: {CLASSIC_ZIP} does not exist!")

    content = "\n".join(checksums) + "\n"
    with open(SHA256_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[✓] Written: {SHA256_FILE}")


if __name__ == "__main__":
    create_classic_zip()
    write_checksums()
