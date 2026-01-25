# PiSecure Docker Image - Validation Only
# For mining, use native installation on Raspberry Pi hardware
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PISECURE_DATA_DIR=/app/data
ENV PISECURE_VALIDATE_ONLY=1
ENV PISECURE_MOCK_HARDWARE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY pisecure ./pisecure
COPY pyproject.toml setup.py ./

# Install PiSecure package
RUN pip install --no-cache-dir -e .

# Create data directories
RUN mkdir -p /app/data /var/lib/pisecure

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash pisecure && \
    chown -R pisecure:pisecure /app /var/lib/pisecure

USER pisecure

# Health check - validate blockchain
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pisecure status || exit 1

# Expose API port
EXPOSE 3142

# Default: run validator
CMD ["pisecure", "validate", "--continuous"]