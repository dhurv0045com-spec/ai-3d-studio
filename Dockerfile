# ============================================================
# AI 3D Studio - Dockerfile for Railway.app deployment
# Includes Blender 4.2 headless + Python 3.11 + all deps
# ============================================================

FROM python:3.11-slim

# Install system dependencies that Blender needs on Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    xz-utils \
    libxi6 \
    libxxf86vm1 \
    libxfixes3 \
    libxrender1 \
    libgl1-mesa-glx \
    libglu1-mesa \
    libsm6 \
    libice6 \
    libx11-6 \
    libxext6 \
    libfreetype6 \
    libfontconfig1 \
    libgomp1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Download and install Blender 4.2 portable Linux
RUN wget -q \
    https://download.blender.org/release/Blender4.2/blender-4.2.0-linux-x64.tar.xz \
    -O /tmp/blender.tar.xz \
    && mkdir -p /app/blender \
    && tar -xf /tmp/blender.tar.xz \
       --strip-components=1 \
       -C /app/blender \
    && rm /tmp/blender.tar.xz \
    && chmod +x /app/blender/blender \
    && echo "Blender installed: $(/app/blender/blender --version | head -1)"

# Set Blender path environment variable
ENV BLENDER_PATH=/app/blender/blender

# Copy requirements first (Docker layer cache - faster rebuilds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Create all required directories
RUN mkdir -p \
    models/cache \
    models/presets \
    models/scripts \
    logs \
    static \
    storage/users/user/default \
    storage/users/user/vehicles \
    storage/users/user/creatures \
    storage/users/user/buildings \
    storage/users/user/misc

# Create required empty JSON files if they don't exist
RUN [ -f history.json ]  || echo "[]"  > history.json
RUN [ -f folders.json ]  || echo '["default","vehicles","creatures","buildings","misc"]' > folders.json
RUN [ -f state.json ]    || echo '{"status":"idle","progress":0,"log":[]}' > state.json

# Railway sets PORT env var automatically
EXPOSE 5000

# Start the server
CMD ["python", "server.py"]
