# =========================================================
# STAGE 1: Build React + Vite Frontend Static Assets
# =========================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# =========================================================
# STAGE 2: Python Backend & Production Service
# =========================================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies needed for PyMuPDF / document parsing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements & install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ ./backend/

# Copy frontend static build assets into backend static folder
COPY --from=frontend-builder /app/frontend/dist ./backend/static

WORKDIR /app/backend

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
