import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.join(ROOT, "server")

if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

_main_path = os.path.join(SERVER_DIR, "main.py")
_spec = importlib.util.spec_from_file_location("examguard_server_main", _main_path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
app = _module.app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
