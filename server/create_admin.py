import asyncio
import sys
import os

# Add the current directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import async_session, init_db
from auth.models import User, UserRole
from auth.utils import hash_password
from sqlalchemy import select

async def create_initial_admin():
    print("Checking for existing admin user...")
    await init_db()
    
    async with async_session() as session:
        # Check if admin already exists
        result = await session.execute(select(User).where(User.username == "admin"))
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            print(f"Admin user already exists: {existing_admin.username}")
            return
            
        print("Creating initial admin user...")
        admin = User(
            username="admin",
            email="admin@examguard.pro",
            hashed_password=hash_password("admin123"),
            full_name="System Administrator",
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )
        
        session.add(admin)
        await session.commit()
        print("Initial admin user created successfully!")
        print("Username: admin")
        print("Password: admin123")

if __name__ == "__main__":
    asyncio.run(create_initial_admin())
