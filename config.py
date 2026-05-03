"""
Configuration and constants for BikeCommute Analytics
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Google Drive
GOOGLE_DRIVE_FOLDER_NAME = "Health Sync Aktywności"
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

# Location coordinates (latitude, longitude, elevation in meters)
HOME = {
    "name": "Home",
    "lat": 60.0689722,
    "lon": 18.7577927,
    "ele": 17,
}

OFFICE = {
    "name": "Office",
    "lat": 60.0467292,
    "lon": 18.5843477,
    "ele": 17,
}

# Route detection radius in meters
ROUTE_DETECTION_RADIUS = 200

# Weather API
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# Database
DATABASE_FILE = "bikecommute.db"

# File management
TCX_DOWNLOAD_DIR = "tcx_files"
PROCESSED_FILES_DB = "processed_files.json"

# UI Settings
DARK_MODE = True
APP_TITLE = "BikeCommute Analytics"
