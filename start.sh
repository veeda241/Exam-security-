#!/bin/bash
# Start script for Render deployment
set -e

echo "=== Starting ExamGuard Pro ==="
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo "Contents: $(ls -la)"
echo "Server directory: $(ls -la server/)"

export PYTHONPATH=server
echo "PYTHONPATH set to: $PYTHONPATH"

echo "=== Starting Uvicorn ==="
exec uvicorn server.main:app --host 0.0.0.0 --port $PORT --log-level info
