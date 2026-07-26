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

# 🔥🔥 EJS SCRIPTS DOWNLOAD VIA GITHUB API 🔥🔥🔥
RUN mkdir -p /root/.cache/yt-dlp/ytdlp-ejs && \
    python3 -c "\
import urllib.request, json, os, ssl; \
ctx = ssl.create_default_context(); \
api = 'https://api.github.com/repos/yt-dlp/ejs/releases/latest'; \
req = urllib.request.Request(api, headers={'User-Agent': 'DockerBuild'}); \
data = json.loads(urllib.request.urlopen(req, context=ctx).read()); \
print(f'EJS Release: {data[\"tag_name\"]}'); \
[print(f'Downloading {a[\"name\"]}...') or urllib.request.urlretrieve(a['browser_download_url'], f'/root/.cache/yt-dlp/ytdlp-ejs/{a[\"name\"]}') or print(f'  OK: {os.path.getsize(f\"/root/.cache/yt-dlp/ytdlp-ejs/{a[\"name\"]}\")} bytes') for a in data['assets'] if a['name'].endswith('.js')]" && \
    echo "=== EJS Cache ===" && ls -la /root/.cache/yt-dlp/ytdlp-ejs/ && \
    echo "=== File sizes ===" && wc -c /root/.cache/yt-dlp/ytdlp-ejs/*.js

COPY . .

CMD ["python", "-m", "FileStream"]
