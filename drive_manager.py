"""
Google Drive integration for BikeCommute Analytics
Handles OAuth2 authentication and GPX file management
"""
import os
import json
import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import discovery
from config import (
    GOOGLE_DRIVE_FOLDER_NAME,
    GOOGLE_DRIVE_FOLDER_ID,
    GOOGLE_SCOPES,
    CREDENTIALS_FILE,
    TOKEN_FILE,
    TCX_DOWNLOAD_DIR,
    PROCESSED_FILES_DB,
)


class GoogleDriveManager:
    def __init__(self):
        self.service = None
        self.folder_id = None
        self.processed_files = self._load_processed_files()
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Drive API using OAuth2"""
        creds = None

        # Check if token.json exists
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "rb") as token:
                creds = pickle.load(token)

        # If no valid credentials, perform OAuth2 flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"{CREDENTIALS_FILE} not found. Please set up Google OAuth credentials."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, GOOGLE_SCOPES
                )
                # Opens browser for user authentication
                creds = flow.run_local_server(port=0)

            # Save credentials to token.json for future runs
            with open(TOKEN_FILE, "wb") as token:
                pickle.dump(creds, token)

        self.service = discovery.build("drive", "v3", credentials=creds)

    def _find_folder_id(self):
        """Get the folder ID for GPX files"""
        if self.folder_id:
            return self.folder_id

        if not GOOGLE_DRIVE_FOLDER_ID:
            raise ValueError(
                "GOOGLE_DRIVE_FOLDER_ID not found in .env file. "
                "Please add: GOOGLE_DRIVE_FOLDER_ID=your_folder_id"
            )

        self.folder_id = GOOGLE_DRIVE_FOLDER_ID
        print(f"Using folder ID: {self.folder_id} ({GOOGLE_DRIVE_FOLDER_NAME})")
        return self.folder_id

    def _load_processed_files(self):
        """Load the list of already processed file IDs"""
        if os.path.exists(PROCESSED_FILES_DB):
            with open(PROCESSED_FILES_DB, "r") as f:
                return json.load(f)
        return {"processed": []}

    def _save_processed_files(self):
        """Save the list of processed file IDs"""
        with open(PROCESSED_FILES_DB, "w") as f:
            json.dump(self.processed_files, f, indent=2)

    def list_tcx_files(self):
        """List all TCX files in the Health Sync folder"""
        folder_id = self._find_folder_id()

        try:
            results = (
                self.service.files()
                .list(
                    q=f"'{folder_id}' in parents and name contains '.tcx' and trashed=false",
                    spaces="drive",
                    fields="files(id, name, createdTime, modifiedTime)",
                    pageSize=100,
                    orderBy="modifiedTime desc"
                )
                .execute()
            )

            files = results.get("files", [])
            print(f"📁 Found {len(files)} TCX files in folder:")
            for f in files:
                mod_time = f.get('modifiedTime', 'unknown')[:10]
                print(f"   - {f['name']} (ID: {f['id'][:10]}..., modified: {mod_time})")
            return files
        except Exception as e:
            print(f"Error listing files: {e}")
            return []

    def get_new_files(self):
        """Get list of unprocessed TCX files - checks both ID and modification date"""
        from datetime import datetime, timedelta

        all_files = self.list_tcx_files()
        print(f"✓ Total files on Drive: {len(all_files)}")
        print(f"✓ Already processed: {len(self.processed_files['processed'])} files")

        new_files = []
        today = datetime.now().date()

        for f in all_files:
            file_id = f["id"]
            is_in_processed = file_id in self.processed_files["processed"]

            # Check modification date
            mod_time_str = f.get('modifiedTime', '')[:10]  # YYYY-MM-DD
            try:
                mod_date = datetime.fromisoformat(mod_time_str).date()
                is_recent = (today - mod_date).days <= 1  # Modified today or yesterday
            except:
                is_recent = False
                mod_date = None

            # Add file if: not processed OR modified recently (prevents missing re-uploaded files)
            if not is_in_processed or is_recent:
                new_files.append(f)
                status = "NEW ID" if not is_in_processed else "RE-MODIFIED"
                print(f"   → {f['name']} ({status}, mod: {mod_date})")

        print(f"✓ New/modified files to process: {len(new_files)}")

        # Debug: show all files with status
        if not new_files and all_files:
            print("⚠️  No new files found. Showing all files:")
            for f in all_files:
                mod_time_str = f.get('modifiedTime', '')[:10]
                in_db = "✓ PROCESSED" if f["id"] in self.processed_files["processed"] else "✗ NOT IN DB"
                print(f"   {f['name']} ({mod_time_str}) - {in_db}")

        return new_files

    def download_tcx_file(self, file_id, file_name):
        """Download a single TCX file from Google Drive"""
        # Create TCX directory if it doesn't exist
        Path(TCX_DOWNLOAD_DIR).mkdir(exist_ok=True)

        local_path = os.path.join(TCX_DOWNLOAD_DIR, file_name)

        try:
            request = self.service.files().get_media(fileId=file_id)
            with open(local_path, "wb") as f:
                f.write(request.execute())

            print(f"Downloaded: {file_name}")
            return local_path
        except Exception as e:
            print(f"Error downloading {file_name}: {e}")
            return None

    def sync_new_files(self):
        """Download all new TCX files and mark them as processed"""
        new_files = self.get_new_files()

        if not new_files:
            print("No new TCX files to sync.")
            return []

        print(f"Found {len(new_files)} new TCX file(s)")
        downloaded_files = []

        for file in new_files:
            file_id = file["id"]
            file_name = file["name"]

            # Download the file
            local_path = self.download_tcx_file(file_id, file_name)

            if local_path:
                # Mark as processed
                self.processed_files["processed"].append(file_id)
                downloaded_files.append(local_path)

        # Save the updated processed files list
        if downloaded_files:
            self._save_processed_files()

        return downloaded_files

    def get_all_processed_files(self):
        """Get count of all processed files"""
        return len(self.processed_files["processed"])

    def reset_processed_files_after_date(self, date_str):
        """Reset processed status for files modified after given date (YYYY-MM-DD)
        Useful for forcing re-sync of files uploaded on a specific date"""
        from datetime import datetime

        all_files = self.list_tcx_files()
        files_to_reset = []

        for f in all_files:
            mod_time_str = f.get('modifiedTime', '')[:10]
            if mod_time_str >= date_str:  # Files modified on or after date_str
                if f["id"] in self.processed_files["processed"]:
                    self.processed_files["processed"].remove(f["id"])
                    files_to_reset.append(f["name"])

        if files_to_reset:
            self._save_processed_files()
            print(f"✓ Reset {len(files_to_reset)} files for re-sync:")
            for name in files_to_reset:
                print(f"   - {name}")
        else:
            print(f"No files found modified after {date_str}")

        return files_to_reset


if __name__ == "__main__":
    # Test the Google Drive integration
    manager = GoogleDriveManager()
    print(f"Total processed files: {manager.get_all_processed_files()}")

    # List all TCX files
    all_files = manager.list_tcx_files()
    print(f"Total TCX files on Drive: {len(all_files)}")

    # Sync new files
    downloaded = manager.sync_new_files()
    print(f"Downloaded {len(downloaded)} file(s)")
