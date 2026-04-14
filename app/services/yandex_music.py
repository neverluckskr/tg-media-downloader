import asyncio
import logging
import re
from pathlib import Path
from typing import Optional

from app.config import config
from app.services.base import BaseDownloader, MediaResult
from app.services.mp3tools import MP3Tags, mp3tools

try:
    from yandex_music import ClientAsync
except ImportError:
    ClientAsync = None


logger = logging.getLogger(__name__)


class YandexMusicDownloader(BaseDownloader):
    PLATFORM = "yandex_music"
    URL_PATTERN = (
        r"https?://music\.yandex\.(?:ru|com|by|kz|uz)"
        r"/album/\d+/track/\d+(?:\?[^\s]+)?"
    )
    TRACK_PATTERN = re.compile(
        r"https?://music\.yandex\.(?:ru|com|by|kz|uz)/album/(?P<album_id>\d+)/track/(?P<track_id>\d+)"
    )
    BITRATE_FALLBACKS = (320, 192, 128, 64)

    def __init__(self) -> None:
        self._client = None
        self._client_lock = asyncio.Lock()

    async def _get_client(self):
        if ClientAsync is None:
            raise RuntimeError("Python package 'yandex-music' is not installed")
        if not config.YANDEX_MUSIC_TOKEN:
            raise RuntimeError("YANDEX_MUSIC_TOKEN is not configured")

        if self._client is not None:
            return self._client

        async with self._client_lock:
            if self._client is None:
                self._client = await ClientAsync(config.YANDEX_MUSIC_TOKEN).init()
        return self._client

    @classmethod
    def _parse_track_key(cls, url: str) -> str:
        match = cls.TRACK_PATTERN.match(url.strip())
        if not match:
            raise ValueError("Unsupported Yandex Music URL")
        return f"{match.group('track_id')}:{match.group('album_id')}"

    @staticmethod
    def _safe_name(value: str, fallback: str) -> str:
        cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", value or "").strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned[:120] or fallback

    @staticmethod
    def _get_artists(track) -> str:
        artists = []
        for artist in getattr(track, "artists", []) or []:
            name = getattr(artist, "name", None)
            if name:
                artists.append(name)
        return ", ".join(artists) or "Unknown"

    @staticmethod
    def _get_album(track) -> str:
        albums = getattr(track, "albums", []) or []
        if not albums:
            return ""
        return getattr(albums[0], "title", "") or ""

    @staticmethod
    def _get_track_number(track) -> str:
        albums = getattr(track, "albums", []) or []
        if not albums:
            return ""
        position = getattr(albums[0], "track_position", None)
        if not position:
            return ""
        index = getattr(position, "index", None)
        if index is None:
            return ""
        return str(index)

    @staticmethod
    def _get_year(track) -> str:
        albums = getattr(track, "albums", []) or []
        if not albums:
            return ""
        year = getattr(albums[0], "year", None)
        return str(year) if year else ""

    async def _download_track_audio(self, track, file_path: Path) -> None:
        last_error = None
        for bitrate in self.BITRATE_FALLBACKS:
            try:
                await track.download_async(str(file_path), codec="mp3", bitrate_in_kbps=bitrate)
                return
            except Exception as exc:
                last_error = exc
                logger.warning("Yandex Music download failed for bitrate %s: %s", bitrate, exc)

        raise RuntimeError(str(last_error) if last_error else "Unable to download track")

    async def download(self, url: str, media_type: str = "audio") -> MediaResult:
        if media_type != "audio":
            return MediaResult(success=False, error="Yandex Music supports audio only")

        try:
            track_key = self._parse_track_key(url)
        except ValueError as exc:
            return MediaResult(success=False, error=str(exc))

        try:
            client = await self._get_client()
            tracks = await client.tracks([track_key])
            track = tracks[0] if tracks else None

            if not track:
                return MediaResult(success=False, error="Track not found")
            if getattr(track, "available", True) is False:
                return MediaResult(success=False, error="Track is unavailable")

            artist = self._get_artists(track)
            title = track.title or "Unknown"
            version = getattr(track, "version", None)
            if version:
                title = f"{title} ({version})"

            safe_artist = self._safe_name(artist, "Unknown")
            safe_title = self._safe_name(title, "track")
            file_path = config.DOWNLOAD_DIR / f"ym_{track.id}_{safe_artist} - {safe_title}.mp3"

            await self._download_track_audio(track, file_path)

            if not file_path.exists():
                return MediaResult(success=False, error="Downloaded file not found")

            if file_path.stat().st_size > config.MAX_FILE_SIZE:
                await BaseDownloader.cleanup(file_path)
                return MediaResult(success=False, error="File exceeds 50 MB limit")

            cover_bytes = None
            try:
                cover_bytes = await track.download_cover_bytes_async(size="1000x1000")
            except Exception as exc:
                logger.warning("Yandex Music cover download failed: %s", exc)

            if cover_bytes:
                await mp3tools.set_album_art(file_path, cover_bytes)

            await mp3tools.set_tags(
                file_path,
                MP3Tags(
                    title=title,
                    artist=artist,
                    album=self._get_album(track) or None,
                    date=self._get_year(track) or None,
                    track=self._get_track_number(track) or None,
                ),
            )

            duration_ms = getattr(track, "duration_ms", None)
            duration = int(duration_ms / 1000) if duration_ms else None

            return MediaResult(
                success=True,
                file_path=file_path,
                title=title,
                author=artist,
                duration=duration,
                media_type="audio",
            )
        except Exception as exc:
            logger.exception("Yandex Music download failed")
            message = str(exc)
            if "Unauthorized" in message or "token" in message.lower():
                message = "Invalid or expired Yandex Music token"
            return MediaResult(success=False, error=message[:200] or "Yandex Music download failed")
