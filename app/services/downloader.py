import asyncio
import re
import sys
import uuid
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from app.config import config


def get_ytdlp_path() -> str:
    """Get yt-dlp executable path from current venv."""
    venv_path = Path(sys.executable).parent / "yt-dlp"
    if venv_path.exists():
        return str(venv_path)
    return "yt-dlp"


@dataclass
class DownloadResult:
    success: bool
    file_path: Optional[Path] = None
    title: Optional[str] = None
    artist: Optional[str] = None
    duration: Optional[int] = None
    error: Optional[str] = None


class SoundCloudDownloader:
    """Async wrapper for yt-dlp to download SoundCloud tracks."""
    
    def __init__(self, download_dir: Optional[Path] = None):
        self.download_dir = download_dir or config.DOWNLOAD_DIR
        self.download_dir.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if URL is a valid SoundCloud track link."""
        pattern = config.SOUNDCLOUD_PATTERN
        return bool(re.match(pattern, url.strip()))
    
    async def download(self, url: str) -> DownloadResult:
        """Download a SoundCloud track asynchronously."""
        if not self.is_valid_url(url):
            return DownloadResult(success=False, error="Invalid SoundCloud URL")
        
        # Unique filename to avoid collisions
        unique_id = uuid.uuid4().hex[:8]
        output_template = str(self.download_dir / f"%(title)s_{unique_id}.%(ext)s")
        
        cmd = [
            get_ytdlp_path(),
            "--no-playlist",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",  # Best quality
            "--embed-thumbnail",
            "--add-metadata",
            "--output", output_template,
            "--print", "after_move:filepath",
            "--print", "%(title)s",
            "--print", "%(uploader)s",
            "--print", "%(duration)s",
            "--no-warnings",
            "--quiet",
            url.strip()
        ]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            
            if proc.returncode != 0:
                error_msg = stderr.decode().strip()
                if "private" in error_msg.lower():
                    return DownloadResult(success=False, error="This track is private")
                if "not exist" in error_msg.lower() or "404" in error_msg:
                    return DownloadResult(success=False, error="Track not found")
                return DownloadResult(
                    success=False, 
                    error=f"Download failed: {error_msg or 'Unknown error'}"
                )
            
            # Parse output: filepath, title, artist, duration
            lines = stdout.decode().strip().split("\n")
            if len(lines) < 4:
                return DownloadResult(success=False, error="Failed to parse download output")
            
            file_path = Path(lines[0])
            if not file_path.exists():
                return DownloadResult(success=False, error="Downloaded file not found")
            
            # Check file size
            if file_path.stat().st_size > config.MAX_FILE_SIZE:
                file_path.unlink(missing_ok=True)
                return DownloadResult(
                    success=False, 
                    error="File exceeds Telegram's 50 MB limit"
                )
            
            duration = None
            try:
                duration = int(float(lines[3])) if lines[3] and lines[3] != "NA" else None
            except (ValueError, IndexError):
                pass
            
            return DownloadResult(
                success=True,
                file_path=file_path,
                title=lines[1] if lines[1] != "NA" else "Unknown Title",
                artist=lines[2] if lines[2] != "NA" else "Unknown Artist",
                duration=duration
            )
            
        except asyncio.TimeoutError:
            return DownloadResult(success=False, error="Download timed out (120s)")
        except FileNotFoundError:
            return DownloadResult(
                success=False, 
                error="yt-dlp not installed. Run: pip install yt-dlp"
            )
        except Exception as e:
            return DownloadResult(success=False, error=f"Unexpected error: {str(e)}")
    
    @staticmethod
    async def cleanup(file_path: Path) -> None:
        """Remove temporary file after sending."""
        try:
            if file_path and file_path.exists():
                file_path.unlink()
        except Exception:
            pass


soundcloud_downloader = SoundCloudDownloader()
