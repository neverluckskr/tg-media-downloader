import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    DOWNLOAD_DIR: Path = Path(os.getenv("DOWNLOAD_DIR", "/tmp/media_downloads"))
    
    # Telegram file size limit (50 MB for bots)
    MAX_FILE_SIZE: int = 50 * 1024 * 1024
    
    @classmethod
    def validate(cls) -> None:
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required")
        cls.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


config = Config()
