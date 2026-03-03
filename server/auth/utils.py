"""
ExamGuard Pro - Authentication Utilities
Password hashing, JWT handling, and security utilities
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple, Any
import hashlib
import secrets

from jose import jwt, JWTError
from passlib.context import CryptContext

from auth.config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    BCRYPT_ROUNDS,
)


# =============================================================================
# Password Hashing
# =============================================================================

# Password context for bcrypt hashing
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=BCRYPT_ROUNDS
)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


# =============================================================================
# JWT Token Handling
# =============================================================================

def create_access_token(
    user_id: int,
    username: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token"""
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    now = datetime.utcnow()
    expire = now + expires_delta
    
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "type": TOKEN_TYPE_ACCESS,
        "exp": expire,
        "iat": now,
    }
    
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    user_id: int,
    username: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT refresh token"""
    if expires_delta is None:
        expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    now = datetime.utcnow()
    expire = now + expires_delta
    
    # Add a unique identifier for token rotation
    jti = secrets.token_hex(16)
    
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "type": TOKEN_TYPE_REFRESH,
        "exp": expire,
        "iat": now,
        "jti": jti,
    }
    
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_tokens(user_id: int, username: str, role: str) -> Tuple[str, str, int]:
    """
    Create both access and refresh tokens.
    Returns: (access_token, refresh_token, expires_in_seconds)
    """
    access_token = create_access_token(user_id, username, role)
    refresh_token = create_refresh_token(user_id, username, role)
    expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    return access_token, refresh_token, expires_in


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.
    Returns the payload if valid, None otherwise.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_access_token(token: str) -> Optional[dict]:
    """Verify an access token and return payload"""
    payload = decode_token(token)
    if payload is None:
        return None
    
    if payload.get("type") != TOKEN_TYPE_ACCESS:
        return None
    
    return payload


def verify_refresh_token(token: str) -> Optional[dict]:
    """Verify a refresh token and return payload"""
    payload = decode_token(token)
    if payload is None:
        return None
    
    if payload.get("type") != TOKEN_TYPE_REFRESH:
        return None
    
    return payload


# =============================================================================
# Token Hashing (for storage)
# =============================================================================

def hash_token(token: str) -> str:
    """Hash a token for secure storage"""
    return hashlib.sha256(token.encode()).hexdigest()


# =============================================================================
# API Key Utilities
# =============================================================================

def generate_api_key() -> str:
    """Generate a secure API key"""
    return f"eg_{secrets.token_urlsafe(32)}"


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """Verify an API key against its hash"""
    return hash_token(api_key) == stored_hash


# =============================================================================
# Security Utilities
# =============================================================================

def generate_verification_token() -> str:
    """Generate a token for email verification"""
    return secrets.token_urlsafe(32)


def generate_password_reset_token() -> str:
    """Generate a token for password reset"""
    return secrets.token_urlsafe(32)


def get_token_expiry(token: str) -> Optional[datetime]:
    """Get the expiry time of a token"""
    payload = decode_token(token)
    if payload and "exp" in payload:
        return datetime.fromtimestamp(payload["exp"])
    return None
