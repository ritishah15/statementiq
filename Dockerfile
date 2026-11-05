# Multi-stage production container for StatementIQ Backend
FROM python:3.11-slim

# Install system dependencies: Tesseract OCR, OpenCV dependencies, libGL
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libtesseract-dev \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python requirements
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application source
COPY backend /app/backend

ENV PYTHONPATH=/app/backend
ENV PORT=8000

EXPOSE 8000

# Start Uvicorn production server
CMD ["python", "backend/run.py"]
