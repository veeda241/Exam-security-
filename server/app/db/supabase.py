from supabase import create_client, Client
from app.core.config import settings
from loguru import logger

_supabase: Client = None

def get_supabase_client() -> Client:
    global _supabase
    if _supabase is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            logger.warning("Supabase credentials not found in settings")
            return None
        _supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase
