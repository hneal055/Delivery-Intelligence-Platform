# Create_ProjectStructure.ps1
# Comprehensive folder structure creation

$folders = @(
    # Documentation
    "docs\requirements",
    "docs\architecture", 
    "docs\api",
    "docs\deployment",
    
    # Source Code
    "src\backend\api",
    "src\backend\services",
    "src\backend\models", 
    "src\backend\utils",
    "src\analytics\data_processing",
    "src\analytics\ml_models",
    "src\analytics\geofencing",
    "src\analytics\image_analysis",
    "src\scripts\deployment",
    "src\scripts\data_etl",
    "src\scripts\monitoring",
    "src\scripts\testing",
    "src\scripts\setup",
    
    # Testing
    "tests\unit",
    "tests\integration", 
    "tests\performance",
    "tests\mobile_sim",
    "tests\test_data",
    
    # Data
    "data\raw",
    "data\processed",
    "data\models",
    "data\geofences", 
    "data\images",
    
    # Infrastructure
    "infrastructure\docker",
    "infrastructure\kubernetes",
    "infrastructure\cloudformation",
    "infrastructure\monitoring",
    
    # Tools & Config
    "tools\simulators",
    "tools\data_generators",
    "tools\validators",
    "tools\profilers",
    "config\environments",
    "config\logging",
    "config\feature_flags",
    
    # VS Code
    ".vscode"
)

Write-Host "Creating project structure..." -ForegroundColor Cyan

foreach ($folder in $folders) {
    New-Item -ItemType Directory -Path $folder -Force
    Write-Host "Created: $folder" -ForegroundColor Gray
}

Write-Host "Project structure created successfully!" -ForegroundColor Green
Write-Host "Total folders created: $($folders.Count)" -ForegroundColor Yellow