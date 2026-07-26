FROM python:3.11

# FFmpeg + Node.js + fonts + git
RUN apt-get update && apt-get install -y \
    ffmpeg fonts-dejavu fonts-liberation curl git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Latest yt-dlp
RUN pip install --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/refs/heads/master.tar.gz

# 🔥 bgutil POT provider PLUGIN (yt-dlp ko po_token deta hai)
RUN pip install "https://github.com/Brainicism/bgutil-ytdlp-pot-provider/archive/master.tar.gz#subdirectory=plugin"

# 🔥 bgutil POT provider SERVER (po_token generate karta hai)
RUN git clone https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /opt/bgutil && \
    cd /opt/bgutil/server && \
    npm install && \
    npm run build || echo "⚠️ Server build had warnings"

# Verify
RUN echo "=== bgutil server files ===" && ls -la /opt/bgutil/server/build/ 2>/dev/null || ls -la /opt/bgutil/server/dist/ 2>/dev/null || echo "Checking src..." && ls -la /opt/bgutil/server/src/ 2>/dev/null || true

COPY . .
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
