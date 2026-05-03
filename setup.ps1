# BikeCommute Setup Script for Windows PowerShell

Write-Host "🚴 BikeCommute Analytics - Setup" -ForegroundColor Green

# Check if Python is installed
Write-Host "`nChecking Python installation..." -ForegroundColor Yellow
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Python not found. Please install Python 3.8+ from https://python.org" -ForegroundColor Red
    exit 1
}

# Create virtual environment
Write-Host "`nCreating virtual environment..." -ForegroundColor Yellow
python -m venv venv
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to create virtual environment" -ForegroundColor Red
    exit 1
}

# Activate virtual environment
Write-Host "`nActivating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "`nUpgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install requirements
Write-Host "`nInstalling dependencies from requirements.txt..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Verify credentials.json exists
Write-Host "`nVerifying Google credentials..." -ForegroundColor Yellow
if (Test-Path "credentials.json") {
    Write-Host "✓ credentials.json found" -ForegroundColor Green
} else {
    Write-Host "⚠ credentials.json not found" -ForegroundColor Red
    Write-Host "  Download from Google Cloud Console and save as credentials.json" -ForegroundColor Yellow
}

# Verify .env exists
Write-Host "`nVerifying .env configuration..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "✓ .env file found" -ForegroundColor Green
} else {
    Write-Host "⚠ .env file not found" -ForegroundColor Red
    Write-Host "  Create .env with: OPENWEATHER_API_KEY=your_key_here" -ForegroundColor Yellow
}

# Create necessary directories
Write-Host "`nCreating directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "gpx_files" | Out-Null
Write-Host "✓ gpx_files directory ready" -ForegroundColor Green

# Test imports
Write-Host "`nTesting module imports..." -ForegroundColor Yellow
python -c "import config; import database; import analyzer; print('✓ All modules import successfully')" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Module imports successful" -ForegroundColor Green
} else {
    Write-Host "⚠ Some modules failed to import" -ForegroundColor Red
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "✓ Setup complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Ensure credentials.json is in the project root" -ForegroundColor White
Write-Host "2. Update .env with your OpenWeatherMap API key if needed" -ForegroundColor White
Write-Host "3. Run: python main.py" -ForegroundColor White
Write-Host "`nThe dashboard will open at http://127.0.0.1:8000" -ForegroundColor Cyan
