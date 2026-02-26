"""
Auth middleware — validates Supabase JWT tokens.
Extracts user_id and raw token for downstream use.

Supports both HS256 (legacy) and ES256 (current) Supabase JWTs
by fetching the JWKS public keys from Supabase.
"""

import jwt
import json
import httpx
from functools import lru_cache
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer

from app import config

security = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _get_jwks():
    """Fetch and cache the Supabase JWKS public keys."""
    if not config.SUPABASE_URL:
        return None
    url = f"{config.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    try:
        resp = httpx.get(url, headers={"apikey": config.SUPABASE_ANON_KEY}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[Auth] Failed to fetch JWKS: {e}")
        return None


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
    # If no JWT secret configured, return a dev user
    if not config.SUPABASE_JWT_SECRET:
        return {
            "user_id": "dev-user",
            "email": "dev@arrival.ai",
            "token": config.SUPABASE_SERVICE_ROLE_KEY,
        }

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
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
