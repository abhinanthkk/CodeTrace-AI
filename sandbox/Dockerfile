# CodeTrace AI — Sandbox Image
#
# Build from the repository root:
#   docker build -f sandbox/Dockerfile -t codetrace-sandbox .
#
# Security decisions for MVP:
# - Non-root user (sandbox) with minimal permissions
# - No network access configured at container run time (--network none)
# - Read-only filesystem at run time (--read-only) with writable /tmp
# - CPU and memory limits set at container run time
# - Execution timeout enforced by the host, not the container
#
# Docker alone does not create a perfectly secure execution platform.
# For production, consider gVisor (runsc) or Firecracker.

FROM python:3.12-slim

# Create non-root user
RUN useradd --create-home --shell /bin/bash sandbox

# Copy the backend app code (tracing package)
COPY backend/app/ /app/

# Copy the runner script
COPY sandbox/runner.py /runner.py

# Create workspace directory owned by sandbox user
RUN mkdir -p /workspace /tmp/exec && \
    chown -R sandbox:sandbox /workspace /tmp/exec && \
    chmod 755 /workspace /tmp/exec

# Switch to non-root user
USER sandbox

# App code available to Python
ENV PYTHONPATH=/app:$PYTHONPATH

WORKDIR /workspace

ENTRYPOINT ["python", "/runner.py"]
