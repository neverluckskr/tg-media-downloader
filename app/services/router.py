from typing import Optional

from app.services.base import BaseDownloader, MediaResult
from app.services.soundcloud import SoundCloudDownloader
from app.services.tiktok import TikTokDownloader


DOWNLOADERS: list[type[BaseDownloader]] = [
    SoundCloudDownloader,
    TikTokDownloader,
]


class DownloadRouter:
    def __init__(self):
        self._instances: dict[str, BaseDownloader] = {}
    
    def get_downloader(self, url: str) -> Optional[BaseDownloader]:
        for cls in DOWNLOADERS:
            if cls.match(url):
                if cls.PLATFORM not in self._instances:
                    self._instances[cls.PLATFORM] = cls()
                return self._instances[cls.PLATFORM]
        return None
    
    def get_platform(self, url: str) -> Optional[str]:
        for cls in DOWNLOADERS:
            if cls.match(url):
                return cls.PLATFORM
        return None
    
    async def download(self, url: str, media_type: str = "audio") -> MediaResult:
        downloader = self.get_downloader(url)
        if not downloader:
            return MediaResult(success=False, error="Unsupported platform")
        return await downloader.download(url, media_type)


router = DownloadRouter()
