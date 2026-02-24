"""
Auth middleware — validates Supabase JWT tokens.
Extracts user_id and raw token for downstream use.
"""

import jwt
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer

from app import config

security = HTTPBearer(auto_error=False)


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
        payload = jwt.decode(
            token,
            config.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
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
