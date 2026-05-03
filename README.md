# BikeCommute Analytics

A modern analytics dashboard for tracking daily 15km bike commutes, powered by GPS data from Samsung Health, weather integration, and a NiceGUI dashboard.

## Features

- **Google Drive Integration**: Automatically sync GPX files from "Health Sync Aktywności" folder
- **GPS Analysis**: Parse Samsung Health GPX exports with heart rate data
- **Route Detection**: Automatically classify rides as "To Work" or "Return" based on start location
- **Weather Integration**: Track temperature and wind conditions from OpenWeatherMap
- **Wind Component Calculation**: Calculate headwind/tailwind based on bearing and wind direction
- **Performance Metrics**: Track ride duration, distance, speed, heart rate, and efficiency factor
- **Beautiful Dashboard**: Dark-mode NiceGUI interface with interactive Plotly charts
- **PR Notifications**: Get notified when you achieve a new personal record

## Installation

### 1. Clone and Setup

```bash
cd c:\Projects\BikeCommute
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Google Drive API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project called "BikeCommute"
3. Enable **Google Drive API**
4. Create **OAuth 2.0 Desktop Application** credentials
5. Download the JSON file and save as `credentials.json` in the project root

### 3. Configuration

Edit `.env`:
```
OPENWEATHER_API_KEY=your_api_key_here
```

Update `config.py` if your home/office locations differ:
```python
HOME = {"name": "Home", "lat": 60.0689722, "lon": 18.7577927, "ele": 17}
OFFICE = {"name": "Office", "lat": 60.0467292, "lon": 18.5843477, "ele": 17}
ROUTE_DETECTION_RADIUS = 200  # meters
```

## Running the App

```bash
python main.py
```

The dashboard will open at `http://127.0.0.1:8000`

## First Run

1. Click **"Sync with Google Drive"**
2. Browser will open for OAuth authentication
3. Authorize access to your Google Drive
4. Token is saved locally for future runs
5. App downloads and processes all GPX files from "Health Sync Aktywności"

## Project Structure

```
BikeCommute/
├── main.py              # NiceGUI dashboard
├── config.py            # Configuration & constants
├── database.py          # SQLite database management
├── drive_manager.py     # Google Drive integration
├── analyzer.py          # GPS/GPX parsing & analysis
├── weather.py           # OpenWeatherMap integration
├── requirements.txt     # Python dependencies
├── .env                 # API keys (create this)
├── credentials.json     # Google OAuth (download from Google Cloud)
└── .gitignore          # Git ignore rules
```

## Data Structure

### SQLite Database (bikecommute.db)

**rides table:**
- `id` - Primary key
- `drive_file_id` - Google Drive file ID (prevents re-processing)
- `date` - Ride start time (ISO format)
- `duration` - Ride duration in seconds
- `distance` - Distance in kilometers
- `avg_hr` - Average heart rate (bpm)
- `max_hr` - Maximum heart rate (bpm)
- `avg_speed` - Average speed (km/h)
- `temp` - Temperature (°C)
- `wind_speed` - Wind speed (m/s)
- `wind_direction` - Wind direction (degrees 0-360)
- `wind_component` - Headwind/tailwind component (km/h)
  - Positive = headwind (slowing you down)
  - Negative = tailwind (speeding you up)
- `route_type` - "To Work", "Return", or "Other"

## Key Metrics Explained

### Efficiency Factor (EF)
```
EF = Average Speed (km/h) / Average Heart Rate (bpm)
```
Higher EF = better efficiency (faster with lower heart rate)

### Wind Component
- **Headwind** (positive): Wind coming from ahead, slows you down
- **Tailwind** (negative): Wind from behind, speeds you up
- Calculated based on your direction of travel vs wind direction

### Route Detection
- **Start within 200m of HOME** → "To Work"
- **Start within 200m of OFFICE** → "Return"
- **Otherwise** → "Other"

## Files Generated

- `bikecommute.db` - SQLite database with all ride data
- `processed_files.json` - Tracks which GPX files have been processed
- `token.json` - OAuth token for Google Drive (auto-created, never commit)
- `gpx_files/` - Local copies of downloaded GPX files

## Troubleshooting

### "Folder 'Health Sync Aktywności' not found"
- Check that your Google Drive folder name matches exactly
- Make sure Samsung Health export folder is shared properly

### No heart rate data showing
- Verify Samsung Health is exporting HR data in GPX `<extensions>` tags
- Check that Health Sync is syncing with heart rate enabled

### Weather data showing as null
- Verify OpenWeatherMap API key is correct in `.env`
- Check API key has not exceeded rate limits (free tier: 60 calls/minute)

### OAuth authentication fails
- Delete `token.json` and try syncing again
- Ensure `credentials.json` is in the project root
- Verify Google Cloud project has Drive API enabled

## Security Notes

⚠️ **Never commit the following to version control:**
- `credentials.json` - Contains OAuth client secrets
- `token.json` - Contains user authentication tokens
- `.env` - May contain sensitive API keys

These are in `.gitignore` by default.

## Future Enhancements

- Historical weather data (paid OpenWeatherMap API)
- Strava integration
- Export to CSV/Excel
- Performance trends and analytics
- Cadence analysis (if available in GPX)
- Elevation profile visualization
- Comparison with other riders
