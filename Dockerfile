FROM python:3.11

# FFmpeg + fonts + git + curl
RUN apt-get update && apt-get install -y \
    ffmpeg fonts-dejavu fonts-liberation curl git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Deno (for bgutil PO token server)
RUN curl -fsSL https://deno.land/install.sh | sh
ENV DENO_DIR=/root/.deno
ENV PATH="/root/.deno/bin:${PATH}"

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN pip install --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/refs/heads/master.tar.gz

# bgutil PLUGIN (Python side - yt-dlp ko PO token deta hai)
RUN pip install "https://github.com/Brainicism/bgutil-ytdlp-pot-provider/archive/master.tar.gz#subdirectory=plugin"

# bgutil SERVER (Deno side - PO token generate karta hai)
RUN git clone https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /opt/bgutil && \
    cd /opt/bgutil/server && \
    deno install && \
    deno cache src/main.ts && \
    echo "✅ bgutil server ready!"

# 🔥 EJS SCRIPTS (Node.js ke liye - signature + n-challenge solve karta hai)
COPY download_ejs.py /tmp/download_ejs.py
RUN python3 /tmp/download_ejs.py && rm /tmp/download_ejs.py

COPY . .

CMD ["python", "-m", "FileStream"]
