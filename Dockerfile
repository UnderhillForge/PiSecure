# PiSecure Docker image — validation / API node (not a Pi miner)
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PISECURE_DATA_DIR=/var/lib/pisecure \
    PISECURE_CONFIG_DIR=/etc/pisecure \
    PISECURE_VALIDATE_ONLY=1 \
    PISECURE_MOCK_HARDWARE=1 \
    PISECURE_API_HOST=0.0.0.0 \
    PISECURE_API_PORT=3142 \
    PISECURE_BOOTSTRAP_URL=https://bootstrap.pisecure.org

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        curl \
        pkg-config \
        libssl-dev \
        libffi-dev \
        libsqlite3-dev \
        libwebsockets-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt pyproject.toml setup.py README.md ./
RUN pip install --no-cache-dir -r requirements.txt

COPY pisecure ./pisecure
COPY cpp ./cpp
COPY config ./config

RUN pip install --no-cache-dir -e . --no-build-isolation || pip install --no-cache-dir -e .

RUN mkdir -p /var/lib/pisecure /etc/pisecure /app/data \
    && useradd --create-home --shell /bin/bash --uid 3142 pisecure \
    && chown -R pisecure:pisecure /app /var/lib/pisecure /etc/pisecure

USER pisecure

EXPOSE 3142 3144 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD pisecure status || exit 1

CMD ["pisecure", "--validate-only", "--mock-hardware", "status"]
