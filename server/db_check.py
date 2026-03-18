import os
import sys
import asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Load .env first
load_dotenv()

# Add current dir to sys.path to import config
sys.path.append(str(Path(__file__).parent))

try:
    import config
    
    async def check_db():
        db_url = config.DATABASE_URL
        print(f"DEBUG: Using DATABASE_URL: {db_url.split('@')[-1] if '@' in db_url else db_url}")
        
        try:
            # Create async engine with appropriate settings (handled in database.py usually)
            engine = create_async_engine(db_url)
            
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                if result.scalar() == 1:
                    print("✅ Connection successful!")
                    # Check table count
                    from sqlalchemy import inspect
                    def get_tables(connection):
                        inspector = inspect(connection)
                        return inspector.get_table_names()
                    
                    tables = await conn.run_sync(get_tables)
                    print(f"📊 Tables found: {len(tables)} ({', '.join(tables[:5])}{'...' if len(tables) > 5 else ''})")
                else:
                    print("❌ Connection failed: Unexpected result from SELECT 1")
            
            await engine.dispose()
        except Exception as e:
            print(f"❌ Connection failed: {str(e)}")

    if __name__ == "__main__":
        asyncio.run(check_db())
except Exception as e:
    print(f"General error: {str(e)}")
