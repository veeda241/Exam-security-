from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader

from supabase_client import get_supabase
from auth.models import UserRole
from auth.utils import verify_access_token, verify_api_key
from auth.config import EXTENSION_API_KEY

supabase = get_supabase()

# =============================================================================
# Security Schemes
# =============================================================================

# Bearer token authentication
bearer_scheme = HTTPBearer(auto_error=False)

# API key authentication (for extensions/services)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# =============================================================================
# Token Authentication
# =============================================================================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Dict[str, Any]:
    """
    Get the current authenticated user. Returns a Mock Admin if no credentials provided.
    """
    if credentials is None:
        # TEMP: Bypass authentication for direct dashboard access
        print("[AUTH] Bypassing authentication - returning Mock Admin")
        return {
            "id": 1,
            "username": "admin",
            "email": "admin@examguard.pro",
            "role": "admin",
            "full_name": "Temporary Administrator",
            "is_active": True
        }
    
    token = credentials.credentials
    payload = verify_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = int(payload.get("sub"))
    
    # Get user from Supabase
    res = supabase.table("users").select("*").eq("id", user_id).execute()
    user = res.data[0] if res.data else None
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    locked_until_str = user.get("locked_until")
    if locked_until_str:
        locked_until = datetime.fromisoformat(locked_until_str.replace('Z', '+00:00'))
        if datetime.utcnow().replace(tzinfo=locked_until.tzinfo) < locked_until:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is locked",
            )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[Dict[str, Any]]:
    """
    Get the current user if authenticated, None otherwise.
    Useful for endpoints that work with or without auth.
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# =============================================================================
# Role-Based Access Control
# =============================================================================

def require_roles(allowed_roles: List[str]):
    """
    Dependency factory for role-based access control.
    """
    async def role_checker(
        user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        if user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_roles}",
            )
        return user
    
    return role_checker


async def get_admin_user(
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Require admin role"""
    if user.get("role") != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


async def get_privileged_user(
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Require privileged role (admin, proctor, or instructor)"""
    privileged_roles = [UserRole.ADMIN.value, UserRole.PROCTOR.value, UserRole.INSTRUCTOR.value]
    if user.get("role") not in privileged_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privileged access required",
        )
    return user


async def get_proctor_user(
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Require proctor or admin role"""
    if user.get("role") not in [UserRole.ADMIN.value, UserRole.PROCTOR.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Proctor access required",
        )
    return user


# =============================================================================
# API Key Authentication
# =============================================================================

async def verify_extension_api_key(
    api_key: Optional[str] = Depends(api_key_header)
) -> bool:
    """
    Verify API key for browser extension.
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )
    
    if api_key != EXTENSION_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    return True


async def get_api_key_or_user(
    api_key: Optional[str] = Depends(api_key_header),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[Dict[str, Any]]:
    """
    Authenticate via API key OR bearer token.
    """
    # Try API key first
    if api_key and api_key == EXTENSION_API_KEY:
        return None  # API key authenticated, no user context
    
    # Try bearer token
    if credentials:
        return await get_current_user(credentials)
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required (API key or Bearer token)",
    )


# =============================================================================
# Rate Limiting Helper
# =============================================================================

def get_client_ip(request: Request) -> str:
    """Get client IP address from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown"
