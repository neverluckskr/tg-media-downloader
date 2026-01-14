from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import re


@dataclass
class MediaResult:
    success: bool
    file_path: Optional[Path] = None
    title: Optional[str] = None
    author: Optional[str] = None
    duration: Optional[int] = None
    media_type: str = "audio"
    error: Optional[str] = None


class BaseDownloader(ABC):
    PLATFORM: str = ""
    URL_PATTERN: str = ""
    
    @classmethod
    def match(cls, url: str) -> bool:
        return bool(re.match(cls.URL_PATTERN, url.strip()))
    
    @abstractmethod
    async def download(self, url: str, media_type: str = "audio") -> MediaResult:
        pass
    
    @staticmethod
    async def cleanup(file_path: Optional[Path]) -> None:
        try:
            if file_path and file_path.exists():
                file_path.unlink()
        except Exception:
            pass
