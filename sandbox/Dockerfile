FROM python:3.12-slim

# Create non-root user for sandboxed execution
RUN useradd --create-home --shell /bin/bash sandbox

# Copy the runner script
COPY runner.py /runner.py

# Create a working directory with write permissions for sandbox user
RUN mkdir /workspace && chown sandbox:sandbox /workspace

USER sandbox
WORKDIR /workspace

ENTRYPOINT ["python", "/runner.py"]
