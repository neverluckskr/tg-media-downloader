from app.services.base import BaseDownloader, MediaResult
from app.services.ytdlp_wrapper import run_ytdlp, extract_title_from_path
from app.config import config


class InstagramDownloader(BaseDownloader):
    PLATFORM = "instagram"
    URL_PATTERN = r"https?://(?:www\.)?instagram\.com/(?:p|reel|reels|stories)/[\w-]+"
    
    async def download(self, url: str, media_type: str = "video") -> MediaResult:
        extract_audio = media_type == "audio"
        
        success, file_path, error = await run_ytdlp(
            url=url,
            output_dir=config.DOWNLOAD_DIR,
            extract_audio=extract_audio,
            audio_format="mp3",
            format_spec="best" if not extract_audio else None,
            extra_args=["--cookies-from-browser", "chrome"] if False else None  # Enable if needed
        )
        
        if not success:
            # Instagram often requires login
            if "login" in error.lower() or "401" in error:
                return MediaResult(success=False, error="Instagram requires login for this content")
            return MediaResult(success=False, error=error)
        
        unique_id = file_path.name.split("_")[0]
        title = extract_title_from_path(file_path, unique_id)
        
        return MediaResult(
            success=True,
            file_path=file_path,
            title=title,
            author="Instagram",
            media_type=media_type
        )
