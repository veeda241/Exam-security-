#!/usr/bin/env bash
# Render build script for ExamGuard Pro
set -e

echo "=== Starting ExamGuard Pro Build ==="

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install system dependencies for ML (OpenCV, Tesseract)
echo "Installing system dependencies..."
apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Build React frontend
echo "Building React frontend..."
cd ../react-frontend
npm install
npm run build
cd ..

# Copy frontend build to server directory for monolithic deployment
echo "Copying frontend build to server/dist..."
mkdir -p server/dist
cp -r react-frontend/dist/* server/dist/

echo "=== Build Complete ==="
echo "Frontend files in server/dist:"
ls -la server/dist/
