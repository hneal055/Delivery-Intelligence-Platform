from authlib.integrations.starlette_client import OAuth

from src.backend.core.config import settings

oauth = OAuth()

if (
    settings.OIDC_ENABLED
    and settings.OIDC_CLIENT_ID
    and settings.OIDC_CLIENT_SECRET
    and settings.OIDC_TENANT_ID
):
    oauth.register(
        name="microsoft",
        client_id=settings.OIDC_CLIENT_ID,
        client_secret=settings.OIDC_CLIENT_SECRET,
        server_metadata_url=(
            "https://login.microsoftonline.com/"
            f"{settings.OIDC_TENANT_ID}"
            "/v2.0/.well-known/openid-configuration"
        ),
        client_kwargs={
            "scope": "openid profile email"
        },
    )