import re

from app.services.base import BaseDownloader, MediaResult
from app.services.ytdlp_wrapper import run_ytdlp, extract_title_from_path
from app.config import config


class YouTubeDownloader(BaseDownloader):
    PLATFORM = "youtube"
    URL_PATTERN = r"https?://(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/|music\.youtube\.com/watch\?v=)[\w-]+"
    
    @staticmethod
    def clean_url(url: str) -> str:
        """Remove tracking params, convert music.youtube to regular youtube."""
        # Extract video ID
        patterns = [
            r"(?:youtube\.com/watch\?v=|youtu\.be/|music\.youtube\.com/watch\?v=)([\w-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                return f"https://www.youtube.com/watch?v={video_id}"
        return url
    
    async def download(self, url: str, media_type: str = "audio") -> MediaResult:
        # Convert music.youtube.com to regular youtube.com
        clean_url = self.clean_url(url)
        extract_audio = media_type == "audio"
        
        # Video: limit filesize for Telegram
        format_spec = None
        if not extract_audio:
            format_spec = "best[filesize<50M]/bestvideo[filesize<45M]+bestaudio/best"
        
        success, file_path, error = await run_ytdlp(
            url=clean_url,
            output_dir=config.DOWNLOAD_DIR,
            extract_audio=extract_audio,
            audio_format="mp3",
            format_spec=format_spec,
            timeout=300
        )
        
        if not success:
            return MediaResult(success=False, error=error)
        
        unique_id = file_path.name.split("_")[0]
        title = extract_title_from_path(file_path, unique_id)
        
        return MediaResult(
            success=True,
            file_path=file_path,
            title=title,
            author="YouTube",
            media_type=media_type
        )
