"""
Milestone R1 - GitHub Release Automation Script
==============================================
DO NOT EXECUTE WITHOUT EXPLICIT USER APPROVAL: "APPROVED TO PUSH"

This script performs the remote GitHub API actions for Milestone R1:
1. Converts older/intermediate releases (v1.0.0, v1.2.0, v1.3.0) to DRAFT status.
2. Updates release v1.1.0 to "OmniCapture Classic (Terminal) v1.1.0", adds notes,
   and uploads dist/OmniCapture-Classic-v1.1.0-Windows-x64.zip.
3. Creates release v1.4.0 as a DRAFT PRE-RELEASE: "OmniCapture Studio (Desktop GUI) v1.4.0",
   and uploads dist/OmniCapture-Studio-v1.4.0-Windows-x64-Portable.zip and dist/SHA256SUMS.txt.
"""

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / "dist"
REPO_NAME = "rajvisual/OmniCapture"

STUDIO_ZIP_NAME = "OmniCapture-Studio-v1.4.0-Windows-x64-Portable.zip"
CLASSIC_ZIP_NAME = "OmniCapture-Classic-v1.1.0-Windows-x64.zip"
CHECKSUMS_NAME = "SHA256SUMS.txt"


def get_github_token() -> str:
    """Retrieve GitHub token securely from Git Credential Manager without logging."""
    p = subprocess.Popen(
        ["git", "credential", "fill"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, _ = p.communicate(input="protocol=https\nhost=github.com\n\n")
    for line in out.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    raise RuntimeError("Could not retrieve GitHub credentials from Git Credential Manager.")


def github_api_request(endpoint: str, method: str = "GET", data: dict = None, token: str = None) -> dict:
    url = f"https://api.github.com/repos/{REPO_NAME}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "OmniCapture-Release-Manager",
        "Accept": "application/vnd.github.v3+json",
    }
    encoded_data = json.dumps(data).encode("utf-8") if data is not None else None
    if encoded_data:
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def upload_asset(release_id: int, file_path: Path, token: str, content_type: str = "application/octet-stream"):
    url = f"https://uploads.github.com/repos/{REPO_NAME}/releases/{release_id}/assets?name={file_path.name}"
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "OmniCapture-Release-Manager",
        "Content-Type": content_type,
        "Content-Length": str(len(file_bytes)),
    }
    req = urllib.request.Request(url, data=file_bytes, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def execute_r1():
    print("=" * 70)
    print("  OMNICAPTURE MILESTONE R1 - GITHUB RELEASE EXECUTION")
    print("=" * 70)

    token = get_github_token()
    print("[✓] Secure GitHub token acquired via Git Credential Manager.")

    # 1. Fetch all releases
    print("[*] Querying existing GitHub releases...")
    releases = github_api_request("releases", token=token)
    rel_by_tag = {r["tag_name"]: r for r in releases}
    print(f"    Found {len(releases)} existing releases: {list(rel_by_tag.keys())}")

    # 2. Convert v1.0.0, v1.2.0, v1.3.0 to DRAFT
    for draft_tag in ["v1.0.0", "v1.2.0", "v1.3.0"]:
        if draft_tag in rel_by_tag:
            rel = rel_by_tag[draft_tag]
            rel_id = rel["id"]
            if not rel.get("draft", False):
                print(f"[*] Converting {draft_tag} (ID: {rel_id}) to DRAFT...")
                patch_data = {"draft": True}
                github_api_request(f"releases/{rel_id}", method="PATCH", data=patch_data, token=token)
                print(f"[✓] {draft_tag} is now DRAFT (hidden from public releases, tag preserved).")
            else:
                print(f"[-] {draft_tag} is already in DRAFT state.")

    # 3. Update v1.1.0 to OmniCapture Classic (Terminal) v1.1.0
    if "v1.1.0" in rel_by_tag:
        rel_110 = rel_by_tag["v1.1.0"]
        rel_110_id = rel_110["id"]
        print(f"[*] Updating v1.1.0 (ID: {rel_110_id}) to Classic Edition...")
        classic_notes = (
            "# OmniCapture Classic (Terminal) v1.1.0\n\n"
            "This is the official **Classic Terminal Edition** of OmniCapture — the fast, lightweight, "
            "keyboard-driven terminal version with zero desktop GUI overhead.\n\n"
            "### Features:\n"
            "- Low-latency Android screen mirroring and Camera2 stealth capture via bundled scrcpy.\n"
            "- Direct PC screen capture and simultaneous dual recording (FFmpeg required).\n"
            "- Interactive terminal menu (`python omni.py` or `omni.bat`).\n"
            "- Zero GUI dependencies (no CustomTkinter, no display server requirements).\n\n"
            "---\n"
            "> [!TIP]\n"
            "> **Looking for the modern Windows 11 GUI?**\n"
            "> For live dual video preview monitors, visual audio mixer, scene management, and native "
            "Windows 11 Fluent UI, download **[OmniCapture Studio (Desktop GUI) v1.4.0]"
            "(https://github.com/rajvisual/OmniCapture/releases/tag/v1.4.0)**.\n\n"
            "### Installation & Usage:\n"
            "1. Download `OmniCapture-Classic-v1.1.0-Windows-x64.zip` below.\n"
            "2. Extract the archive and double-click `omni.bat`.\n"
        )
        patch_110 = {
            "name": "OmniCapture Classic (Terminal) v1.1.0",
            "body": classic_notes,
            "draft": False,
            "prerelease": False,
        }
        github_api_request(f"releases/{rel_110_id}", method="PATCH", data=patch_110, token=token)
        print(f"[✓] v1.1.0 title and body updated.")

        # Upload Classic asset if not already attached
        existing_assets = [a["name"] for a in rel_110.get("assets", [])]
        classic_zip = DIST_DIR / CLASSIC_ZIP_NAME
        if CLASSIC_ZIP_NAME not in existing_assets and classic_zip.exists():
            print(f"[*] Uploading {CLASSIC_ZIP_NAME} ({classic_zip.stat().st_size / (1024*1024):.2f} MB)...")
            upload_asset(rel_110_id, classic_zip, token, "application/zip")
            print(f"[✓] {CLASSIC_ZIP_NAME} uploaded to Classic release.")
        else:
            print(f"[-] {CLASSIC_ZIP_NAME} already exists on v1.1.0 or archive missing.")

    # 4. Create Studio v1.4.0 as PRE-RELEASE (DRAFT first so user can inspect)
    studio_zip = DIST_DIR / STUDIO_ZIP_NAME
    sums_file = DIST_DIR / CHECKSUMS_NAME
    
    studio_notes = (
        "# OmniCapture Studio (Desktop GUI) v1.4.0 (Pre-Release)\n\n"
        "OmniCapture Studio v1.4.0 transforms OmniCapture into an industry-grade Windows 11 desktop broadcast "
        "workstation for content creators and educators.\n\n"
        "### 🌟 Highlights & Capabilities:\n"
        "- **Windows 11 Fluent Desktop Interface**: Native DWM Mica backdrop, rounded corners, custom caption bar.\n"
        "- **Dual Surface Themes**: Contrast-verified Light Minimal and Dark Liquid Glass.\n"
        "- **DAW Audio Mixer**: Stereo dB peak meters, volume sliders, mute toggles.\n"
        "- **Synchronized Recording**: One-click simultaneous PC screen and mobile camera capture.\n"
        "- **Hardware Diagnostics & Safe Process Lifecycle**: Windows Job Objects prevent orphan scrcpy/ffmpeg processes.\n"
        "- **Accessibility & Focus Ring Engine**: Full keyboard navigation (`Tab`, `Shift+Tab`, `Space`, `Enter`).\n"
        "- **Zero-Install Standalone Portable**: Run directly without Python or dependencies.\n\n"
        "---\n"
        "### 📦 Download & Run:\n"
        "1. Download `OmniCapture-Studio-v1.4.0-Windows-x64-Portable.zip` below.\n"
        "2. Extract anywhere on Windows 10/11.\n"
        "3. Run `OmniCapture.exe`.\n\n"
        "> [!IMPORTANT]\n"
        "> **FFmpeg Requirement**: PC screen recording requires FFmpeg. Install via `winget install Gyan.FFmpeg` "
        "or place `ffmpeg.exe` into the application's `bin/` directory.\n\n"
        "### Verification Checksums:\n"
        "Verify downloads against `SHA256SUMS.txt`.\n"
    )

    print("[*] Creating Studio v1.4.0 release (DRAFT pre-release)...")
    payload_140 = {
        "tag_name": "v1.4.0",
        "name": "OmniCapture Studio (Desktop GUI) v1.4.0",
        "body": studio_notes,
        "draft": True,  # Created as DRAFT first per user instruction
        "prerelease": True,
    }
    rel_140 = github_api_request("releases", method="POST", data=payload_140, token=token)
    rel_140_id = rel_140["id"]
    print(f"[✓] Studio v1.4.0 draft release created (ID: {rel_140_id}).")

    if studio_zip.exists():
        print(f"[*] Uploading {STUDIO_ZIP_NAME} ({studio_zip.stat().st_size / (1024*1024):.2f} MB)...")
        upload_asset(rel_140_id, studio_zip, token, "application/zip")
        print(f"[✓] {STUDIO_ZIP_NAME} uploaded.")

    if sums_file.exists():
        print(f"[*] Uploading {CHECKSUMS_NAME}...")
        upload_asset(rel_140_id, sums_file, token, "text/plain")
        print(f"[✓] {CHECKSUMS_NAME} uploaded.")

    print("\n" + "=" * 70)
    print("  ✅ MILESTONE R1 GITHUB EXECUTION READY")
    print(f"  Studio v1.4.0 URL: {rel_140.get('html_url')}")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--confirm-approved-to-push":
        print("[!] ERROR: This script cannot run without explicit flag --confirm-approved-to-push.")
        sys.exit(1)
    execute_r1()
