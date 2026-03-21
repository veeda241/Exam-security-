#!/usr/bin/env bash
# ExamGuard Pro - Unified Build Script for Render
set -e

echo "=== STARTING UNIFIED BUILD ==="
echo "Python Version: $(python -V)"
echo "Node Version: $(node -v)"
echo "Working Directory: $(pwd)"

# 1. Install Backend Dependencies
echo "--- Installing Python dependencies ---"
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi
if [ -f "server/requirements.txt" ]; then
    pip install -r server/requirements.txt
fi

# 2. Build Frontend
echo "--- Building React Frontend ---"
cd react-frontend
npm install
npm run build
cd ..

# 3. Aggregating Files
echo "--- Preparing Distribution ---"
mkdir -p server/dist
cp -rv react-frontend/dist/* server/dist/

echo "=== BUILD COMPLETE ==="
ls -la server/dist/
