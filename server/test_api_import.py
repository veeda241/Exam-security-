
import sys
import os
sys.path.append(os.getcwd())

print("Attempting to import api module...")
try:
    from api import register_all_routers
    print("SUCCESS: Imported register_all_routers")
except ImportError as e:
    print(f"FAILURE: ImportError: {e}")
except Exception as e:
    print(f"FAILURE: Exception: {e}")

try:
    import api
    print("SUCCESS: Imported api package")
except Exception as e:
    print(f"FAILURE: Imported api package: {e}")
