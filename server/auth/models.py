"""
ExamGuard Pro - Auth Models
Data structures for user authentication (Supabase-based)
"""

from datetime import datetime
from typing import Optional
import enum
from pydantic import BaseModel, Field

class UserRole(str, enum.Enum):
    """User roles for access control"""
    ADMIN = "admin"
    PROCTOR = "proctor"
    INSTRUCTOR = "instructor"
    STUDENT = "student"

class User(BaseModel):
    """Schema for user profile (from Supabase)"""
    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.STUDENT
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None
    
    # Helper properties for compatibility with original code
    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN
    
    @property
    def is_privileged(self) -> bool:
        return self.role in [UserRole.ADMIN, UserRole.PROCTOR, UserRole.INSTRUCTOR]

class RefreshToken(BaseModel):
    """Schema for refresh token storage (from Supabase)"""
    id: int
    user_id: str
    token_hash: str
    expires_at: datetime
    revoked: bool = False
    
    @property
    def is_valid(self) -> bool:
        return not self.revoked and datetime.utcnow() < self.expires_at
