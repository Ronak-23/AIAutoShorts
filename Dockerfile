# ==============================================================================
# AIAutoShorts — Multi-Architecture Production Container (ARM64 / AMD64)
# Compatible with Oracle Cloud Ampere A1 (ARM64) and standard x86_64 VPS
# ==============================================================================
FROM python:3.11-slim

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies: FFmpeg, Git, Curl, and C-compilers for fast pip builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure storage directories exist with proper permissions
RUN mkdir -p data output/videos output/thumbnails output/logs config/bgm_defaults

EXPOSE 8000

# Unified runner: starts FastAPI REST API, React Web Studio, and background scheduler
CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "8000"]
