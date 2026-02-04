from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
import os
from typing import Optional

# Setup API Key security schema
# Using a header 'X-DIAD-Token' for the device connection
api_key_header = APIKeyHeader(name="X-DIAD-Token", auto_error=False)

class AuthService:
    """
    Handles authentication for DIAD devices and backend services.
    Crucial for securing device connections.
    """
    
    def __init__(self):
        # In production, load this from secure env vars or secrets manager
        self.msg_api_key = os.getenv("DIAD_API_KEY", "dev-secret-key-123")

    async def validate_device_token(self, api_key_header: str = Security(api_key_header)):
        """
        Dependency for FastAPI routes to validate the device API key.
        """
        if api_key_header == self.msg_api_key:
            return True
        
        # If we had JWT logic (python-jose), it would go here.
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate device credentials"
        )

    def generate_temp_token(self, driver_id: str) -> str:
        """
        Mock method to generate a session token for a driver.
        """
        return f"session-{driver_id}-xyz"

auth_service = AuthService()

async def get_current_device(api_key: str = Security(api_key_header)):
    """
    FastAPI Dependency to enforce auth on routes.
    """
    return await auth_service.validate_device_token(api_key)
