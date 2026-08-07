from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: str | None = Security(api_key_header)) -> str:
    if not settings.api_key_set:
        return ""
    if key is None or key not in settings.api_key_set:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return key