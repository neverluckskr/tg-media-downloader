import asyncio
import re
import uuid
import aiohttp
from pathlib import Path
from typing import Optional

from app.services.base import BaseDownloader, MediaResult
from app.services.ytdlp_wrapper import run_ytdlp, extract_title_from_path
from app.config import config


class TikTokDownloader(BaseDownloader):
    PLATFORM = "tiktok"
    URL_PATTERN = r"https?://(?:www\.)?(?:tiktok\.com/@[\w.-]+/(?:video|photo)/\d+|vm\.tiktok\.com/[\w]+|vt\.tiktok\.com/[\w]+)"
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    async def _resolve_short_url(self, url: str) -> Optional[str]:
        """Resolve vm.tiktok.com or vt.tiktok.com to full URL."""
        if "vm.tiktok.com" in url or "vt.tiktok.com" in url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.head(url, headers=self.HEADERS, allow_redirects=True, timeout=10) as resp:
                        return str(resp.url)
            except Exception:
                pass
        return url
    
    async def _is_photo_post(self, url: str) -> bool:
        """Check if URL is a photo slideshow post."""
        resolved = await self._resolve_short_url(url)
        return "/photo/" in resolved if resolved else False
    
    async def _download_photo_slideshow(self, url: str) -> MediaResult:
        """Download TikTok photo slideshow using TikWM API."""
        try:
            resolved_url = await self._resolve_short_url(url)
            
            # Extract post ID from URL
            match = re.search(r'/photo/(\d+)', resolved_url)
            if not match:
                return MediaResult(success=False, error="Cannot extract photo ID")
            
            post_id = match.group(1)
            
            # Use TikWM API (free, no auth required)
            api_url = "https://www.tikwm.com/api/"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    api_url,
                    data={"url": resolved_url, "hd": 1},
                    headers=self.HEADERS,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status != 200:
                        return MediaResult(success=False, error=f"API error: {resp.status}")
                    
                    data = await resp.json()
                    
                    if data.get("code") != 0:
                        return MediaResult(success=False, error=data.get("msg", "API error"))
                    
                    video_data = data.get("data", {})
                    images = video_data.get("images", [])
                    
                    if not images:
                        # Fallback: maybe it's actually a video
                        video_url = video_data.get("play") or video_data.get("hdplay")
                        if video_url:
                            return await self._download_video_direct(video_url, video_data.get("title", "TikTok"))
                        return MediaResult(success=False, error="No images found")
                    
                    # Download all images and create a collage or return first one
                    output_dir = config.DOWNLOAD_DIR
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    unique_id = uuid.uuid4().hex[:8]
                    downloaded_images = []
                    
                    for i, img_url in enumerate(images[:10]):  # Max 10 images
                        try:
                            async with session.get(img_url, timeout=aiohttp.ClientTimeout(total=15)) as img_resp:
                                if img_resp.status == 200:
                                    img_data = await img_resp.read()
                                    img_path = output_dir / f"{unique_id}_photo_{i}.jpg"
                                    img_path.write_bytes(img_data)
                                    downloaded_images.append(img_path)
                        except Exception:
                            continue
                    
                    if not downloaded_images:
                        return MediaResult(success=False, error="Failed to download images")
                    
                    title = video_data.get("title", "TikTok Slideshow")[:80]
                    author = video_data.get("author", {}).get("nickname", "TikTok")
                    
                    return MediaResult(
                        success=True,
                        file_path=downloaded_images[0],  # Return first image, handler will send all
                        title=title,
                        author=author,
                        media_type="photo",
                        extra_files=downloaded_images[1:] if len(downloaded_images) > 1 else None
                    )
                    
        except asyncio.TimeoutError:
            return MediaResult(success=False, error="Download timed out")
        except Exception as e:
            return MediaResult(success=False, error=str(e)[:200])
    
    async def _download_video_direct(self, video_url: str, title: str) -> MediaResult:
        """Download video directly from URL."""
        try:
            output_dir = config.DOWNLOAD_DIR
            output_dir.mkdir(parents=True, exist_ok=True)
            
            unique_id = uuid.uuid4().hex[:8]
            safe_title = re.sub(r'[^\w\s-]', '', title)[:50]
            file_path = output_dir / f"{unique_id}_{safe_title}.mp4"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url, headers=self.HEADERS, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status != 200:
                        return MediaResult(success=False, error=f"Download failed: {resp.status}")
                    
                    content = await resp.read()
                    
                    if len(content) > config.MAX_FILE_SIZE:
                        return MediaResult(success=False, error="File exceeds 50 MB limit")
                    
                    file_path.write_bytes(content)
                    
                    return MediaResult(
                        success=True,
                        file_path=file_path,
                        title=title[:80],
                        author="TikTok",
                        media_type="video"
                    )
        except Exception as e:
            return MediaResult(success=False, error=str(e)[:200])
    
    async def download(self, url: str, media_type: str = "video") -> MediaResult:
        # Check if it's a photo slideshow
        if await self._is_photo_post(url):
            return await self._download_photo_slideshow(url)
        
        # Regular video download via yt-dlp
        extract_audio = media_type == "audio"
        
        success, file_path, error = await run_ytdlp(
            url=url,
            output_dir=config.DOWNLOAD_DIR,
            extract_audio=extract_audio,
            audio_format="mp3",
            format_spec="best" if not extract_audio else None
        )
        
        if not success:
            return MediaResult(success=False, error=error)
        
        unique_id = file_path.name.split("_")[0]
        title = extract_title_from_path(file_path, unique_id)
        
        return MediaResult(
            success=True,
            file_path=file_path,
            title=title,
            author="TikTok",
            media_type=media_type
        )
