import asyncio
import sys
import os
from sqlalchemy import select, update
from dotenv import load_dotenv

# Add the current directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()
from database import async_session, init_db
from auth.models import User
from auth.utils import hash_password

async def reset_admin_password():
    print("Resetting admin password for Supabase...")
    await init_db()
    
    async with async_session() as session:
        # Update admin user if exists, otherwise create
        result = await session.execute(select(User).where(User.username == "admin"))
        existing_admin = result.scalar_one_or_none()
        
        new_hashed = hash_password("admin123")
        
        if existing_admin:
            print(f"Updating existing admin: {existing_admin.username}")
            existing_admin.hashed_password = new_hashed
            await session.commit()
            print("Password reset successfully!")
        else:
            print("Creating fresh admin user...")
            from auth.models import UserRole
            admin = User(
                username="admin",
                email="admin@examguard.pro",
                hashed_password=new_hashed,
                full_name="System Administrator",
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True
            )
            session.add(admin)
            await session.commit()
            print("Admin user created!")

if __name__ == "__main__":
    asyncio.run(reset_admin_password())
