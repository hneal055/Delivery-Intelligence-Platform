from typing import Optional
import hmac

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from src.backend.core.config import settings

# Device authentication header
api_key_header = APIKeyHeader(
    name="X-DIAD-Token",
    auto_error=False,
)


class AuthService:
    """
    Handles authentication for DIAD devices and backend services.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.msg_api_key = (
            api_key if api_key is not None else settings.DIAD_API_KEY
        )

    async def validate_device_token(
        self,
        api_key=None,
        api_key_header=None,
    ):
        token = api_key if api_key is not None else api_key_header

        # Fail closed: with no key configured, no device is accepted.
        # compare_digest keeps the check constant-time.
        if (
            self.msg_api_key
            and token
            and hmac.compare_digest(
                token.encode(),
                self.msg_api_key.encode(),
            )
        ):
            return True

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate device credentials",
        )


auth_service = AuthService()


async def get_current_device(
    api_key: Optional[str] = Security(api_key_header),
) -> bool:
    """
    FastAPI dependency enforcing DIAD authentication.
    """

    return await auth_service.validate_device_token(api_key)
