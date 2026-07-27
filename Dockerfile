FROM python:3.11-slim

# Install FFmpeg and wget (for thumbnails)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    fonts-dejavu \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (better caching)
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of the files
COPY . .

CMD ["python", "-m", "FileStream"]
