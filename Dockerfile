FROM python:3.11

# FFmpeg + Node.js + fonts
RUN apt-get update && apt-get install -y \
    ffmpeg fonts-dejavu fonts-liberation curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Latest yt-dlp
RUN pip install --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/refs/heads/master.tar.gz

# 🔥🔥 EJS SOLVER PRE-DOWNLOAD (Build time pe, runtime pe nahi) 🔥🔥
# Ye GitHub se JS scripts download karke /root/.cache/yt-dlp/ytdlp-ejs/ me save karta hai
RUN mkdir -p /root/.cache/yt-dlp/ytdlp-ejs && \
    curl -fsSL -o /root/.cache/yt-dlp/ytdlp-ejs/ejs.sandbox.bundle.js \
        https://github.com/yt-dlp/ejs/releases/latest/download/ejs.sandbox.bundle.js && \
    curl -fsSL -o /root/.cache/yt-dlp/ytdlp-ejs/ejs.wasm.bundle.js \
        https://github.com/yt-dlp/ejs/releases/latest/download/ejs.wasm.bundle.js && \
    echo "✅ EJS scripts downloaded:" && ls -la /root/.cache/yt-dlp/ytdlp-ejs/

COPY . .

CMD ["python", "-m", "FileStream"]
