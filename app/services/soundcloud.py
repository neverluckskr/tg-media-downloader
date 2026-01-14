from app.services.base import BaseDownloader, MediaResult
from app.services.ytdlp_wrapper import run_ytdlp, extract_title_from_path
from app.config import config


class SoundCloudDownloader(BaseDownloader):
    PLATFORM = "soundcloud"
    URL_PATTERN = r"https?://(?:www\.)?soundcloud\.com/[\w-]+/[\w-]+"
    
    async def download(self, url: str, media_type: str = "audio") -> MediaResult:
        success, file_path, error = await run_ytdlp(
            url=url,
            output_dir=config.DOWNLOAD_DIR,
            extract_audio=True,
            audio_format="mp3"
        )
        
        if not success:
            return MediaResult(success=False, error=error)
        
        unique_id = file_path.name.split("_")[0]
        title = extract_title_from_path(file_path, unique_id)
        
        return MediaResult(
            success=True,
            file_path=file_path,
            title=title,
            author="SoundCloud",
            media_type="audio"
        )
