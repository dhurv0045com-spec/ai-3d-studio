FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    xz-utils \
    libxi6 \
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
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN wget -q https://download.blender.org/release/Blender4.2/blender-4.2.0-linux-x64.tar.xz \
    -O /tmp/blender.tar.xz \
    && mkdir -p /app/blender \
    && tar -xf /tmp/blender.tar.xz --strip-components=1 -C /app/blender \
    && rm /tmp/blender.tar.xz \
    && chmod +x /app/blender/blender

ENV BLENDER_PATH=/app/blender/blender

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["python", "server.py"]
```

Press **Ctrl+S**, close Notepad, then run in PowerShell:
```
git add Dockerfile
git commit -m "Remove libxxf86vm1 and fix all packages"
git push