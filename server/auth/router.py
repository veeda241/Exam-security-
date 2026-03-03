"""
ExamGuard Pro - Authentication Router
API endpoints for authentication
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
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
from auth.models import User, UserRole
from auth.service import AuthService
from auth.dependencies import (
    get_current_user,
    get_admin_user,
    get_privileged_user,
    get_client_ip,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# Registration & Login
# =============================================================================

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.
    
    - **email**: Valid email address
    - **username**: Unique username (3-50 characters)
    - **password**: Strong password (min 8 chars, uppercase, lowercase, digit)
    - **full_name**: Optional full name
    """
    service = AuthService(db)
    
    try:
        user = await service.register(user_data)
        
        # Auto-login after registration
        login_data = UserLogin(username=user.username, password=user_data.password)
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
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with username/email and password.
    
    Returns access and refresh tokens.
    """
    service = AuthService(db)
    
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
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    
    Implements token rotation - returns new refresh token.
    """
    service = AuthService(db)
    
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
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """
    Logout and revoke refresh token.
    """
    service = AuthService(db)
    await service.logout(token_data.refresh_token)
    
    return MessageResponse(message="Logged out successfully")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout from all sessions/devices.
    
    Requires authentication.
    """
    service = AuthService(db)
    count = await service.logout_all(current_user.id)
    
    return MessageResponse(message=f"Logged out from {count} sessions")


# =============================================================================
# User Profile
# =============================================================================

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's profile.
    
    Requires authentication.
    """
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's profile.
    
    Requires authentication.
    """
    if update_data.full_name is not None:
        current_user.full_name = update_data.full_name
    
    if update_data.email is not None:
        # Check if email is taken
        service = AuthService(db)
        existing = await service.get_user_by_email(update_data.email)
        if existing and existing.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        current_user.email = update_data.email
        current_user.is_verified = False  # Require re-verification
    
    await db.commit()
    await db.refresh(current_user)
    
    return UserResponse.model_validate(current_user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change current user's password.
    
    Requires current password verification.
    Logs out from all other sessions.
    """
    service = AuthService(db)
    
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
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all users (admin only).
    
    Supports pagination and filtering by role.
    """
    from sqlalchemy import select, func
    from auth.models import User
    
    # Build query
    query = select(User)
    count_query = select(func.count(User.id))
    
    if role:
        try:
            role_enum = UserRole(role)
            query = query.where(User.role == role_enum)
            count_query = count_query.where(User.role == role_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {role}"
            )
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(User.created_at.desc())
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    role_data: UserRoleUpdate,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a user's role (admin only).
    """
    service = AuthService(db)
    
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
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate a user account (admin only).
    """
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    service = AuthService(db)
    
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
    current_user: User = Depends(get_current_user)
):
    """
    Verify if the current token is valid.
    
    Returns success if token is valid.
    """
    return MessageResponse(message="Token is valid", success=True)
