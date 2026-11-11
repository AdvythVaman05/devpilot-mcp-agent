# Production Dockerfile for DevPilot Backend
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Install system dependencies including git and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application and test configuration
COPY devpilot/ ./devpilot/
COPY pytest.ini ./

# Copy sample repository and initialize isolated git repository
COPY sample_repo/ ./sample_repo/
RUN git -C sample_repo init && \
    git -C sample_repo config user.name "DevPilot Agent" && \
    git -C sample_repo config user.email "agent@devpilot.internal" && \
    git -C sample_repo add . && \
    git -C sample_repo commit -m "feat(auth): initial authentication service"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://127.0.0.1:${PORT:-8000}/api/health || exit 1

CMD ["sh", "-c", "python -m devpilot.main --host 0.0.0.0 --port ${PORT:-8000}"]
