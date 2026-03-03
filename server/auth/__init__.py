"""
ExamGuard Pro - Authentication Module
JWT-based authentication with role-based access control
"""

from auth.models import User, UserRole, RefreshToken
from auth.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    AuthResponse,
    MessageResponse,
)
from auth.utils import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
)
from auth.dependencies import (
    get_current_user,
    get_current_user_optional,
    get_admin_user,
    get_privileged_user,
    get_proctor_user,
    require_roles,
    verify_extension_api_key,
    get_api_key_or_user,
)
from auth.service import AuthService
from auth.router import router as auth_router


__all__ = [
    # Models
    "User",
    "UserRole",
    "RefreshToken",
    
    # Schemas
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "Token",
    "AuthResponse",
    "MessageResponse",
    
    # Utils
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "verify_access_token",
    "verify_refresh_token",
    
    # Dependencies
    "get_current_user",
    "get_current_user_optional",
    "get_admin_user",
    "get_privileged_user",
    "get_proctor_user",
    "require_roles",
    "verify_extension_api_key",
    "get_api_key_or_user",
    
    # Service
    "AuthService",
    
    # Router
    "auth_router",
]
