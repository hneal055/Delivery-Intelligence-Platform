@echo off

cd /d C:\Projects\DELIVERYINTELLIGENCEPLATFORM

call .venv\Scripts\activate.bat

python -m src.backend.scripts.role_audit_export

pause