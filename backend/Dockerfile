# MAPORA AI Spatial Mapping Backend Dockerfile
FROM python:3.11-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies for OpenCV, FFmpeg, and PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    ffmpeg \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

# Create storage and model cache directories
RUN mkdir -p /app/storage_data /app/models_cache

EXPOSE 8000

# Default command: FastAPI development / production server with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
