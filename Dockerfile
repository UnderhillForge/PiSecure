# PiSecure Dockerfile for development and testing
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PISECURE_DATA_DIR=/app/data
ENV PISECURE_MOCK_HARDWARE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy source code
COPY . .

# Create data directories
RUN mkdir -p /app/data /var/lib/pisecure

# Set permissions
RUN chmod +x /app/scripts/pisecure.py

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash pisecure && \
    chown -R pisecure:pisecure /app /var/lib/pisecure
USER pisecure

# Expose ports (if needed for future API server)
# EXPOSE 8000

# Default command
CMD ["python", "-m", "pisecure", "--help"]