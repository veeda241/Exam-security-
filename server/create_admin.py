import asyncio
import sys
import os
from datetime import datetime

# Add the current directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase_client import get_supabase
from auth.utils import hash_password
from auth.models import UserRole

supabase = get_supabase()

async def create_initial_admin():
    print("Checking for existing admin user in Supabase...")
    
    # Check if admin already exists
    res = supabase.table("users").select("*").eq("username", "admin").execute()
    existing_admin = res.data[0] if res.data else None
    
    if existing_admin:
        print(f"Admin user already exists: {existing_admin['username']}")
        return
        
    print("Creating initial admin user...")
    admin = {
        "username": "admin",
        "email": "admin@examguard.pro",
        "hashed_password": hash_password("admin123"),
        "full_name": "System Administrator",
        "role": UserRole.ADMIN.value,
        "is_active": True,
        "is_verified": True,
        "created_at": datetime.utcnow().isoformat()
    }
    
    try:
        supabase.table("users").insert(admin).execute()
        print("Initial admin user created successfully!")
        print("Username: admin")
        print("Password: admin123")
    except Exception as e:
        print(f"Error creating admin: {e}")

if __name__ == "__main__":
    asyncio.run(create_initial_admin())
