from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

from supabase_client import get_supabase
from auth.models import UserRole
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

supabase = get_supabase()

class AuthService:
    """Authentication service for user management via Supabase"""
    
    def __init__(self, db=None):
        # db parameter kept for signature compatibility during transition
        pass
    
    async def register(
        self,
        user_data: UserCreate,
        role: UserRole = UserRole.STUDENT
    ) -> Dict[str, Any]:
        """Register a new user in Supabase."""
        
        # Check if email exists
        res = supabase.table("users").select("id").eq("email", user_data.email).execute()
        if res.data:
            raise ValueError("Email already registered")
        
        # Check if username exists
        res = supabase.table("users").select("id").eq("username", user_data.username.lower()).execute()
        if res.data:
            raise ValueError("Username already taken")
        
        # Create user
        user = {
            "email": user_data.email,
            "username": user_data.username.lower(),
            "hashed_password": hash_password(user_data.password),
            "full_name": user_data.full_name,
            "role": role.value,
            "is_active": True,
            "is_verified": False,
            "failed_login_attempts": 0,
            "password_changed_at": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        res = supabase.table("users").insert(user).execute()
        if not res.data:
            raise ValueError("Failed to create user")
            
        return res.data[0]
    
    async def authenticate(
        self,
        login_data: UserLogin,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[Dict[str, Any], Token]:
        """Authenticate user and return tokens via Supabase."""
        
        # Find user by username or email
        res = supabase.table("users").select("*").or_(f"username.eq.{login_data.username.lower()},email.eq.{login_data.username.lower()}").execute()
        if not res.data:
            raise ValueError("Invalid credentials")
            
        user = res.data[0]
        
        # Check if account is locked
        locked_until_str = user.get("locked_until")
        if locked_until_str:
            locked_until = datetime.fromisoformat(locked_until_str.replace('Z', '+00:00'))
            if datetime.utcnow().replace(tzinfo=locked_until.tzinfo) < locked_until:
                minutes_remaining = (locked_until - datetime.utcnow().replace(tzinfo=locked_until.tzinfo)).seconds // 60
                raise ValueError(f"Account is locked. Try again in {minutes_remaining} minutes")
        
        # Check if account is active
        if not user.get("is_active", True):
            raise ValueError("Account is disabled")
        
        # TEMP: Bypass password verification
        # if not verify_password(login_data.password, user.get("hashed_password")):
        #     attempts = user.get("failed_login_attempts", 0) + 1
        #     update_data = {"failed_login_attempts": attempts}
            
        #     if attempts >= MAX_LOGIN_ATTEMPTS:
        #         lock_time = datetime.utcnow() + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
        #         update_data["locked_until"] = lock_time.isoformat()
        #         supabase.table("users").update(update_data).eq("id", user["id"]).execute()
        #         raise ValueError(f"Account locked due to too many failed attempts. Try again in {LOGIN_LOCKOUT_MINUTES} minutes")
            
        #     supabase.table("users").update(update_data).eq("id", user["id"]).execute()
        #     raise ValueError("Invalid credentials")
        
        # Successful login
        update_data = {
            "failed_login_attempts": 0,
            "locked_until": None,
            "last_login": datetime.utcnow().isoformat()
        }
        supabase.table("users").update(update_data).eq("id", user["id"]).execute()
        
        # Create tokens
        access_token, refresh_token, expires_in = create_tokens(
            user["id"], user["username"], user["role"]
        )
        
        # Store refresh token
        token_record = {
            "user_id": user["id"],
            "token_hash": hash_token(refresh_token),
            "expires_at": (datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).isoformat(),
            "user_agent": user_agent,
            "ip_address": ip_address,
            "created_at": datetime.utcnow().isoformat(),
            "revoked": False
        }
        supabase.table("refresh_tokens").insert(token_record).execute()
        
        tokens = Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in,
        )
        
        return user, tokens
    
    async def refresh_tokens(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Token:
        """Refresh tokens using rotation via Supabase."""
        
        payload = verify_refresh_token(refresh_token)
        if payload is None:
            raise ValueError("Invalid refresh token")
        
        user_id = int(payload.get("sub"))
        token_hash = hash_token(refresh_token)
        
        # Find token in Supabase
        res = supabase.table("refresh_tokens").select("*").eq("token_hash", token_hash).eq("user_id", user_id).eq("revoked", False).execute()
        if not res.data:
            raise ValueError("Invalid or expired refresh token")
            
        token_record = res.data[0]
        expires_at = datetime.fromisoformat(token_record["expires_at"].replace('Z', '+00:00'))
        if datetime.utcnow().replace(tzinfo=expires_at.tzinfo) >= expires_at:
            raise ValueError("Refresh token expired")
        
        # Get user
        res = supabase.table("users").select("*").eq("id", user_id).execute()
        if not res.data or not res.data[0].get("is_active", True):
            raise ValueError("User not found or inactive")
        
        user = res.data[0]
        
        # Revoke old token
        supabase.table("refresh_tokens").update({
            "revoked": True,
            "revoked_at": datetime.utcnow().isoformat()
        }).eq("id", token_record["id"]).execute()
        
        # Create new tokens
        access_token, new_refresh_token, expires_in = create_tokens(
            user["id"], user["username"], user["role"]
        )
        
        # Store new refresh token
        new_record = {
            "user_id": user["id"],
            "token_hash": hash_token(new_refresh_token),
            "expires_at": (datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).isoformat(),
            "user_agent": user_agent,
            "ip_address": ip_address,
            "created_at": datetime.utcnow().isoformat(),
            "revoked": False
        }
        supabase.table("refresh_tokens").insert(new_record).execute()
        
        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=expires_in,
        )
    
    async def logout(self, refresh_token: str) -> bool:
        """Revoke a refresh token in Supabase."""
        token_hash = hash_token(refresh_token)
        supabase.table("refresh_tokens").update({
            "revoked": True,
            "revoked_at": datetime.utcnow().isoformat()
        }).eq("token_hash", token_hash).execute()
        return True
    
    async def logout_all(self, user_id: int) -> int:
        """Revoke all active refresh tokens for a user in Supabase."""
        res = supabase.table("refresh_tokens").update({
            "revoked": True,
            "revoked_at": datetime.utcnow().isoformat()
        }).eq("user_id", user_id).eq("revoked", False).execute()
        return len(res.data) if res.data else 0
    
    async def change_password(
        self,
        user: Dict[str, Any],
        current_password: str,
        new_password: str
    ) -> bool:
        """Change password and revoke all tokens in Supabase."""
        if not verify_password(current_password, user.get("hashed_password")):
            raise ValueError("Current password is incorrect")
        
        supabase.table("users").update({
            "hashed_password": hash_password(new_password),
            "password_changed_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", user["id"]).execute()
        
        await self.logout_all(user["id"])
        return True
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        res = supabase.table("users").select("*").eq("id", user_id).execute()
        return res.data[0] if res.data else None
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        res = supabase.table("users").select("*").eq("email", email).execute()
        return res.data[0] if res.data else None
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        res = supabase.table("users").select("*").eq("username", username.lower()).execute()
        return res.data[0] if res.data else None
    
    async def update_user_role(self, user_id: int, new_role: UserRole) -> Dict[str, Any]:
        res = supabase.table("users").update({"role": new_role.value, "updated_at": datetime.utcnow().isoformat()}).eq("id", user_id).execute()
        if not res.data:
            raise ValueError("User not found")
        return res.data[0]
    
    async def deactivate_user(self, user_id: int) -> Dict[str, Any]:
        res = supabase.table("users").update({"is_active": False, "updated_at": datetime.utcnow().isoformat()}).eq("id", user_id).execute()
        if not res.data:
            raise ValueError("User not found")
        await self.logout_all(user_id)
        return res.data[0]
