from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from src.analytics.ml_models.eta_predictor import eta_predictor
from src.backend.api.deps import get_current_active_user
from src.backend.models.domain import User

router = APIRouter(prefix="/analytics", tags=["analytics"])

class ETARequest(BaseModel):
    distance_km: float
    traffic_load: float = 0.5  # 0.0 to 1.0 (Low to High)
    num_packages: int = 1

class ETAResponse(BaseModel):
    estimated_minutes: float
    confidence_score: float = 0.95 # Mock for now
    model_version: str = "v1.0-rf"

@router.post("/predict-eta", response_model=ETAResponse)
async def predict_delivery_time(
    request: ETARequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Predicts the estimated time of arrival (ETA) for a delivery segment.
    Uses a Random Forest Regressor trained on historical fleet data.
    """
    if request.distance_km < 0:
        raise HTTPException(status_code=400, detail="Distance cannot be negative")
    
    eta = eta_predictor.predict(
        distance_km=request.distance_km,
        traffic_load=request.traffic_load,
        num_packages=request.num_packages
    )
    
    return {
        "estimated_minutes": eta,
        "confidence_score": 0.88,
        "model_version": "RandomForest-v1"
    }

@router.post("/train-model")
async def train_model(
    current_user: User = Depends(get_current_active_user)
):
    """
    Manually triggers a retraining of the ETA model.
    (Admin only in real world, open for now)
    """
    eta_predictor.train()
    return {"status": "trained", "message": "Model retraining complete"}

