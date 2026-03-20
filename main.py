import os
import sys

# ExamGuard Pro - App Entry Point Redirect
# This file allows 'uvicorn main:app' to work from the project root.

# Add the 'server' folder to sys.path so that its internal imports 
# (like 'from database import ...') work correctly.
server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server")
if server_path not in sys.path:
    sys.path.insert(0, server_path)

# Now we can safely import the FastAPI app from server/main.py
# Using absolute import through the 'server' package
from server.main import app

# This block allows running with 'python main.py'
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    # Note: Using "server.main:app" string ensures uvicorn can find it if we reload
    uvicorn.run("server.main:app", host="0.0.0.0", port=port, reload=True)
