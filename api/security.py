from fastapi import Header, HTTPException

from database.settings import get_settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> str:
    """FastAPI dependency gating protected routes behind a shared API key.

    This is deliberately simple (a single shared secret, not per-user auth/roles) --
    proportionate to a portfolio demo's "basic security" bar, not a production IAM
    system. It replaces the previous state where any client could call the API
    anonymously and freely set an arbitrary `user_id` with no verification at all.
    """
    allowed_keys = get_settings().allowed_api_keys()
    if not allowed_keys:
        raise HTTPException(status_code=500, detail="Server misconfiguration: no API_KEYS configured.")
    if not x_api_key or x_api_key not in allowed_keys:
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key header.")
    return x_api_key
