from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import asyncio
from io import BytesIO

from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON, TDRC, TRCK, APIC, ID3NoHeaderError
from PIL import Image


@dataclass
class MP3Tags:
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    genre: Optional[str] = None
    date: Optional[str] = None
    track: Optional[str] = None


class MP3ToolsService:
    """Service for editing MP3 tags and album art."""
    
    @staticmethod
    async def get_tags(file_path: Path) -> MP3Tags:
        """Extract tags from MP3 file."""
        def _get_tags():
            try:
                audio = MP3(file_path)
                tags = audio.tags
                if not tags:
                    return MP3Tags()
                
                return MP3Tags(
                    title=str(tags.get("TIT2", "")) or None,
                    artist=str(tags.get("TPE1", "")) or None,
                    album=str(tags.get("TALB", "")) or None,
                    genre=str(tags.get("TCON", "")) or None,
                    date=str(tags.get("TDRC", "")) or None,
                    track=str(tags.get("TRCK", "")) or None,
                )
            except Exception:
                return MP3Tags()
        
        return await asyncio.to_thread(_get_tags)
    
    @staticmethod
    async def set_tags(file_path: Path, tags: MP3Tags) -> bool:
        """Set tags on MP3 file."""
        def _set_tags():
            try:
                try:
                    audio = ID3(file_path)
                except ID3NoHeaderError:
                    audio = ID3()
                
                if tags.title:
                    audio["TIT2"] = TIT2(encoding=3, text=tags.title)
                if tags.artist:
                    audio["TPE1"] = TPE1(encoding=3, text=tags.artist)
                if tags.album:
                    audio["TALB"] = TALB(encoding=3, text=tags.album)
                if tags.genre:
                    audio["TCON"] = TCON(encoding=3, text=tags.genre)
                if tags.date:
                    audio["TDRC"] = TDRC(encoding=3, text=tags.date)
                if tags.track:
                    audio["TRCK"] = TRCK(encoding=3, text=tags.track)
                
                audio.save(file_path)
                return True
            except Exception:
                return False
        
        return await asyncio.to_thread(_set_tags)
    
    @staticmethod
    async def get_album_art(file_path: Path) -> Optional[bytes]:
        """Extract album art from MP3 file."""
        def _get_art():
            try:
                audio = MP3(file_path)
                tags = audio.tags
                if not tags:
                    return None
                
                for key in tags.keys():
                    if key.startswith("APIC"):
                        return tags[key].data
                return None
            except Exception:
                return None
        
        return await asyncio.to_thread(_get_art)
    
    @staticmethod
    async def set_album_art(file_path: Path, image_data: bytes, mime_type: str = "image/jpeg") -> bool:
        """Set album art on MP3 file."""
        def _set_art():
            try:
                from mutagen.mp3 import MP3
                
                # Ensure file has ID3 tags
                audio_file = MP3(file_path)
                if audio_file.tags is None:
                    audio_file.add_tags()
                    audio_file.save()
                
                # Now load ID3 and add artwork
                audio = ID3(file_path)
                
                # Remove existing album art
                audio.delall("APIC")
                
                # Add new album art
                audio["APIC"] = APIC(
                    encoding=3,
                    mime=mime_type,
                    type=3,  # Front cover
                    desc="Cover",
                    data=image_data
                )
                
                audio.save(file_path, v2_version=3)
                return True
            except Exception as e:
                print(f"Error setting album art: {e}")
                return False
        
        return await asyncio.to_thread(_set_art)
    
    @staticmethod
    async def delete_album_art(file_path: Path) -> bool:
        """Delete album art from MP3 file."""
        def _delete_art():
            try:
                audio = ID3(file_path)
                audio.delall("APIC")
                audio.save(file_path)
                return True
            except Exception:
                return False
        
        return await asyncio.to_thread(_delete_art)
    
    @staticmethod
    async def get_thumbnail_for_telegram(file_path: Path) -> Optional[bytes]:
        """Get album art resized for Telegram (320x320 JPEG)."""
        def _get_thumb():
            try:
                audio = ID3(file_path)
                for key in audio.keys():
                    if key.startswith("APIC"):
                        img_data = audio[key].data
                        
                        # Open and resize image
                        img = Image.open(BytesIO(img_data))
                        img = img.convert("RGB")  # Ensure RGB for JPEG
                        img.thumbnail((320, 320), Image.Resampling.LANCZOS)
                        
                        # Save as JPEG
                        output = BytesIO()
                        img.save(output, format="JPEG", quality=85)
                        return output.getvalue()
                return None
            except Exception:
                return None
        
        return await asyncio.to_thread(_get_thumb)
    
    @staticmethod
    def parse_tags_input(text: str) -> MP3Tags:
        """Parse user input for tags.
        
        Formats:
        - Simple: title:artist
        - Advanced: title:Value\\nartist:Value\\n...
        """
        lines = text.strip().split("\n")
        
        # Simple format: title:artist
        if len(lines) == 1 and lines[0].count(":") == 1:
            parts = lines[0].split(":")
            return MP3Tags(title=parts[0].strip(), artist=parts[1].strip())
        
        # Advanced format
        tags = MP3Tags()
        for line in lines:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            
            if key == "title":
                tags.title = value
            elif key == "artist":
                tags.artist = value
            elif key == "album":
                tags.album = value
            elif key == "genre":
                tags.genre = value
            elif key == "date":
                tags.date = value
            elif key == "track":
                tags.track = value
        
        return tags


mp3tools = MP3ToolsService()
