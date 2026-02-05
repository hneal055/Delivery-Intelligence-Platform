import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import joblib
import os
import logging

logger = logging.getLogger(__name__)

class ETAPredictor:
    """
    Machine Learning model to predict delivery ETA based on distance and traffic conditions.
    Model: Random Forest Regressor
    """
    
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.is_trained = False
        self.model_path = "src/analytics/ml_models/eta_model.joblib"

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
            "num_packages": num_packages
        })
        y = delays
        
        return X, y

    def train(self):
        """
        Trains the model on synthetic data.
        """
        logger.info("Generating synthetic training data...")
        X, y = self._generate_synthetic_data()
        
        logger.info("Training Random Forest model...")
        self.model.fit(X, y)
        self.is_trained = True
        
        # Save model (simulated persistence)
        # joblib.dump(self.model, self.model_path)
        logger.info(f"Model trained. Score: {self.model.score(X, y):.4f}")

    def predict(self, distance_km: float, traffic_load: float, num_packages: int) -> float:
        """
        Returns estimated minutes for delivery.
        """
        if not self.is_trained:
            logger.warning("Model not trained, training now...")
            self.train()
            
        input_data = pd.DataFrame({
            "distance_km": [distance_km],
            "traffic_load": [traffic_load],
            "num_packages": [num_packages]
        })
        
        prediction = self.model.predict(input_data)[0]
        return round(prediction, 1)

# Singleton instance
eta_predictor = ETAPredictor()

