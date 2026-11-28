"""
Publish OmniCapture Studio v2.0.0 to GitHub Releases
"""
import json
import subprocess
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / "dist"
REPO_NAME = "rajvisual/OmniCapture"

STUDIO_ZIP = DIST_DIR / "OmniCapture-Studio-v2.0.0-Windows-x64-Portable.zip"
SETUP_EXE = DIST_DIR / "OmniCapture-Studio-v2.0.0-Setup.exe"
CHECKSUMS = DIST_DIR / "SHA256SUMS.txt"


def get_token() -> str:
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
    raise RuntimeError("Could not retrieve token.")


def github_req(endpoint: str, method: str = "GET", data: dict = None, token: str = None) -> dict:
    url = f"https://api.github.com/repos/{REPO_NAME}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "OmniCapture-Release",
        "Accept": "application/vnd.github.v3+json",
    }
    encoded = json.dumps(data).encode("utf-8") if data is not None else None
    if encoded:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=encoded, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        body = resp.read()
        if not body:
            return {}
        return json.loads(body.decode("utf-8"))


def upload_asset(release_id: int, file_path: Path, token: str, content_type: str = "application/octet-stream"):
    url = f"https://uploads.github.com/repos/{REPO_NAME}/releases/{release_id}/assets?name={file_path.name}"
    with open(file_path, "rb") as f:
        data = f.read()
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "OmniCapture-Release",
        "Content-Type": content_type,
        "Content-Length": str(len(data)),
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    token = get_token()
    print("[*] Acquired GitHub token.")

    releases = github_req("releases", token=token)
    rel_by_tag = {r["tag_name"]: r for r in releases}

    notes = (
        "# OmniCapture Studio v2.0.0 — Native Windows 11 Desktop Application\n\n"
        "**OmniCapture Studio v2.0.0** elevates OmniCapture into a true, standalone Windows 11 desktop broadcast "
        "workstation for content creators and educators — completely eliminating the terminal and command prompt.\n\n"
        "---\n\n"
        "### 🌟 Highlights & New Features in v2.0.0:\n"
        "- **100% Zero-Terminal Desktop Experience**:\n"
        "  - Double-clicking `OmniCapture.exe` launches the Windows 11 GUI Studio directly with zero black CMD windows, "
        "zero terminal menus, and zero command-line overhead.\n"
        "  - Added `studio.pyw` and silent `OmniCapture Studio.vbs` launchers for source users.\n"
        "  - Added 1-click Windows Desktop Shortcut generator (`scripts/create_desktop_shortcut.ps1`).\n"
        "- **Broadcast Console Architecture**:\n"
        "  - Native Windows 11 DWM Mica / Acrylic backdrop integration with custom top bar and dark titlebar.\n"
        "  - Two contrast-verified themes: **Dark Liquid Glass** and **Light Minimal** (100% WCAG AA compliant).\n"
        "  - DAW-style audio mixer channel strips with real dB peak VU meters and volume controls.\n"
        "  - Creator Hero Mode: 1-click synchronized PC screen and mobile camera capture with sub-millisecond sync metadata.\n"
        "- **Robust Reliability & Safety**:\n"
        "  - Crash-safe Matroska (`.mkv`) and fragmented MP4 stream recording with startup recovery.\n"
        "  - Win32 Job Object isolation: guarantees zero orphaned scrcpy/ffmpeg/adb processes upon exit or crash.\n"
        "  - 21-state Studio State Banner matrix with plain-language cause summaries and 1-click remedies.\n"
        "  - Full keyboard accessibility engine with tab focus rings and safe dismiss (`Escape` never stops recording).\n\n"
        "---\n\n"
        "### 📦 Download Options:\n"
        "- **Recommended for Windows 11**: **[OmniCapture-Studio-v2.0.0-Setup.exe](https://github.com/rajvisual/OmniCapture/releases/download/v2.0.0/OmniCapture-Studio-v2.0.0-Setup.exe)** (27.4 MB)\n"
        "  1-click native Windows installer. Automatically creates Desktop and Start Menu shortcuts. Zero UAC prompts required.\n"
        "- **Zero-Install Standalone Portable**: **[OmniCapture-Studio-v2.0.0-Windows-x64-Portable.zip](https://github.com/rajvisual/OmniCapture/releases/download/v2.0.0/OmniCapture-Studio-v2.0.0-Windows-x64-Portable.zip)** (46.9 MB)\n"
        "  Extract anywhere on your PC and double-click `OmniCapture.exe` to launch immediately!\n\n"
        "> [!NOTE]\n"
        "> **FFmpeg Requirement**: PC screen recording requires FFmpeg. Install via `winget install Gyan.FFmpeg` "
        "or drop `ffmpeg.exe` into the app's `bin/` directory.\n\n"
        "### 🔐 Verification Checksums (SHA-256):\n"
        "```text\n"
        "39047e17c104387404422afe0f0eab43d6072bcdc757b1a7c5da0aee66d6dde6  OmniCapture-Studio-v2.0.0-Setup.exe\n"
        "7ded9025dbaa21de1616d88459b1a2e2d49501c6bcd749456dc284e39f719d31  OmniCapture-Studio-v2.0.0-Windows-x64-Portable.zip\n"
        "17246d92222385590f5586c776d1d8f3d3ace32fb4ab600f95283f37b40491ce  OmniCapture-Classic-v1.1.0-Windows-x64.zip\n"
        "```\n\n"
        "---\n"
        "*Prefer a pure keyboard-driven terminal? Download [OmniCapture Classic (Terminal) v1.1.0]"
        "(https://github.com/rajvisual/OmniCapture/releases/tag/v1.1.0).*"
    )

    if "v2.0.0" not in rel_by_tag:
        print("[*] Creating release v2.0.0...")
        payload = {
            "tag_name": "v2.0.0",
            "name": "OmniCapture Studio v2.0.0 (Native Desktop Application)",
            "body": notes,
            "draft": False,
            "prerelease": False,
        }
        rel = github_req("releases", method="POST", data=payload, token=token)
        rel_id = rel["id"]
        print(f"[✓] Release v2.0.0 created (ID: {rel_id})")
    else:
        rel = rel_by_tag["v2.0.0"]
        rel_id = rel["id"]
        print(f"[*] Updating existing release v2.0.0 (ID: {rel_id})...")
        payload = {
            "name": "OmniCapture Studio v2.0.0 (Native Desktop Application)",
            "body": notes,
            "draft": False,
            "prerelease": False,
        }
        github_req(f"releases/{rel_id}", method="PATCH", data=payload, token=token)

    # Upload assets
    rel_data = github_req(f"releases/{rel_id}", token=token)
    existing_assets = {a["name"]: a["id"] for a in rel_data.get("assets", [])}

    def safe_upload(file_path: Path, content_type: str):
        if not file_path.exists():
            return
        if file_path.name in existing_assets:
            asset_id = existing_assets[file_path.name]
            print(f"[*] Deleting existing asset {file_path.name} (ID: {asset_id})...")
            github_req(f"releases/assets/{asset_id}", method="DELETE", token=token)
        print(f"[*] Uploading {file_path.name} ({file_path.stat().st_size / (1024*1024):.2f} MB)...")
        upload_asset(rel_id, file_path, token, content_type)
        print(f"[✓] {file_path.name} uploaded successfully.")

    safe_upload(SETUP_EXE, "application/octet-stream")
    safe_upload(STUDIO_ZIP, "application/zip")
    safe_upload(CHECKSUMS, "text/plain")

    print("\n" + "=" * 70)
    print("  ✅ OMNICAPTURE STUDIO v2.0.0 PUBLISHED SUCCESSFULLY!")
    print(f"  URL: https://github.com/rajvisual/OmniCapture/releases/tag/v2.0.0")
    print("=" * 70)


if __name__ == "__main__":
    main()
