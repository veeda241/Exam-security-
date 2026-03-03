"""
ExamGuard Pro - Authentication Configuration
JWT and security settings
"""

import os
from datetime import timedelta

# =============================================================================
# JWT Configuration
# =============================================================================

# Secret key for JWT signing - MUST be changed in production!
# Generate a secure key with: openssl rand -hex 32
SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY", 
    "examguard-dev-secret-key-change-in-production-2026"
)

# Algorithm for JWT
ALGORITHM = "HS256"

# Token expiration times
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Token types
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"

# =============================================================================
# Password Configuration
# =============================================================================

# Bcrypt settings
BCRYPT_ROUNDS = 12

# Password requirements
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGIT = True
PASSWORD_REQUIRE_SPECIAL = False

# =============================================================================
# User Roles
# =============================================================================

class UserRole:
    """User role constants"""
    ADMIN = "admin"
    PROCTOR = "proctor"
    INSTRUCTOR = "instructor"
    STUDENT = "student"
    
    @classmethod
    def all_roles(cls):
        return [cls.ADMIN, cls.PROCTOR, cls.INSTRUCTOR, cls.STUDENT]
    
    @classmethod
    def privileged_roles(cls):
        """Roles with elevated access"""
        return [cls.ADMIN, cls.PROCTOR, cls.INSTRUCTOR]

# =============================================================================
# API Key Configuration (for service-to-service auth)
# =============================================================================

# API key for extension communication
EXTENSION_API_KEY = os.getenv("EXTENSION_API_KEY", "examguard-extension-key-2026")

# Allowed API key prefixes
API_KEY_PREFIX = "eg_"

# =============================================================================
# Session Configuration
# =============================================================================

# Maximum concurrent sessions per user
MAX_SESSIONS_PER_USER = 3

# Session inactivity timeout (minutes)
SESSION_TIMEOUT_MINUTES = 120

# =============================================================================
# Rate Limiting
# =============================================================================

# Login attempt limits
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15

# API rate limits (requests per minute)
RATE_LIMIT_DEFAULT = 60
RATE_LIMIT_AUTH = 10  # Stricter for auth endpoints
