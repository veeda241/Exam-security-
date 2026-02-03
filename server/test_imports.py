#!/usr/bin/env python3
"""Test all imports to verify the application can load correctly"""

import sys
print("Python version:", sys.version)
print("\n=== Testing imports ===")

try:
    from main import app
    print("✓ main.app imported")
except Exception as e:
    print(f"✗ main.app error: {e}")
    sys.exit(1)

try:
    from database import init_db, get_db
    print("✓ database module imported")
except Exception as e:
    print(f"✗ database error: {e}")
    sys.exit(1)

try:
    from api import sessions, events, uploads, reports
    print("✓ All API modules imported")
except Exception as e:
    print(f"✗ API modules error: {e}")
    sys.exit(1)

try:
    from models.session import ExamSession
    from models.event import Event
    from models.analysis import AnalysisResult
    print("✓ All models imported")
except Exception as e:
    print(f"✗ Models error: {e}")
    sys.exit(1)

try:
    from scoring.calculator import calculate_risk_score
    print("✓ Scoring module imported")
except Exception as e:
    print(f"✗ Scoring error: {e}")
    sys.exit(1)

try:
    from reports.generator import generate_pdf_report
    print("✓ Reports module imported")
except Exception as e:
    print(f"✗ Reports error: {e}")
    sys.exit(1)

print("\n=== All imports successful! ===")
print("✅ Application is ready to run!")
