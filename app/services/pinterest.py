import asyncio
import re
import uuid
import aiohttp
from pathlib import Path
from typing import Optional

from app.services.base import BaseDownloader, MediaResult
from app.config import config


class PinterestDownloader(BaseDownloader):
    PLATFORM = "pinterest"
    URL_PATTERN = r"https?://(?:[a-z]{2}\.)?(?:www\.)?(?:pinterest\.(?:com|co\.uk|de|fr|es|it|ca|au|jp|kr|se|nz|at|ch|pt|ie|co|cl|mx|dk|no|be|fi|nl|pl|cz)/pin/[\w-]+|pin\.it/[\w]+)"
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    async def _resolve_short_url(self, url: str) -> Optional[str]:
        """Resolve pin.it short URL to full Pinterest URL."""
        if "pin.it" in url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.head(url, headers=self.HEADERS, allow_redirects=True, timeout=10) as resp:
                        return str(resp.url)
            except Exception:
                pass
        return url
    
    async def _extract_media(self, url: str) -> tuple[Optional[str], Optional[str], str]:
        """
        Extract media URL from Pinterest page.
        Returns: (image_url, video_url, title)
        """
        try:
            resolved_url = await self._resolve_short_url(url)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(resolved_url, headers=self.HEADERS, timeout=15) as resp:
                    if resp.status != 200:
                        return None, None, ""
                    
                    html = await resp.text()
                    
                    # Extract title
                    title_match = re.search(r'<title>([^<]+)</title>', html)
                    title = title_match.group(1) if title_match else "Pinterest"
                    title = re.sub(r'\s*[-|]\s*Pinterest.*$', '', title).strip()
                    
                    # Find video URLs (check first - videos are preferred)
                    videos = re.findall(r'https://v[^\"\s]*\.pinimg\.com/[^\"\s]+\.mp4', html)
                    video_url = videos[0] if videos else None
                    
                    # Find image URLs
                    images = re.findall(r'https://i\.pinimg\.com/[^\"\s]+\.(?:jpg|png|gif|webp)', html)
                    
                    # Prefer original quality
                    image_url = None
                    if images:
                        originals = [img for img in images if '/originals/' in img]
                        high_res = [img for img in images if '/1200x/' in img or '/736x/' in img]
                        
                        if originals:
                            image_url = originals[0]
                        elif high_res:
                            image_url = high_res[0]
                        else:
                            image_url = images[0]
                    
                    return image_url, video_url, title[:80]
                    
        except Exception:
            return None, None, ""
    
    async def download(self, url: str, media_type: str = "auto") -> MediaResult:
        image_url, video_url, title = await self._extract_media(url)
        
        if not image_url and not video_url:
            return MediaResult(success=False, error="Could not extract media from Pinterest")
        
        # Determine what to download
        media_url = video_url if video_url else image_url
        is_video = video_url is not None
        
        try:
            output_dir = config.DOWNLOAD_DIR
            output_dir.mkdir(parents=True, exist_ok=True)
            
            unique_id = uuid.uuid4().hex[:8]
            safe_title = re.sub(r'[^\w\s-]', '', title)[:50] or "pinterest"
            ext = ".mp4" if is_video else ".jpg"
            file_path = output_dir / f"{unique_id}_{safe_title}{ext}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(media_url, headers=self.HEADERS, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status != 200:
                        return MediaResult(success=False, error=f"Download failed: {resp.status}")
                    
                    content = await resp.read()
                    
                    if len(content) > config.MAX_FILE_SIZE:
                        return MediaResult(success=False, error="File exceeds 50 MB limit")
                    
                    file_path.write_bytes(content)
                    
                    return MediaResult(
                        success=True,
                        file_path=file_path,
                        title=title or "Pinterest",
                        author="Pinterest",
                        media_type="video" if is_video else "photo"
                    )
                    
        except asyncio.TimeoutError:
            return MediaResult(success=False, error="Download timed out")
        except Exception as e:
            return MediaResult(success=False, error=str(e)[:200])
