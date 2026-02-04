from fastapi import FastAPI, Depends
from fastapi.responses import RedirectResponse
from src.backend.services.auth import get_current_device
from src.backend.services.notifications import notification_service

app = FastAPI(title="Delivery Intelligence Platform")

@app.get("/")
async def root():
    return RedirectResponse(url="/docs")

@app.get("/health")
async def health_check():
    return {"status": "online"}

@app.post("/secure-ping", dependencies=[Depends(get_current_device)])
async def secure_ping():
    return {"msg": "Device Authenticated"}
