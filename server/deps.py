"""
Shared FastAPI dependencies for V2 API.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import sys
import os

_server_dir = os.path.dirname(os.path.abspath(__file__))
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

from supabase_client import get_supabase
from auth.utils import verify_access_token

bearer_scheme = HTTPBearer(auto_error=False)
supabase = get_supabase()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Dict[str, Any]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    if supabase is None:
        return {
            "id": str(user_id),
            "role": payload.get("role", "admin"),
            "username": payload.get("username"),
            "email": f"{payload.get('username', 'admin')}@examguard.local",
            "full_name": "Dev User",
        }

    try:
        profile_res = supabase.table("profiles").select("*").eq("id", str(user_id)).execute()
        if profile_res.data:
            row = profile_res.data[0]
            return {
                "id": row["id"],
                "role": row.get("role", "student"),
                "full_name": row.get("full_name"),
                "email": row.get("email"),
            }

        user_res = supabase.table("users").select("*").eq("id", int(user_id)).execute()
        if user_res.data:
            user = user_res.data[0]
            return {
                "id": str(user["id"]),
                "role": user.get("role", "student"),
                "full_name": user.get("full_name"),
                "email": user.get("email"),
                "username": user.get("username"),
            }
    except Exception:
        return {
            "id": str(user_id),
            "role": payload.get("role", "admin"),
            "username": payload.get("username"),
            "email": f"{payload.get('username', 'admin')}@examguard.local",
            "full_name": "Dev User",
        }

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[Dict[str, Any]]:
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_roles(*roles: str):
    async def checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {', '.join(roles)}",
            )
        return user

    return checker


get_admin_user = require_roles("admin")
get_proctor_user = require_roles("admin", "proctor")


def get_db():
    return get_supabase()
