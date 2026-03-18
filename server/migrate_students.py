import asyncio
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Add current dir to sys.path to import config
sys.path.append(str(Path(__file__).parent))

load_dotenv()
import config

async def migrate_db():
    db_url = config.DATABASE_URL
    print(f"DEBUG: Using DATABASE_URL: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    
    try:
        # Create async engine with pooling-friendly settings
        engine = create_async_engine(
            db_url,
            connect_args={"statement_cache_size": 0} # Required for Supabase pgbouncer transaction mode
        )
        
        async with engine.begin() as conn:
            # Check for missing columns in 'students' table
            # Adding if they don't exist
            print("Checking/Adding missing columns to 'students' table...")
            
            # Using raw SQL to add columns safely if they don't exist
            # Note: PostgreSQL's catch error pattern for IF NOT EXISTS depends on version for ADD COLUMN
            # but usually it's easier to just try/catch if necessary or use info schema
            
            queries = [
                "ALTER TABLE students ADD COLUMN IF NOT EXISTS department VARCHAR;",
                "ALTER TABLE students ADD COLUMN IF NOT EXISTS year VARCHAR;",
                "ALTER TABLE students ADD COLUMN IF NOT EXISTS email VARCHAR;",
                "ALTER TABLE students ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
            ]
            
            for query in queries:
                try:
                    await conn.execute(text(query))
                    print(f"✅ Executed: {query}")
                except Exception as e:
                    print(f"⚠️ Query failed (might already exist): {str(e)}")
            
        print("\nMigration check completed!")
        await engine.dispose()
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(migrate_db())
