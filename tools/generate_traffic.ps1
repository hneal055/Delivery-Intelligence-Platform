$ErrorActionPreference = "Stop"
$pkgId = 0

# 1. Authenticate
$authUrl = "http://localhost:8000/auth/token"
$confirmUrl = "http://localhost:8000/delivery/confirm"
$username = "driver1"
$password = "driverpassword"

Write-Host "Authenticating as $username..."
$body = @{
    grant_type = "password"
    username = $username
    password = $password
}

try {
    $tokenResponse = Invoke-RestMethod -Uri $authUrl -Method Post -Body $body
    $token = $tokenResponse.access_token
    Write-Host "Authentication successful."
}
catch {
    Write-Error "Authentication failed: $_"
    exit 1
}

$headers = @{
    Authorization = "Bearer $token"
}

# 2. Check dummy file
if (-not (Test-Path "dummy_image.jpg")) {
    Set-Content -Path "dummy_image.jpg" -Value ("A" * 2000)
}

# 3. Generate Traffic loop
Write-Host "Starting traffic generation (Press Ctrl+C to stop)..."
for ($i=1; $i -le 50; $i++) {
    $pkgId++
    $currentPkg = "PKG-$pkgId"
    
    # Random wait to simulate natural traffic and vary the rate
    $sleepTime = Get-Random -Minimum 1 -Maximum 3
    Start-Sleep -Seconds $sleepTime
    
    try {
        # Using -Form (PowerShell Core feature) for multipart/form-data
        $form = @{
            package_id = $currentPkg
            photo = Get-Item -Path "dummy_image.jpg"
        }
        
        $response = Invoke-RestMethod -Uri $confirmUrl -Method Post -Form $form -Headers $headers
        Write-Host "[$i/50] Delivered $currentPkg - Status: $($response.status)"
        
    }
    catch {
        Write-Host "[$i/50] Error delivering $currentPkg`: $_" -ForegroundColor Red
    }
}
Write-Host "Traffic generation complete."
