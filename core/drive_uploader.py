import os
import sys
import time
import shutil
import json
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

class DriveUploader:
    def __init__(self, config_dict: Dict[str, Any]):
        self.config = config_dict
        self.drive_cfg = self.config.get("google_drive", {})
        self.desktop_sync_path = self._detect_desktop_drive()

    def _detect_desktop_drive(self) -> Optional[Path]:
        """Detect Google Drive for Desktop virtual drive or sync folder across all drive letters."""
        def safe_exists(p: Path) -> bool:
            try:
                return p.exists()
            except (OSError, PermissionError):
                return False

        configured_path = self.drive_cfg.get("desktop_sync_path")
        if configured_path and safe_exists(Path(configured_path)):
            target = Path(configured_path)
            if target.is_dir():
                return target

        # Check all possible drive letters D: through Z: for Google Drive mount
        import string
        for letter in string.ascii_uppercase[3:]:
            for sub in ["My Drive", "Google Drive", ""]:
                candidate = Path(f"{letter}:/{sub}") if sub else Path(f"{letter}:/")
                if safe_exists(candidate) and safe_exists(candidate / "My Drive"):
                    candidate = candidate / "My Drive"
                if safe_exists(candidate) and (letter not in ("C", "E") or sub):
                    # Check if this drive looks like Google Drive
                    if safe_exists(candidate / "My Drive") or "My Drive" in str(candidate):
                        target = candidate / "OmniCapture"
                        try:
                            target.mkdir(parents=True, exist_ok=True)
                            return target
                        except Exception:
                            pass

        # Standard Windows mount points for Google Drive for Desktop
        candidates = [
            Path("G:/My Drive"),
            Path("G:/"),
            Path("H:/My Drive"),
            Path("H:/"),
            Path(os.path.expanduser("~")) / "Google Drive",
            Path(os.path.expanduser("~")) / "GoogleDrive",
        ]
        for c in candidates:
            if safe_exists(c):
                target = c / "OmniCapture"
                try:
                    target.mkdir(parents=True, exist_ok=True)
                    return target
                except Exception:
                    pass
        return None

    def upload_file(self, file_path: str, progress_callback=None) -> Tuple[bool, str]:
        """
        Upload file using either Google Drive for Desktop Sync or Google Drive API.
        Returns (success, message_or_link).
        """
        path = Path(file_path)
        if not path.is_file():
            return False, f"File not found: {file_path}"

        method = self.drive_cfg.get("method", "auto")

        # 1. Desktop Sync Check
        if method in ("desktop", "auto") and self.desktop_sync_path:
            return self._sync_to_desktop(path)

        # 2. Google Drive API Check
        if method in ("api", "auto"):
            api_ok, msg = self._upload_via_api(path, progress_callback)
            if api_ok:
                return True, msg
            if method == "api":
                return False, msg

        # Fallback if both not available
        if method == "desktop":
            return False, (
                "Google Drive Desktop virtual drive (e.g. G:\\My Drive) not detected.\n"
                "1. If Google Drive for Desktop is installed, make sure it is running.\n"
                "2. If it syncs to a custom folder, set it via 'python omni.py drive-setup' (Option 2)."
            )
        return False, (
            "Google Drive is not yet configured.\n"
            "Run 'python omni.py drive-setup' to authenticate or configure sync."
        )

    def _sync_to_desktop(self, src_path: Path) -> Tuple[bool, str]:
        """Copy file directly to Google Drive Desktop sync folder."""
        dest_folder = self.desktop_sync_path
        dest_path = dest_folder / src_path.name
        try:
            print(f"\033[96m[Google Drive Desktop]\033[0m Syncing to {dest_path}...")
            shutil.copy2(str(src_path), str(dest_path))
            return True, f"Synced to Google Drive: {dest_path}"
        except Exception as e:
            return False, f"Desktop sync copy failed: {e}"

    def _upload_via_api(self, file_path: Path, progress_callback=None) -> Tuple[bool, str]:
        """Upload via official Google Drive v3 REST API with resumable upload."""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
        except ImportError:
            return False, "Google API libraries not installed. Install with: pip install -r requirements.txt"

        SCOPES = ["https://www.googleapis.com/auth/drive.file"]
        creds = None
        token_path = Path(self.drive_cfg.get("token_file", "drive_token.json"))
        client_secrets_path = Path(self.drive_cfg.get("credentials_file", "client_secrets.json"))

        # Look in omnicapture root
        base_dir = Path(__file__).resolve().parent.parent
        if not token_path.is_absolute():
            token_path = base_dir / token_path
        if not client_secrets_path.is_absolute():
            client_secrets_path = base_dir / client_secrets_path

        if token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            except Exception:
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None
            if not creds:
                if not client_secrets_path.exists():
                    return False, f"Missing '{client_secrets_path.name}'. Place Google Cloud OAuth client_secrets.json in omnicapture directory."
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), SCOPES)
                    creds = flow.run_local_server(port=0)
                    with open(token_path, "w", encoding="utf-8") as f:
                        f.write(creds.to_json())
                except Exception as e:
                    return False, f"OAuth authentication failed: {e}"

        # Initialize Drive service
        try:
            service = build("drive", "v3", credentials=creds)

            # Find or create OmniCapture folder
            folder_id = self.drive_cfg.get("folder_id")
            if not folder_id:
                folder_id = self._get_or_create_drive_folder(service, "OmniCapture Recordings")

            file_metadata = {
                "name": file_path.name,
                "parents": [folder_id] if folder_id else []
            }
            media = MediaFileUpload(
                str(file_path),
                mimetype="video/mp4" if file_path.suffix.lower() == ".mp4" else "video/x-matroska",
                resumable=True,
                chunksize=5 * 1024 * 1024
            )

            request = service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, webViewLink, webContentLink"
            )

            response = None
            total_size = file_path.stat().st_size
            print(f"\033[96m[Google Drive Upload]\033[0m Uploading {file_path.name} ({total_size / (1024*1024):.1f} MB)...")

            while response is None:
                status, response = request.next_chunk()
                if status:
                    percent = int(status.progress() * 100)
                    sys.stdout.write(f"\r\033[93m[Upload Progress]\033[0m {percent}% completed")
                    sys.stdout.flush()

            print("\r\033[92m[Upload Complete!]\033[0m 100% finished!              ")
            link = response.get("webViewLink") or f"https://drive.google.com/file/d/{response.get('id')}/view"
            return True, f"Uploaded to Google Drive: {link}"

        except Exception as e:
            return False, f"Drive upload error: {e}"

    def _get_or_create_drive_folder(self, service, folder_name: str) -> Optional[str]:
        """Search for folder in Google Drive root or create it if not found."""
        query = f"mimeType = 'application/vnd.google-apps.folder' and name = '{folder_name}' and trashed = false"
        res = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
        files = res.get("files", [])
        if files:
            return files[0]["id"]

        # Create folder
        meta = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        folder = service.files().create(body=meta, fields="id").execute()
        return folder.get("id")
