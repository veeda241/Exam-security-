"""
ExamGuard Pro - Authentication Service
Business logic for authentication operations
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from auth.models import User, UserRole, RefreshToken
from auth.schemas import UserCreate, UserLogin, UserResponse, Token, AuthResponse
from auth.utils import (
    hash_password,
    verify_password,
    create_tokens,
    verify_refresh_token,
    hash_token,
)
from auth.config import (
    MAX_LOGIN_ATTEMPTS,
    LOGIN_LOCKOUT_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)


class AuthService:
    """Authentication service for user management"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # =========================================================================
    # User Registration
    # =========================================================================
    
    async def register(
        self,
        user_data: UserCreate,
        role: UserRole = UserRole.STUDENT
    ) -> User:
        """
        Register a new user.
        
        Args:
            user_data: User registration data
            role: User role (default: STUDENT)
            
        Returns:
            Created user
            
        Raises:
            ValueError: If email or username already exists
        """
        # Check if email exists
        result = await self.db.execute(
            select(User).where(User.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")
        
        # Check if username exists
        result = await self.db.execute(
            select(User).where(User.username == user_data.username.lower())
        )
        if result.scalar_one_or_none():
            raise ValueError("Username already taken")
        
        # Create user
        user = User(
            email=user_data.email,
            username=user_data.username.lower(),
            hashed_password=hash_password(user_data.password),
            full_name=user_data.full_name,
            role=role,
            is_active=True,
            is_verified=False,  # Requires email verification
            password_changed_at=datetime.utcnow(),
        )
        
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        
        return user
    
    # =========================================================================
    # User Login
    # =========================================================================
    
    async def authenticate(
        self,
        login_data: UserLogin,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[User, Token]:
        """
        Authenticate a user and return tokens.
        
        Args:
            login_data: Login credentials
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Tuple of (user, tokens)
            
        Raises:
            ValueError: If credentials are invalid or account is locked
        """
        # Find user by username or email
        result = await self.db.execute(
            select(User).where(
                or_(
                    User.username == login_data.username.lower(),
                    User.email == login_data.username.lower()
                )
            )
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            raise ValueError("Invalid credentials")
        
        # Check if account is locked
        if user.is_locked:
            minutes_remaining = (user.locked_until - datetime.utcnow()).seconds // 60
            raise ValueError(f"Account is locked. Try again in {minutes_remaining} minutes")
        
        # Check if account is active
        if not user.is_active:
            raise ValueError("Account is disabled")
        
        # Verify password
        if not verify_password(login_data.password, user.hashed_password):
            # Increment failed attempts
            user.failed_login_attempts += 1
            
            if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
                await self.db.commit()
                raise ValueError(f"Account locked due to too many failed attempts. Try again in {LOGIN_LOCKOUT_MINUTES} minutes")
            
            await self.db.commit()
            raise ValueError("Invalid credentials")
        
        # Successful login - reset failed attempts
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        
        # Create tokens
        access_token, refresh_token, expires_in = create_tokens(
            user.id, user.username, user.role.value
        )
        
        # Store refresh token
        token_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.add(token_record)
        
        await self.db.commit()
        
        tokens = Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in,
        )
        
        return user, tokens
    
    # =========================================================================
    # Token Refresh
    # =========================================================================
    
    async def refresh_tokens(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Token:
        """
        Refresh access token using refresh token.
        Implements token rotation - old refresh token is revoked.
        
        Args:
            refresh_token: The refresh token
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            New tokens
            
        Raises:
            ValueError: If refresh token is invalid
        """
        # Verify refresh token
        payload = verify_refresh_token(refresh_token)
        if payload is None:
            raise ValueError("Invalid refresh token")
        
        user_id = int(payload.get("sub"))
        token_hash = hash_token(refresh_token)
        
        # Find token in database
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False,
            )
        )
        token_record = result.scalar_one_or_none()
        
        if token_record is None or not token_record.is_valid:
            raise ValueError("Invalid or expired refresh token")
        
        # Get user
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user is None or not user.is_active:
            raise ValueError("User not found or inactive")
        
        # Revoke old refresh token (token rotation)
        token_record.revoked = True
        token_record.revoked_at = datetime.utcnow()
        
        # Create new tokens
        access_token, new_refresh_token, expires_in = create_tokens(
            user.id, user.username, user.role.value
        )
        
        # Store new refresh token
        new_token_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(new_refresh_token),
            expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.add(new_token_record)
        
        await self.db.commit()
        
        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=expires_in,
        )
    
    # =========================================================================
    # Logout
    # =========================================================================
    
    async def logout(self, refresh_token: str) -> bool:
        """
        Logout user by revoking refresh token.
        
        Args:
            refresh_token: The refresh token to revoke
            
        Returns:
            True if successful
        """
        token_hash = hash_token(refresh_token)
        
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        token_record = result.scalar_one_or_none()
        
        if token_record:
            token_record.revoked = True
            token_record.revoked_at = datetime.utcnow()
            await self.db.commit()
        
        return True
    
    async def logout_all(self, user_id: int) -> int:
        """
        Logout user from all sessions by revoking all refresh tokens.
        
        Args:
            user_id: The user ID
            
        Returns:
            Number of sessions revoked
        """
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False,
            )
        )
        tokens = result.scalars().all()
        
        count = 0
        for token in tokens:
            token.revoked = True
            token.revoked_at = datetime.utcnow()
            count += 1
        
        await self.db.commit()
        return count
    
    # =========================================================================
    # Password Management
    # =========================================================================
    
    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password.
        
        Args:
            user: The user
            current_password: Current password
            new_password: New password
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If current password is incorrect
        """
        if not verify_password(current_password, user.hashed_password):
            raise ValueError("Current password is incorrect")
        
        user.hashed_password = hash_password(new_password)
        user.password_changed_at = datetime.utcnow()
        
        # Revoke all refresh tokens (force re-login)
        await self.logout_all(user.id)
        
        await self.db.commit()
        return True
    
    # =========================================================================
    # User Management
    # =========================================================================
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        result = await self.db.execute(
            select(User).where(User.username == username.lower())
        )
        return result.scalar_one_or_none()
    
    async def update_user_role(self, user_id: int, new_role: UserRole) -> User:
        """Update user role (admin only)"""
        user = await self.get_user_by_id(user_id)
        if user is None:
            raise ValueError("User not found")
        
        user.role = new_role
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def deactivate_user(self, user_id: int) -> User:
        """Deactivate user account"""
        user = await self.get_user_by_id(user_id)
        if user is None:
            raise ValueError("User not found")
        
        user.is_active = False
        await self.logout_all(user_id)
        await self.db.commit()
        await self.db.refresh(user)
        return user
