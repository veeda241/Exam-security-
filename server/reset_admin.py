import asyncio
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Add the current directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()
from supabase_client import get_supabase
from auth.utils import hash_password
from auth.models import UserRole

supabase = get_supabase()

async def reset_admin_password():
    print("Resetting admin password via Supabase...")
    
    new_hashed = hash_password("admin123")
    
    # Check if admin already exists
    res = supabase.table("users").select("*").eq("username", "admin").execute()
    existing_admin = res.data[0] if res.data else None
    
    if existing_admin:
        print(f"Updating existing admin: {existing_admin['username']}")
        supabase.table("users").update({"hashed_password": new_hashed}).eq("id", existing_admin["id"]).execute()
        print("Password reset successfully!")
    else:
        print("Creating fresh admin user...")
        admin = {
            "username": "admin",
            "email": "admin@examguard.pro",
            "hashed_password": new_hashed,
            "full_name": "System Administrator",
            "role": UserRole.ADMIN.value,
            "is_active": True,
            "is_verified": True,
            "created_at": datetime.utcnow().isoformat()
        }
        supabase.table("users").insert(admin).execute()
        print("Admin user created!")

if __name__ == "__main__":
    asyncio.run(reset_admin_password())
