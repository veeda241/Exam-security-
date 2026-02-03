import sys
import os

print("--- Dependency Check ---")
print(f"Python Version: {sys.version}")

try:
    import sqlite3
    print(f"[OK] sqlite3: {sqlite3.version}")
except Exception as e:
    print(f"[ERROR] sqlite3: {e}")

try:
    import fastapi
    print(f"[OK] fastapi: {fastapi.__version__}")
except Exception as e:
    print(f"[ERROR] fastapi: {e}")

try:
    import sqlalchemy
    print(f"[OK] sqlalchemy: {sqlalchemy.__version__}")
except Exception as e:
    print(f"[ERROR] sqlalchemy: {e}")

try:
    import aiosqlite
    print(f"[OK] aiosqlite: {aiosqlite.__version__}")
except Exception as e:
    print(f"[ERROR] aiosqlite: {e}")

try:
    import pydantic
    print(f"[OK] pydantic: {pydantic.__version__}")
except Exception as e:
    print(f"[ERROR] pydantic: {e}")

print("--- End Check ---")
