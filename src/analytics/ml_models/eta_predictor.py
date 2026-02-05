import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import joblib
import os
import logging
from sqlalchemy import select
from src.backend.models.sql_models import Package
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class ETAPredictor:
    """
    Machine Learning model to predict delivery ETA based on distance and traffic conditions.
    Model: Random Forest Regressor
    """
    
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.is_trained = False
        # Use an absolute path or relative to project root. 
        # Inside docker, app is at /app.
        self.model_path = "src/analytics/ml_models/eta_model.joblib"
        self._load_model()

    def _load_model(self):
        """Attempts to load a pre-trained model from disk."""
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                self.is_trained = True
                logger.info(f"Loaded existing ETA model from {self.model_path}")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
        else:
            logger.info("No pre-trained model found. Model will be trained on first request.")

    def _generate_synthetic_data(self, n_samples=1000):
        """
        Generates synthetic historical delivery data for training.
        Core Logic:
        - Base speed: ~30km/h (2 mins per km)
        - Traffic penalty: 0-20 mins
        - Per package handling: 1-3 mins
        """
        np.random.seed(42)
        
        # Features
        distances = np.random.uniform(0.5, 20.0, n_samples)  # 0.5km to 20km
        traffic_load = np.random.uniform(0.0, 1.0, n_samples) # 0 (clear) to 1 (jam)
        num_packages = np.random.randint(1, 10, n_samples)
        
        # Target (Minutes)
        # Time = (Dist * 2) + (Traffic * 20) + (Pkgs * 2) + Noise
        delays = (distances * 2.0) + (traffic_load * 20.0) + (num_packages * 2.0) + np.random.normal(0, 2, n_samples)
        
        # Ensure no negative times
        delays = np.maximum(delays, 5.0)
        
        X = pd.DataFrame({
            "distance_km": distances,
            "traffic_load": traffic_load,
            # "num_packages": num_packages # Syntehtic had this but DB might not yet. 
            # For compat with DB, let's keep it simple or assume 1 pkg
        })
        y = delays
        
        return X, y

    def train(self):
        """
        Trains the model on synthetic data.
        """
        logger.info("Generating synthetic training data...")
        X, y = self._generate_synthetic_data()
        
        logger.info("Training Random Forest model on synthetic data...")
        self.model.fit(X, y)
        self.is_trained = True
        self._save_model()

    async def train_from_db(self, db: AsyncSession):
        """
        Trains the model using real data from the database.
        """
        logger.info("Fetching training data from database...")
        
        # Query packages that have ML features and are completed
        # We assume 'delivered' status implies updated_at is the delivery time
        query = select(Package).where(
            Package.distance_km.isnot(None),
            Package.status == 'delivered'
        )
        result = await db.execute(query)
        packages = result.scalars().all()
        
        if len(packages) < 10:
            logger.warning(f"Not enough data in DB ({len(packages)} records). Falling back to synthetic.")
            self.train()
            return {"source": "synthetic", "records": len(packages)}

        # Prepare Data
        data_points = []
        for p in packages:
            if not p.created_at or not p.updated_at:
                continue
                
            # Calculate duration in minutes
            duration_seconds = (p.updated_at - p.created_at).total_seconds()
            duration_minutes = duration_seconds / 60.0
            
            # Sanity check values
            if duration_minutes <= 0 or duration_minutes > 600: # Max 10 hours
                continue

            data_points.append({
                "distance_km": p.distance_km,
                "traffic_load": p.traffic_condition,
                "duration_minutes": duration_minutes
            })
            
        if not data_points:
             logger.warning("No valid data points after filtering.")
             return {"source": "none", "records": 0}

        df = pd.DataFrame(data_points)
        X = df[["distance_km", "traffic_load"]]
        y = df["duration_minutes"]
        
        logger.info(f"Training Random Forest model on {len(df)} DB records...")
        self.model.fit(X, y)
        self.is_trained = True
        self._save_model()
        
        score = self.model.score(X, y)
        logger.info(f"Model retrained. R2 Score: {score:.4f}")
        return {"source": "database", "records": len(df), "score": score}

    def _save_model(self):
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(self.model, self.model_path)
            logger.info(f"Model saved to {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")

    def predict(self, distance_km: float, traffic_load: float, num_packages: int) -> float:
        """
        Returns estimated minutes for delivery.
        """
        if not self.is_trained:
            logger.warning("Model not trained, training now...")
            self.train()
            
        # Matches features used in training (X)
        input_data = pd.DataFrame({
            "distance_km": [distance_km],
            "traffic_load": [traffic_load]
        })
        
        prediction = self.model.predict(input_data)[0]
        return max(1.0, prediction) # Ensure no negative/zero predictions

eta_predictor = ETAPredictor()
