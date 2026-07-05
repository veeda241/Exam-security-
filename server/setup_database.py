#!/usr/bin/env python3
"""
Apply ExamGuard Pro schema to Supabase PostgreSQL.

Usage (from server/):
  python setup_database.py
  python setup_database.py --seed-admin

Requires PG_HOST / PG_USER / PG_PASSWORD in server/.env (Supabase pooler credentials).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

_server_dir = Path(__file__).resolve().parent
if str(_server_dir) not in sys.path:
    sys.path.insert(0, str(_server_dir))

MIGRATION_FILE = _server_dir / "migrations" / "supabase_schema.sql"


def _connect():
    try:
        import psycopg2
    except ImportError:
        print("Missing psycopg2. Install with: pip install psycopg2-binary")
        sys.exit(1)

    from config import settings

    password = settings.PG_PASSWORD or settings.SUPABASE_DB_PASSWORD
    if not settings.PG_HOST or not password:
        print("Set PG_HOST and PG_PASSWORD (or SUPABASE_DB_PASSWORD) in server/.env")
        sys.exit(1)

    return psycopg2.connect(
        host=settings.PG_HOST,
        port=int(settings.PG_PORT or 5432),
        dbname=settings.PG_DB or "postgres",
        user=settings.PG_USER or "postgres",
        password=password,
        sslmode="require",
    )


def apply_schema() -> None:
    if not MIGRATION_FILE.exists():
        print(f"Migration file not found: {MIGRATION_FILE}")
        sys.exit(1)

    sql = MIGRATION_FILE.read_text(encoding="utf-8")
    print(f"Applying {MIGRATION_FILE.name} ...")

    conn = _connect()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        print("Schema applied successfully.")
    except Exception as exc:
        print(f"Migration failed: {exc}")
        sys.exit(1)
    finally:
        conn.close()


def seed_admin() -> None:
    from supabase_client import get_supabase
    from auth.utils import hash_password
    from auth.models import UserRole

    sb = get_supabase()
    if sb is None:
        print("Supabase client not configured. Set SUPABASE_URL and SUPABASE_KEY in .env")
        sys.exit(1)

    res = sb.table("users").select("id").eq("username", "admin").execute()
    if res.data:
        print("Admin user already exists (username: admin)")
        return

    admin = {
        "username": "admin",
        "email": "admin@examguard.pro",
        "hashed_password": hash_password("admin123"),
        "full_name": "System Administrator",
        "role": UserRole.ADMIN.value,
        "is_active": True,
        "is_verified": True,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    sb.table("users").insert(admin).execute()
    print("Admin user created — username: admin  password: admin123")


def main() -> None:
    parser = argparse.ArgumentParser(description="Setup ExamGuard Pro database on Supabase")
    parser.add_argument("--seed-admin", action="store_true", help="Create default admin user after migration")
    parser.add_argument("--schema-only", action="store_true", help="Only apply SQL schema (skip admin seed)")
    args = parser.parse_args()

    apply_schema()
    if args.seed_admin or not args.schema_only:
        try:
            seed_admin()
        except Exception as exc:
            print(f"Admin seed skipped or failed: {exc}")
            print("Run manually: python create_admin.py")


if __name__ == "__main__":
    main()
