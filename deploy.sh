#!/bin/bash
set -e

# System deps
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv python3-pip ffmpeg nodejs npm

# Node tool for YouTube PO Token
sudo npm install -g youtube-po-token-generator

# Python venv
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -U yt-dlp

echo "✅ Done. Copy .env.example to .env and fill in BOT_TOKEN."
echo "   Then: sudo cp musicbot.service /etc/systemd/system/ && sudo systemctl enable --now musicbot"
