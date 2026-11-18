import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

bearer = HTTPBearer(auto_error=False)


def _token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def require_admin(token: str = Depends(_token)) -> str:
    expected = settings.admin_api_token
    if not expected:
        raise HTTPException(status_code=503, detail="Admin API token is not configured")
    if not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="Administrator access required")
    return "admin"


def require_ingest_access(token: str = Depends(_token)) -> str:
    if settings.admin_api_token and secrets.compare_digest(token, settings.admin_api_token):
        return "admin"
    if settings.device_api_token and secrets.compare_digest(token, settings.device_api_token):
        return "device"
    raise HTTPException(status_code=403, detail="Invalid API token")
