FROM python:3.11

# FFmpeg + Node.js + fonts
RUN apt-get update && apt-get install -y \
    ffmpeg fonts-dejavu fonts-liberation curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN pip install --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/refs/heads/master.tar.gz

# 🔥 EJS scripts pre-download (yt-dlp CLI khud sahi URLs janta hai)
RUN yt-dlp --remote-components ejs:github --js-runtimes nodejs \
    --simulate "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 2>&1 || true

# Verify cache
RUN echo "=== EJS Cache ===" && \
    find /root/.cache/yt-dlp/ -type f 2>/dev/null || echo "No cache" && \
    ls -laR /root/.cache/yt-dlp/ 2>/dev/null || true

COPY . .

CMD ["python", "-m", "FileStream"]
