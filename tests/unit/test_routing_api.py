import pytest
from fastapi import FastAPI
from src.backend.api.routes import routing
from httpx import AsyncClient, ASGITransport

app = FastAPI()
app.include_router(routing.router)

@pytest.mark.asyncio
async def test_optimize_route_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "driver_id": "driver-001",
            "current_location": {"lat": 40.7128, "lon": -74.0060}, 
            "stops": [
                {"lat": 40.730610, "lon": -73.935242}, 
                {"lat": 34.0522, "lon": -118.2437},    
                {"lat": 40.7580, "lon": -73.9855}      
            ]
        }
        
        headers = {"X-DIAD-Token": "dev-secret-key-123"}
        
        response = await client.post("/route/optimize", json=payload, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_stops"] == 3
        
        optimized_stops = data["optimized_stops"]
        assert optimized_stops[0]["lat"] == 40.7580 
        assert optimized_stops[2]["lat"] == 34.0522 

@pytest.mark.asyncio
async def test_optimize_route_unauthorized():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "driver_id": "driver-001",
            "current_location": {"lat": 40.7128, "lon": -74.0060},
            "stops": []
        }
        
        response = await client.post("/route/optimize", json=payload)
        assert response.status_code == 403
