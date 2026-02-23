# Run this script as Administrator once to allow the iPhone to reach Expo Metro.
# Right-click this file -> "Run with PowerShell" (or open Admin Terminal and run it).

$rules = @(
    @{ Name = "Expo Metro Bundler (8081)";  Port = 8081 },
    @{ Name = "Expo Dev Server (19000)";    Port = 19000 },
    @{ Name = "Expo HMR (19001)";           Port = 19001 }
)

foreach ($rule in $rules) {
    $existing = netsh advfirewall firewall show rule name=$($rule.Name) 2>&1
    if ($existing -match "No rules match") {
        netsh advfirewall firewall add rule `
            name=$($rule.Name) `
            dir=in `
            action=allow `
            protocol=TCP `
            localport=$($rule.Port)
        Write-Host "OPENED  port $($rule.Port)  [$($rule.Name)]" -ForegroundColor Green
    } else {
        Write-Host "ALREADY OPEN  port $($rule.Port)  [$($rule.Name)]" -ForegroundColor Cyan
    }
}

Write-Host ""
Write-Host "Done. You can now use:  npx expo start --lan --clear" -ForegroundColor Yellow
Write-Host "iPhone must be on the same Wi-Fi network as this PC (192.168.12.x)." -ForegroundColor Yellow
pause
