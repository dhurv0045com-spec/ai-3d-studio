# ========================================================
# AI 3D Studio - Dockerfile for Railway.app deployment
# Includes Blender 4.2 headless + Python 3.11 + all deps
# ========================================================

FROM python:3.11-slim

# Install system dependencies that Blender needs on Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    xz-utils \
    libxi6 \
    libxxf86vm1 \
    libxfixes3 \
    libxrender1 \
    libgl1 \
    libglu1-mesa \
    libsm6 \
    libice6 \
    libx11-6 \
    libxext6 \
    libfreetype6 \
    libfontconfig1 \
    libgomp1 \
    libegl1 \
    libxkbcommon0 \
    libdbus-1-3 \
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

# Expose port
EXPOSE 8080

# Start the Flask server
CMD ["python", "server.py"]