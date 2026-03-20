from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request

from supabase_client import get_supabase
from auth.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    TokenRefresh,
    AuthResponse,
    MessageResponse,
    PasswordChange,
    UserUpdate,
    UserRoleUpdate,
    UserListResponse,
)
from auth.models import UserRole
from auth.service import AuthService
from auth.dependencies import (
    get_current_user,
    get_admin_user,
    get_privileged_user,
    get_client_ip,
)

router = APIRouter(tags=["Authentication"])
supabase = get_supabase()

# =============================================================================
# Registration & Login
# =============================================================================

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request
):
    """Register a new user account via Supabase."""
    service = AuthService()
    
    try:
        user = await service.register(user_data)
        
        # Auto-login after registration
        login_data = UserLogin(username=user["username"], password=user_data.password)
        user, tokens = await service.authenticate(
            login_data,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )
        
        return AuthResponse(
            user=UserResponse.model_validate(user),
            tokens=tokens
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    login_data: UserLogin,
    request: Request
):
    """Login with username/email and password via Supabase."""
    service = AuthService()
    
    try:
        user, tokens = await service.authenticate(
            login_data,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )
        
        return AuthResponse(
            user=UserResponse.model_validate(user),
            tokens=tokens
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    request: Request
):
    """Refresh access token using refresh token via Supabase."""
    service = AuthService()
    
    try:
        tokens = await service.refresh_tokens(
            token_data.refresh_token,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )
        return tokens
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    token_data: TokenRefresh
):
    """Logout and revoke refresh token in Supabase."""
    service = AuthService()
    await service.logout(token_data.refresh_token)
    
    return MessageResponse(message="Logged out successfully")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all_sessions(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Logout from all sessions/devices via Supabase."""
    service = AuthService()
    count = await service.logout_all(current_user["id"])
    
    return MessageResponse(message=f"Logged out from {count} sessions")


# =============================================================================
# User Profile
# =============================================================================

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get current user's profile."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    update_data: UserUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update current user's profile in Supabase."""
    updates = {}
    if update_data.full_name is not None:
        updates["full_name"] = update_data.full_name
    
    if update_data.email is not None:
        # Check if email is taken
        service = AuthService()
        existing = await service.get_user_by_email(update_data.email)
        if existing and existing["id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        updates["email"] = update_data.email
        updates["is_verified"] = False
    
    if updates:
        res = supabase.table("users").update(updates).eq("id", current_user["id"]).execute()
        current_user = res.data[0]
    
    return UserResponse.model_validate(current_user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Change current user's password in Supabase."""
    service = AuthService()
    
    try:
        await service.change_password(
            current_user,
            password_data.current_password,
            password_data.new_password
        )
        return MessageResponse(message="Password changed successfully")
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# =============================================================================
# Admin Endpoints
# =============================================================================

@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    role: Optional[str] = None,
    admin: Dict[str, Any] = Depends(get_admin_user)
):
    """List all users via Supabase (admin only)."""
    
    query = supabase.table("users").select("*", count="exact")
    
    if role:
        query = query.eq("role", role)
    
    # Paginate
    start = (page - 1) * page_size
    end = start + page_size - 1
    
    res = query.order("created_at", desc=True).range(start, end).execute()
    users = res.data
    total = res.count
    
    total_pages = (total + page_size - 1) // page_size if total else 0
    
    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=total or 0,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    role_data: UserRoleUpdate,
    admin: Dict[str, Any] = Depends(get_admin_user)
):
    """Update a user's role via Supabase (admin only)."""
    service = AuthService()
    
    try:
        role_enum = UserRole(role_data.role)
        user = await service.update_user_role(user_id, role_enum)
        return UserResponse.model_validate(user)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def deactivate_user(
    user_id: int,
    admin: Dict[str, Any] = Depends(get_admin_user)
):
    """Deactivate a user account via Supabase (admin only)."""
    if user_id == admin["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    service = AuthService()
    
    try:
        await service.deactivate_user(user_id)
        return MessageResponse(message="User deactivated successfully")
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# =============================================================================
# Utility Endpoints
# =============================================================================

@router.get("/verify-token", response_model=MessageResponse)
async def verify_token(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Verify if the current token is valid."""
    return MessageResponse(message="Token is valid", success=True)
