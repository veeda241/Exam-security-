"""
ExamGuard Pro - Supabase Client
Direct connection to Supabase using supabase-py
"""

import os
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

# Initialize Supabase client
# Ensure SUPABASE_URL and SUPABASE_KEY are provided in environment
if not SUPABASE_URL or not SUPABASE_KEY:
    print("[WARN] Supabase credentials missing from environment!")
    supabase: Client = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("[INFO] Supabase client initialized successfully")

def get_supabase():
    """Get initialized Supabase client"""
    return supabase
