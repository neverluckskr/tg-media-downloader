# SoundCloud Telegram Bot

Telegram bot for downloading SoundCloud tracks using aiogram + yt-dlp.

## Project Structure

```
soundcloud-bot/
├── bot.py                 # Entry point
├── app/
│   ├── config.py          # Environment configuration
│   ├── handlers/
│   │   ├── common.py      # /start, /help commands
│   │   └── soundcloud.py  # SoundCloud link handler
│   └── services/
│       └── downloader.py  # yt-dlp async wrapper
├── requirements.txt
├── .env.example
└── .gitignore
```

## Local Setup

```bash
# Clone and enter directory
cd soundcloud-bot

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Add your BOT_TOKEN

# Run bot
python bot.py
```

## VPS Deployment (Ubuntu)

### 1. Install System Dependencies

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv ffmpeg -y
```

### 2. Create Bot User (optional, recommended)

```bash
sudo useradd -m -s /bin/bash botuser
sudo su - botuser
```

### 3. Deploy Code

```bash
cd ~
git clone <your-repo-url> soundcloud-bot
cd soundcloud-bot
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env  # Set BOT_TOKEN
```

### 4. Create Systemd Service

```bash
sudo nano /etc/systemd/system/soundcloud-bot.service
```

Content:
```ini
[Unit]
Description=SoundCloud Telegram Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/soundcloud-bot
ExecStart=/home/botuser/soundcloud-bot/.venv/bin/python bot.py
Restart=always
RestartSec=10
EnvironmentFile=/home/botuser/soundcloud-bot/.env

[Install]
WantedBy=multi-user.target
```

### 5. Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable soundcloud-bot
sudo systemctl start soundcloud-bot
sudo systemctl status soundcloud-bot
```

### 6. View Logs

```bash
sudo journalctl -u soundcloud-bot -f
```

## Extending for Other Platforms

To add YouTube, TikTok, etc., create new services in `app/services/` and handlers in `app/handlers/`:

```python
# app/services/youtube.py
class YouTubeDownloader:
    PATTERN = r"https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+"
    # Similar implementation to SoundCloudDownloader
```

## Legal & Technical Notes

### Legal
- **Copyright**: Downloading copyrighted content may violate laws in your jurisdiction
- **Terms of Service**: This may violate SoundCloud's ToS
- **Personal use only**: Do not redistribute downloaded content
- **Artist rights**: Respect creators; consider supporting them directly

### Technical Limitations
- **File size**: Telegram bots can only send files up to 50 MB
- **Rate limits**: SoundCloud may block IPs with excessive requests
- **Private tracks**: Cannot download private or subscriber-only content
- **Quality**: yt-dlp downloads the best available stream (usually 128-320 kbps)
- **Dependencies**: Requires `ffmpeg` for audio conversion

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token from @BotFather | (required) |
| `DOWNLOAD_DIR` | Temporary download directory | `/tmp/soundcloud_downloads` |

## License

MIT - Use at your own risk.
