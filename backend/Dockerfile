# CodeTrace AI — Backend Image
#
# Build:
#   docker build -t codetrace-backend -f backend/Dockerfile .
#
# Run (subprocess mode — free cloud hosting):
#   docker run --rm -p 8000:8000 -e EXECUTION_MODE=subprocess codetrace-backend
#
# Run (Docker mode — local dev, needs Docker socket):
#   docker run --rm -p 8000:8000 \
#     -e EXECUTION_MODE=docker \
#     -v /var/run/docker.sock:/var/run/docker.sock \
#     codetrace-backend

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (none needed beyond slim base)
# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/app/ ./app/

# Create a non-root user for running the server
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose the port for documentation.
# The actual port is set via the PORT environment variable.
EXPOSE 8000

# Start Uvicorn. The PORT env var is read by config.py.
# Defaults to 8000 if PORT is not set.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
