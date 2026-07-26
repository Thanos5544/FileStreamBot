FROM python:3.11

# Install FFmpeg + Node.js (n-challenge solver) + fonts
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fonts-dejavu \
    fonts-liberation \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "FileStream"]
