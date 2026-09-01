import hashlib
import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings


async def authenticate_client(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Annotated[Settings, Depends(get_settings)] = None,
) -> str:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    for client_id, expected in settings.api_keys.items():
        if hmac.compare_digest(x_api_key, expected):
            return client_id
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def key_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]
