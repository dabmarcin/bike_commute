# Module Testing Guide

This document explains how to test individual modules before running the full dashboard.

## Prerequisites

Activate the virtual environment first:
```powershell
.\venv\Scripts\Activate.ps1
```

## 1. Test Configuration Module

```bash
python -c "from config import HOME, OFFICE, ROUTE_DETECTION_RADIUS; print(f'Home: {HOME}'); print(f'Office: {OFFICE}'); print(f'Radius: {ROUTE_DETECTION_RADIUS}m')"
```

Expected output:
```
Home: {'name': 'Home', 'lat': 60.0689722, 'lon': 18.7577927, 'ele': 17}
Office: {'name': 'Office', 'lat': 60.0467292, 'lon': 18.5843477, 'ele': 17}
Radius: 200m
```

## 2. Test Database Module

```bash
python -c "from database import BikeCommuteDB; db = BikeCommuteDB(); print('✓ Database initialized'); print('Total rides:', len(db.get_all_rides()))"
```

Expected output:
```
✓ Database initialized
Total rides: 0
```

## 3. Test Google Drive Integration

First, make sure `credentials.json` is in the project root.

```bash
python drive_manager.py
```

On first run, it will:
1. Open a browser for OAuth authentication
2. Ask you to authorize access to Google Drive
3. Save token.json for future use
4. Scan the "Health Sync Aktywności" folder

Expected output:
```
Found folder: Health Sync Aktywności (ID: xxxxxxxxx)
Total processed files: 0
Total GPX files on Drive: X
Downloaded X file(s)
```

## 4. Test GPX Analysis

After downloading at least one GPX file from Google Drive, test the analyzer:

```bash
python analyzer.py gpx_files/your_ride.gpx
```

Example output:
```
Route Type: To Work
Date: 2026-05-03T07:30:00
Duration: 1800s (30m)
Distance: 15.42 km
Avg Speed: 30.84 km/h
Avg HR: 165 bpm
Max HR: 178 bpm
Avg Bearing: 45.3°
EF: 0.187
```

## 5. Test Weather Integration

```bash
python -c "from weather import WeatherManager; from datetime import datetime; wm = WeatherManager(); w = wm.get_weather_at_time(datetime.now()); print(f'Temp: {w[\"temp\"]}°C'); print(f'Wind: {w[\"wind_speed\"]} m/s'); print(f'Direction: {w[\"wind_direction\"]}°')"
```

Expected output:
```
Temp: 12.5°C
Wind: 3.2 m/s
Direction: 225°
```

## 6. Full Dashboard

```bash
python main.py
```

Then open your browser to: http://127.0.0.1:8000

## Troubleshooting

### "ModuleNotFoundError: No module named 'nicegui'"
- Make sure venv is activated
- Run: `pip install -r requirements.txt`

### "FileNotFoundError: credentials.json"
- Download credentials from Google Cloud Console
- Save as `credentials.json` in project root

### "Folder 'Health Sync Aktywności' not found"
- Check the exact folder name on your Google Drive
- Update `GOOGLE_DRIVE_FOLDER_NAME` in config.py if different

### "No new GPX files to sync"
- Check that GPX files exist in your Drive folder
- Verify they have `.gpx` extension (case-sensitive)
- Ensure app has access to the folder

### "Error parsing GPX file"
- Verify GPX file is valid and not corrupted
- Check file encoding is UTF-8
- Ensure it has GPS points with timestamps

## Testing Wind Component Calculation

The wind component calculation uses:
1. Your average bearing during the ride (calculated from GPS points)
2. Wind direction from OpenWeatherMap (0-360°)
3. Wind speed in m/s

Example:
- Your ride bearing: 45° (Northeast)
- Wind direction: 225° (Southwest - headwind)
- Wind speed: 5 m/s
- **Wind component: ~3.5 m/s headwind** (slowing you down)

Positive = headwind, Negative = tailwind
