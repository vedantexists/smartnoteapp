FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr and creating .pyc
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=7860 \
    DATA_DIR=/data \
    TEMP_DIR=/tmp/smartnote_media

# Install system dependencies including ffmpeg for yt-dlp
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create application user for Hugging Face Spaces (UID 1000)
RUN useradd -m -u 1000 user

# Create directories for persistent storage and temp processing
RUN mkdir -p /data /tmp/smartnote_media /app && \
    chown -R user:user /data /tmp/smartnote_media /app

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .
RUN chown -R user:user /app

# Switch to non-root user
USER user

# Expose default Hugging Face Spaces port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Start FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
