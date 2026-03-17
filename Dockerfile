# ============================================
# Slim Dockerfile for Railway (< 4 GB)
# ============================================
FROM python:3.11-slim

WORKDIR /app

# Install only essential system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install slim Python dependencies (no PyTorch/TensorFlow)
COPY ./server/requirements-deploy.txt .
RUN pip install --no-cache-dir -r requirements-deploy.txt

# Copy backend code
COPY ./server /app/server

# Copy pre-built React frontend (if available)
COPY ./react-frontend-dist /app/react-frontend-dist

WORKDIR /app/server

EXPOSE 8000

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
