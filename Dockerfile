# syntax=docker/dockerfile:1

# --- Base: lightweight Debian + Python ---
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps needed for Blender headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl xz-utils \
    libglib2.0-0 libx11-6 libxi6 libxxf86vm1 libxfixes3 libxcb1 libxrender1 libsm6 libxext6 libglu1-mesa \
    libxkbcommon0 libxrandr2 libxinerama1 libxcursor1 libx11-xcb1 libegl1 libdbus-1-3 libzstd1 libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Create app dir
WORKDIR /app

# Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app ./app
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# --- Blender: download official build at build-time (can override) ---
# --- Blender: download official build at build-time (can override) ---
ARG BLENDER_TAR_URL=https://download.blender.org/release/Blender4.2/blender-4.2.0-linux-x64.tar.xz
ENV BLENDER_DIR=/opt/blender
RUN set -eux; \
    # do NOT pre-create $BLENDER_DIR; it will be a symlink
    mkdir -p /data; \
    echo "Fetching Blender from $BLENDER_TAR_URL"; \
    curl -L "$BLENDER_TAR_URL" -o /tmp/blender.tar.xz; \
    tar -xJf /tmp/blender.tar.xz -C /opt; \
    rm /tmp/blender.tar.xz; \
    BL_DIR="$(ls -1 /opt | grep -E '^blender-[0-9]')" ; \
    echo "Extracted to /opt/$BL_DIR"; \
    rm -rf "$BLENDER_DIR"; \
    ln -s "/opt/$BL_DIR" "$BLENDER_DIR"; \
    ls -l /opt && ls -l "$BLENDER_DIR"; \
    test -x "$BLENDER_DIR/blender"; \
    "$BLENDER_DIR/blender" -v || true

# Ports & volumes
EXPOSE 8084
VOLUME ["/data"]

ENV BLENDER_BIN=/opt/blender/blender \
    DATA_DIR=/data \
    JOBS_DIR=/data/jobs \
    DB_PATH=/data/state.db \
    UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8084

CMD ["/entrypoint.sh"]