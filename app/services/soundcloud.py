import asyncio
import aiohttp
from typing import Optional

from app.services.base import BaseDownloader, MediaResult
from app.services.ytdlp_wrapper import run_ytdlp, extract_title_from_path, get_ytdlp_path
from app.services.mp3tools import mp3tools
from app.config import config


class SoundCloudDownloader(BaseDownloader):
    PLATFORM = "soundcloud"
    URL_PATTERN = r"https?://(?:www\.)?(?:soundcloud\.com/[\w-]+/[\w-]+|on\.soundcloud\.com/[\w]+)"
    
    async def get_metadata(self, url: str) -> dict:
        """Extract metadata including artwork URL using yt-dlp."""
        cmd = [
            get_ytdlp_path(),
            "--dump-json",
            "--no-download",
            url.strip()
        ]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            
            if proc.returncode == 0:
                import json
                return json.loads(stdout.decode())
        except Exception:
            pass
        return {}
    
    async def download_artwork(self, artwork_url: str) -> Optional[bytes]:
        """Download artwork image."""
        try:
            # Get highest quality artwork (replace size in URL)
            hq_url = artwork_url.replace("-large", "-t500x500").replace("-t300x300", "-t500x500")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(hq_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        return await resp.read()
        except Exception:
            pass
        return None
    
    async def download(self, url: str, media_type: str = "audio") -> MediaResult:
        # Get metadata first (for artwork and artist)
        metadata = await self.get_metadata(url)
        
        success, file_path, error = await run_ytdlp(
            url=url,
            output_dir=config.DOWNLOAD_DIR,
            extract_audio=True,
            audio_format="mp3"
        )
        
        if not success:
            return MediaResult(success=False, error=error)
        
        unique_id = file_path.name.split("_")[0]
        raw_title = metadata.get("title") or extract_title_from_path(file_path, unique_id)
        
        # Parse "Artist — Track" or "Artist - Track" format from title
        artist = "Unknown"
        title = raw_title
        for separator in [" — ", " - ", " – "]:
            if separator in raw_title:
                parts = raw_title.split(separator, 1)
                artist = parts[0].strip()
                title = parts[1].strip()
                break
        
        # Download and embed artwork
        artwork_url = metadata.get("thumbnail")
        if artwork_url:
            artwork_data = await self.download_artwork(artwork_url)
            if artwork_data:
                await mp3tools.set_album_art(file_path, artwork_data)
        
        return MediaResult(
            success=True,
            file_path=file_path,
            title=title,
            author=artist,
            media_type="audio"
        )
