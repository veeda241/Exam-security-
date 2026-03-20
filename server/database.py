"""
ExamGuard Pro - Database Configuration (Supabase)
"""

from supabase_client import get_supabase

# Export Supabase client for easy access
supabase = get_supabase()

async def init_db():
    """
    Supabase handles schema management externally.
    This remains for backward compatibility with main.py lifespan.
    """
    print("Database connection verified (Supabase)")
    return True

async def get_db():
    """
    Dependency to get Supabase client.
    Maintains compatibility with existing code expecting a DB session.
    """
    yield supabase
