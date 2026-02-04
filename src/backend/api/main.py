from fastapi import FastAPI, Depends
from fastapi.responses import RedirectResponse
from src.backend.services.auth import get_current_device
from src.backend.api.routes import delivery
from src.backend.api.routes import routing

app = FastAPI(title="Delivery Intelligence Platform")

# Register routers
app.include_router(delivery.router)
app.include_router(routing.router)

@app.get("/")
async def root():
    return RedirectResponse(url="/docs")

@app.get("/health")
async def health_check():
    return {"status": "online"}
