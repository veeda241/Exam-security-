# ============================================
# Stage 1: Build React Frontend
# ============================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/react-frontend

COPY ./react-frontend/package.json ./react-frontend/package-lock.json* ./
RUN npm install

COPY ./react-frontend/ ./
RUN npm run build

# ============================================
# Stage 2: Python Backend + Serve React Build
# ============================================
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY ./server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY ./server /app/server

# Copy React build output from Stage 1
COPY --from=frontend-builder /app/react-frontend/dist /app/react-frontend-dist

WORKDIR /app/server

# Railway injects $PORT at runtime
EXPOSE 8000

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
