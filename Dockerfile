# Multi-stage production container for Alfa-Bank News Analytics Platform
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

# Install security updates
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition
COPY requirements.txt .

# Install dependencies (if any external libraries requested)
RUN pip install --no-cache-dir -r requirements.txt || true

# Copy application source and data
COPY . .

# Expose HTTP port for Alfa-Business
EXPOSE 8080

# Health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/api/clients || exit 1

# Start the enterprise platform
CMD ["python", "src/main.py", "--host", "0.0.0.0", "--port", "8080"]
