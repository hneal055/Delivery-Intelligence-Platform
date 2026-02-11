from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.analytics.ml_models.eta_predictor import eta_predictor
from src.backend.api.deps import get_current_active_user
from src.backend.models.domain import User
from src.backend.core.database import get_db
from src.backend.services.mapbox import mapbox_service

router = APIRouter(prefix="/analytics", tags=["analytics"])

class ETARequest(BaseModel):
    distance_km: float
    traffic_load: float = 0.5  # 0.0 to 1.0 (Low to High)
    num_packages: int = 1
    origin_lat: Optional[float] = None
    origin_lon: Optional[float] = None
    dest_lat: Optional[float] = None
    dest_lon: Optional[float] = None

class ETAResponse(BaseModel):
    estimated_minutes: float
    confidence_score: float = 0.95
    model_version: str = "v1.0-rf"
    mapbox_minutes: Optional[float] = None
    source: str = "ml"

@router.post("/predict-eta", response_model=ETAResponse)
async def predict_delivery_time(
    request: ETARequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Predicts ETA using ML model. When Mapbox is available and coordinates are provided,
    blends Mapbox travel time (60%) with ML prediction (40%) for higher accuracy.
    """
    if request.distance_km < 0:
        raise HTTPException(status_code=400, detail="Distance cannot be negative")

    ml_eta = eta_predictor.predict(
        distance_km=request.distance_km,
        traffic_load=request.traffic_load,
        num_packages=request.num_packages
    )

    # Try Mapbox for real road-network ETA
    mapbox_minutes = None
    if (request.origin_lat is not None and request.origin_lon is not None
            and request.dest_lat is not None and request.dest_lon is not None):
        directions = await mapbox_service.get_directions(
            origin=(request.origin_lat, request.origin_lon),
            destination=(request.dest_lat, request.dest_lon),
        )
        if directions:
            mapbox_minutes = directions["duration_minutes"]

    if mapbox_minutes is not None:
        # Weighted blend: 60% Mapbox (road-network), 40% ML (historical patterns)
        blended = (mapbox_minutes * 0.6) + (ml_eta * 0.4)
        return ETAResponse(
            estimated_minutes=round(blended, 1),
            confidence_score=0.92,
            model_version="Blended-Mapbox+RF",
            mapbox_minutes=round(mapbox_minutes, 1),
            source="blended",
        )

    return ETAResponse(
        estimated_minutes=ml_eta,
        confidence_score=0.88,
        model_version="RandomForest-v1",
        source="ml",
    )

@router.post("/train-from-db")
async def train_model_from_db(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers retraining of the ETA model using real-world data stored in PostgreSQL.
    """
    if current_user.role != "admin" and current_user.role != "manager":
        raise HTTPException(status_code=403, detail="Only admins or managers can retrain models")

    result = await eta_predictor.train_from_db(db)
    return {"message": "Model training completed", "details": result}

@router.post("/train-synthetic")
async def train_model_synthetic(
    current_user: User = Depends(get_current_active_user)
):
    """
    Triggers retraining of the ETA model using synthetic data.
    """
    eta_predictor.train()
    return {"message": "Model trained on synthetic data"}
