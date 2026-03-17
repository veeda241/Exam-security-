#!/usr/bin/env bash
# Render build script for ExamGuard Pro
set -e

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install system dependencies for ML (OpenCV, Tesseract)
apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

echo "Build complete"
