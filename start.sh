#!/bin/bash
# Start script for Render deployment
set -e

echo "=== Starting ExamGuard Pro ==="
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"

# Set environment variables for Matplotlib and other libraries
export MPLBACKEND=Agg
export MPLCONFIGDIR=/tmp/matplotlib_cache
export HOME=/tmp
export PYTHONPATH=$PYTHONPATH:.

# Ensure directories exist
mkdir -p /tmp/matplotlib_cache
mkdir -p server/uploads/screenshots
mkdir -p server/uploads/webcam

echo "=== Starting Uvicorn ==="
# Using 'main:app' from root which redirects to 'server.main:app'
# This handles path manipulation correctly.
exec uvicorn main:app --host 0.0.0.0 --port $PORT --log-level info
