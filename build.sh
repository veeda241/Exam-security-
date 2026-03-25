#!/usr/bin/env bash
# ExamGuard Pro - Unified Build Script for Render
set -e

echo "=== STARTING UNIFIED BUILD ==="
echo "Node Version: $(node -v)"
echo "Python Version: $(python --version)"
echo "Working Directory: $(pwd)"

# 1. Install Python dependencies
echo "--- Installing Python Dependencies ---"
pip install --upgrade pip
pip install --no-cache-dir -r server/requirements-deploy.txt || pip install --no-cache-dir -r requirements.txt

# Try installing torch CPU-only (skip if it fails on Render free tier)
pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu || echo "WARN: torch install skipped (optional)"

# 2. Pre-download YOLO weights for speed
echo "--- Pre-downloading YOLO weights ---"
mkdir -p server/models/weights
WEIGHTS_PATH="server/models/weights/yolov8n.pt"
if [ ! -f "$WEIGHTS_PATH" ]; then
    curl -L https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt -o "$WEIGHTS_PATH"
fi

# 3. Build New Dashboard
echo "--- Building examguard-pro Dashboard ---"
if [ -d "examguard-pro" ]; then
    cd examguard-pro
    npm install
    npm run build
    cd ..
else
    echo "ERROR: examguard-pro directory not found"
    exit 1
fi

# 4. Copy built assets to server/dist
echo "--- Copying assets to server/dist ---"
mkdir -p server/dist
cp -r examguard-pro/dist/* server/dist/

echo "=== BUILD COMPLETE ==="
ls -la server/dist/
