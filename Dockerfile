FROM python:3.11

# Install FFmpeg and Deno (for YouTube JS runtime)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Deno for YouTube extraction
RUN curl -fsSL https://deno.land/install.sh | sh
ENV PATH="/root/.deno/bin:${PATH}"

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Verify cookies file
RUN ls -la cookies.txt || echo "WARNING: cookies.txt not found"

COPY . .

CMD ["python", "-m", "FileStream"]
