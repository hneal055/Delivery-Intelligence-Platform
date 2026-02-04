# Setup_PythonEnvironment.ps1
# Python virtual environment and dependency setup

Write-Host "Setting up Python development environment..." -ForegroundColor Cyan

# Check if Python is installed
$pythonVersion = python --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

Write-Host "Python version: $pythonVersion" -ForegroundColor Yellow

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Gray
python -m venv venv

if (Test-Path "venv") {
    Write-Host "Virtual environment created successfully!" -ForegroundColor Green
} else {
    Write-Host "ERROR: Failed to create virtual environment" -ForegroundColor Red
    exit 1
}

# Activate the environment
Write-Host "Activating virtual environment..." -ForegroundColor Gray
.\venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

Write-Host "Python environment setup complete!" -ForegroundColor Green
Write-Host "Virtual environment location: $(Get-Location)\venv" -ForegroundColor Yellow