$token = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc5MDA5NzI0M30.zxn-V0N5T8arSiaxxDw2FW7vlJkVuDb1Fo20XFk\_KWQ bearer

$headers = @{

&#x20;   Authorization = "  $token"

}



Invoke-RestMethod -Uri "http://localhost:8002/auth/users/me" -Headers $headers



(.venv) PS C:\\Projects\\DELIVERYINTELLIGENCEPLATFORM> $token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc5MDA5NzI0M30.zxn-V0N5T8arSiaxxDw2FW7vlJkVuDb1Fo20XFk\_KWQ"

(.venv) PS C:\\Projects\\DELIVERYINTELLIGENCEPLATFORM> $headers = @{

&#x20;   Authorization = "Bearer $token"

}

(.venv) PS C:\\Projects\\DELIVERYINTELLIGENCEPLATFORM> 

(.venv) PS C:\\Projects\\DELIVERYINTELLIGENCEPLATFORM> Invoke-RestMethod -Uri "http://localhost:8002/auth/users/me" -Headers $headers





###### **ADMIN\_PASSWORD="AdminPassword123!"**

###### **(.venv) PS C:\\Projects\\DELIVERYINTELLIGENCEPLATFORM> $env:DISPATCHER\_PASSWORD="DispatcherPassword123!"**

###### **(.venv) PS C:\\Projects\\DELIVERYINTELLIGENCEPLATFORM> $env:DRIVER\_PASSWORD="DriverPassword123!"**





**(.venv) PS C:\\Projects\\DELIVERYINTELLIGENCEPLATFORM> docker ps**

**CONTAINER ID   IMAGE                     COMMAND                  CREATED             STATUS             PORTS                                         NAMES**

**444044d408c3   delivery\_backend:latest   "uvicorn src.backend…"   55 minutes ago      Up 55 minutes      0.0.0.0:8000->8000/tcp, \[::]:8000->8000/tcp   delivery\_backend**

**0f216362331b   redis:7-alpine            "docker-entrypoint.s…"   About an hour ago   Up About an hour   0.0.0.0:6379->6379/tcp, \[::]:6379->6379/tcp   delivery\_redis**

**cc38430ef618   postgis/postgis:15-3.3    "docker-entrypoint.s…"   About an hour ago   Up About an hour   0.0.0.0:5432->5432/tcp, \[::]:5432->5432/tcp   delivery\_db**





**If everything exploded tomorrow you could recover using:**



**PowerShell**

**git checkout DIP-Stable-Recovery-Baseline-v1**





