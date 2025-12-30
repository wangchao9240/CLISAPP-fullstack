# CLISApp Backend Dockerfile
# Production-ready FastAPI application

FROM python:3.11-slim-bookworm

LABEL maintainer="CLISApp Team"
LABEL description="Climate Information System API Backend"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libspatialindex-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create application user and directories
RUN useradd -m -u 1000 clisapp && \
    mkdir -p /app /app/data /app/tiles && \
    chown -R clisapp:clisapp /app

# Set work directory
WORKDIR /app

# Copy and install Python dependencies first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=clisapp:clisapp app ./app
COPY --chown=clisapp:clisapp data_pipeline ./data_pipeline
COPY --chown=clisapp:clisapp dev_server.py .

# Switch to non-root user
USER clisapp

# Environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
