$ErrorActionPreference = "Stop"

# 1. Authenticate
$authUrl = "http://localhost:8000/auth/token"
$predictUrl = "http://localhost:8000/analytics/predict-eta"
$username = "driver1"
$password = "driverpassword"

Write-Host "Authenticating..."
$body = @{
    grant_type = "password"
    username = $username
    password = $password
}
try {
    $tokenResponse = Invoke-RestMethod -Uri $authUrl -Method Post -Body $body
    $token = $tokenResponse.access_token
} catch {
    Write-Error "Auth failed: $_"
    exit 1
}

$headers = @{
    Authorization = "Bearer $token"
    "Content-Type" = "application/json"
}

# 2. Test Prediction
Write-Host "Testing ETA Prediction..."
$payload = @{
    distance_km = 10.5
    traffic_load = 0.8
    num_packages = 5
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri $predictUrl -Method Post -Body $payload -Headers $headers
    Write-Host "Response received:"
    $response | Format-List
} catch {
    Write-Error "Prediction failed: $_"
}
