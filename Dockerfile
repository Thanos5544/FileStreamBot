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

# 🔥 EJS scripts download via separate Python script (no escaping issues)
COPY download_ejs.py /tmp/download_ejs.py
RUN python3 /tmp/download_ejs.py && rm /tmp/download_ejs.py

COPY . .

CMD ["python", "-m", "FileStream"]
