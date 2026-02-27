"""
Auth middleware — validates Supabase JWT tokens.
Extracts user_id and raw token for downstream use.

Supports both HS256 (legacy) and ES256 (current) Supabase JWTs
by fetching the JWKS public keys from Supabase.
"""

import time
import jwt
import json
import httpx
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer

from app import config

security = HTTPBearer(auto_error=False)

# TTL-based JWKS cache (refresh every hour)
_jwks_cache: dict = {"data": None, "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 3600  # 1 hour


def _get_jwks():
    """Fetch and cache the Supabase JWKS public keys with a 1-hour TTL."""
    if not config.SUPABASE_URL:
        return None

    now = time.time()
    if _jwks_cache["data"] is not None and (now - _jwks_cache["fetched_at"]) < _JWKS_TTL_SECONDS:
        return _jwks_cache["data"]

    url = f"{config.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    try:
        resp = httpx.get(url, headers={"apikey": config.SUPABASE_ANON_KEY}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        _jwks_cache["data"] = data
        _jwks_cache["fetched_at"] = now
        return data
    except Exception as e:
        print(f"[Auth] Failed to fetch JWKS: {e}")
        return _jwks_cache["data"]  # return stale data if available


def _clear_jwks_cache():
    """Clear the JWKS cache so the next call to _get_jwks() fetches fresh keys."""
    _jwks_cache["data"] = None
    _jwks_cache["fetched_at"] = 0.0


def _get_signing_key(token: str):
    """
    Get the correct signing key for the token.
    Tries JWKS first (for ES256), falls back to JWT secret (for HS256).
    """
    # Decode header to check algorithm
    header = jwt.get_unverified_header(token)
    alg = header.get("alg", "HS256")
    kid = header.get("kid")

    if alg == "ES256" and kid:
        jwks_data = _get_jwks()
        if jwks_data and "keys" in jwks_data:
            for key_data in jwks_data["keys"]:
                if key_data.get("kid") == kid:
                    public_key = jwt.algorithms.ECAlgorithm.from_jwk(json.dumps(key_data))
                    return public_key, ["ES256"]

    # Fallback to HS256 with JWT secret
    return config.SUPABASE_JWT_SECRET, ["HS256"]


async def get_current_user(request: Request) -> dict:
    """
    Validate the Authorization header and return the user payload.
    Returns: { "user_id": ..., "email": ..., "role": ..., "token": ... }

    The raw token is included so downstream services can make
    user-scoped Supabase queries (respecting RLS).

    Skip auth if no JWT secret is configured (development mode).
    """
    # If no JWT secret configured, return a dev user (ONLY in debug mode)
    if not config.SUPABASE_JWT_SECRET:
        if config.DEBUG:
            return {
                "user_id": "dev-user",
                "email": "dev@arrival.ai",
                "token": config.SUPABASE_SERVICE_ROLE_KEY,
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Server misconfiguration: JWT secret not set"
            )

    # Extract Bearer token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.replace("Bearer ", "")

    try:
        signing_key, algorithms = _get_signing_key(token)

        payload = jwt.decode(
            token,
            signing_key,
            algorithms=algorithms,
            audience="authenticated",
        )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID")

        return {
            "user_id": user_id,
            "email": payload.get("email", ""),
            "role": payload.get("role", ""),
            "token": token,
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        # Keys may have rotated — clear cache and retry once
        _clear_jwks_cache()
        try:
            signing_key, algorithms = _get_signing_key(token)
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=algorithms,
                audience="authenticated",
            )
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token: no user ID")
            return {
                "user_id": user_id,
                "email": payload.get("email", ""),
                "role": payload.get("role", ""),
                "token": token,
            }
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
