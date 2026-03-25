# ============================================
# Stage 1: Build Frontend (Node.js)
# ============================================
FROM node:20-slim AS builder

WORKDIR /build/frontend

# Install dependencies for building
# We copy package files first for caching
COPY examguard-pro/package*.json ./
RUN npm install

# Copy source and build
COPY examguard-pro/ ./
RUN npm run build

# ============================================
# Stage 2: Runtime Environment (Python/FastAPI)
# ============================================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

# Install system dependencies for Computer Vision & OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (CPU-only optimized)
COPY ./server/requirements-deploy.txt .
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements-deploy.txt

# Copy all relevant project files
COPY . /app/

# Copy built frontend from Stage 1
COPY --from=builder /build/frontend/dist /app/server/dist

# Expose the API port
EXPOSE ${PORT}

WORKDIR /app/server

# Run the proctoring server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
