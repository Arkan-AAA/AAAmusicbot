FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg nodejs npm \
    chromium chromium-driver \
    ca-certificates fonts-liberation libnss3 libatk-bridge2.0-0 \
    libx11-6 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 \
    && npm install -g youtube-po-token-generator \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -U yt-dlp

COPY . .

CMD ["python", "bot.py"]
