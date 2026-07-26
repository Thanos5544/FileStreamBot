FROM python:3.11

# FFmpeg + fonts + git
RUN apt-get update && apt-get install -y \
    ffmpeg fonts-dejavu fonts-liberation curl git \
    && rm -rf /var/lib/apt/lists/*

# Deno install
RUN curl -fsSL https://deno.land/install.sh | sh
ENV DENO_DIR=/root/.deno
ENV PATH="/root/.deno/bin:${PATH}"

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN pip install --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/refs/heads/master.tar.gz

# bgutil PLUGIN (Python side)
RUN pip install "https://github.com/Brainicism/bgutil-ytdlp-pot-provider/archive/master.tar.gz#subdirectory=plugin"

# bgutil SERVER (Deno side)
RUN git clone https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /opt/bgutil && \
    cd /opt/bgutil/server && \
    deno install && \
    deno cache src/main.ts && \
    echo "✅ bgutil server ready!"

COPY . .

CMD ["python", "-m", "FileStream"]
