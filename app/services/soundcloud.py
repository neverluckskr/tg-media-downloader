import asyncio
import aiohttp
import logging
from typing import Optional

from app.services.base import BaseDownloader, MediaResult
from app.services.ytdlp_wrapper import run_ytdlp, extract_title_from_path, get_ytdlp_path
from app.services.mp3tools import mp3tools
from app.config import config

logger = logging.getLogger(__name__)


class SoundCloudDownloader(BaseDownloader):
    PLATFORM = "soundcloud"
    URL_PATTERN = r"https?://(?:www\.)?(?:soundcloud\.com/[\w-]+/[\w-]+|on\.soundcloud\.com/[\w]+)"
    
    async def get_metadata(self, url: str) -> dict:
        """Extract metadata including artwork URL using yt-dlp."""
        cmd = [
            get_ytdlp_path(),
            "--dump-json",
            "--no-download",
            "--socket-timeout", "15",
            url.strip()
        ]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=20)
            
            if proc.returncode == 0 and stdout:
                import json
                data = json.loads(stdout.decode())
                return data
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
        
        # Get uploader (channel name) - try multiple fields
        uploader = (
            metadata.get("uploader") or 
            metadata.get("creator") or 
            metadata.get("artist") or
            metadata.get("channel") or
            metadata.get("uploader_id") or
            ""
        )
        
        logger.info(f"Metadata: title={raw_title}, uploader={uploader}, keys={list(metadata.keys())[:10]}")
        
        # Also try to read artist from MP3 tags (yt-dlp embeds this)
        if not uploader:
            try:
                from mutagen.mp3 import MP3
                from mutagen.id3 import ID3
                audio = MP3(file_path, ID3=ID3)
                if audio.tags:
                    # TPE1 = artist tag
                    if 'TPE1' in audio.tags:
                        uploader = str(audio.tags['TPE1'].text[0])
            except Exception:
                pass
        
        # Parse "Artist — Track" or "Artist - Track" format from title
        artist = None
        title = raw_title
        for separator in [" — ", " - ", " – ", " | "]:
            if separator in raw_title:
                parts = raw_title.split(separator, 1)
                artist = parts[0].strip()
                title = parts[1].strip()
                break
        
        # Fallback: use uploader if no artist found in title
        if not artist or artist == "Unknown":
            artist = uploader if uploader else "Unknown"
        
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
