# Multi-stage Dockerfile for DevPilot
# Stage 1: Build React + Vite Frontend
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python Backend with MCP & Sample Repository
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Install system dependencies including git
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY devpilot/ ./devpilot/
COPY pytest.ini ./

# Copy built frontend assets
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy sample repository and initialize git
COPY sample_repo/ ./sample_repo/
RUN git -C sample_repo init && \
    git -C sample_repo config user.name "DevPilot Robot" && \
    git -C sample_repo config user.email "bot@devpilot.internal" && \
    git -C sample_repo add . && \
    git -C sample_repo commit -m "feat(auth): initial authentication service"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["python", "-m", "devpilot.main", "--host", "0.0.0.0"]
