import asyncio
import sys
import uuid
from pathlib import Path
from typing import Optional

from app.config import config


def get_ytdlp_path() -> str:
    venv_path = Path(sys.executable).parent / "yt-dlp"
    return str(venv_path) if venv_path.exists() else "yt-dlp"


async def run_ytdlp(
    url: str,
    output_dir: Optional[Path] = None,
    extract_audio: bool = True,
    audio_format: str = "mp3",
    format_spec: Optional[str] = None,
    extra_args: Optional[list[str]] = None,
    timeout: int = 180
) -> tuple[bool, Optional[Path], str]:
    """
    Universal yt-dlp async wrapper.
    Returns: (success, file_path, error_message)
    """
    output_dir = output_dir or config.DOWNLOAD_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    unique_id = uuid.uuid4().hex[:8]
    output_template = str(output_dir / f"{unique_id}_%(title)s.%(ext)s")
    
    cmd = [
        get_ytdlp_path(),
        "--no-playlist",
        "--no-warnings",
        "--output", output_template,
    ]
    
    if extract_audio:
        cmd += [
            "--extract-audio",
            "--audio-format", audio_format,
            "--audio-quality", "0",
        ]
    else:
        if format_spec:
            cmd += ["-f", format_spec]
        else:
            cmd += ["-f", "best[filesize<50M]/best"]
    
    cmd += ["--add-metadata"]
    
    if extra_args:
        cmd += extra_args
    
    cmd.append(url.strip())
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        
        if proc.returncode != 0:
            error = stderr.decode().strip()
            if "private" in error.lower():
                return False, None, "Content is private"
            if "404" in error or "not exist" in error.lower():
                return False, None, "Content not found"
            if "login" in error.lower() or "sign in" in error.lower():
                return False, None, "Login required"
            return False, None, error[:200] if error else "Download failed"
        
        # Find downloaded file
        ext = audio_format if extract_audio else "*"
        files = list(output_dir.glob(f"{unique_id}_*.{ext}"))
        if not files:
            files = list(output_dir.glob(f"{unique_id}_*"))
        
        if not files:
            return False, None, "Downloaded file not found"
        
        file_path = files[0]
        
        # Check Telegram size limit
        if file_path.stat().st_size > config.MAX_FILE_SIZE:
            file_path.unlink(missing_ok=True)
            return False, None, "File exceeds 50 MB limit"
        
        return True, file_path, ""
        
    except asyncio.TimeoutError:
        return False, None, f"Download timed out ({timeout}s)"
    except FileNotFoundError:
        return False, None, "yt-dlp not installed"
    except Exception as e:
        return False, None, str(e)


def extract_title_from_path(file_path: Path, unique_id: str) -> str:
    title = file_path.stem
    prefix = f"{unique_id}_"
    if title.startswith(prefix):
        title = title[len(prefix):]
    return title or "Unknown"
