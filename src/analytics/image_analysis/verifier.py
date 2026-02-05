from pydantic import BaseModel
from typing import List, Optional
import random

class ImageVerificationResult(BaseModel):
    is_valid: bool
    confidence_score: float
    detected_objects: List[str] = []
    issues: List[str] = []

class ImageVerifier:
    """
    Stub service for analyzing proof-of-delivery photos.
    Implementation of Requirement 1.2.3 (Phase 2.3)
    In production, this would wrap a TensorFlow/PyTorch model.
    """

    def verify_delivery_photo(self, image_data: bytes) -> ImageVerificationResult:
        """
        Analyzes the uploaded image bytes.
        Mock Logic:
        - Rejects small files (< 1KB) as empty/corrupt.
        - Returns a mocked confidence score.
        """
        
        # 1. Basic Validation (Mocking a "Blurry" or "Corrupt" check)
        if len(image_data) < 1024:
            return ImageVerificationResult(
                is_valid=False,
                confidence_score=0.0,
                issues=["Image data too small or corrupted (blur check failed)"]
            )

        # 2. Mock ML Inference
        # Simulation: We use the length to create a pseudo-random but deterministic score
        # In real life, we would load model.predict(image_data)
        
        mock_score = 0.95 # High confidence for demo purposes
        
        detected = ["package_box"]
        # Simulate detecting a doorstep if the file is "large" enough
        if len(image_data) > 5000:
            detected.append("doorstep")
            
        return ImageVerificationResult(
            is_valid=True,
            confidence_score=mock_score,
            detected_objects=detected,
            issues=[]
        )

    def verify_proof_of_delivery(self, image_data: bytes) -> tuple[bool, str]:
        """
        Legacy/Wrapper method for compatibility with delivery route.
        Returns a tuple (is_valid, reason).
        """
        result = self.verify_delivery_photo(image_data)
        if result.is_valid:
            return True, "Valid"
        else:
            return False, "; ".join(result.issues) if result.issues else "Unknown verification failure"

# Singleton instance
image_verifier = ImageVerifier()
