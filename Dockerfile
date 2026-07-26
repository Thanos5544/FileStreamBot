FROM python:3.11

# FFmpeg + fonts + git + unzip
RUN apt-get update && apt-get install -y \
    ffmpeg fonts-dejavu fonts-liberation curl git unzip \
    && rm -rf /var/lib/apt/lists/*

# 🔥 Install Deno (bgutil server Deno pe chalta hai ab)
RUN curl -fsSL https://deno.land/install.sh | sh
ENV DENO_DIR=/root/.deno
ENV PATH="/root/.deno/bin:${PATH}"

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Latest yt-dlp
RUN pip install --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/refs/heads/master.tar.gz

# 🔥 bgutil PLUGIN (Python side - yt-dlp ko PO token deta hai)
RUN pip install "https://github.com/Brainicism/bgutil-ytdlp-pot-provider/archive/master.tar.gz#subdirectory=plugin"

# 🔥 bgutil SERVER (Deno side - PO token generate karta hai)
RUN git clone https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /opt/bgutil && \
    cd /opt/bgutil/server && \
    deno cache src/main.ts && \
    echo "✅ bgutil server cached!"

COPY . .

CMD ["python", "-m", "FileStream"]
