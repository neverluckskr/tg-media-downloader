import re
import uuid
from aiogram import Router, F
from aiogram.types import Message, FSInputFile, CallbackQuery
from aiogram.enums import ChatAction
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.services.router import router as download_router
from app.services.base import BaseDownloader
from app.services.mp3tools import mp3tools
from app.handlers.mp3tools import _file_storage, get_mp3tools_keyboard
from app.i18n import t


class MediaTypeCallback(CallbackData, prefix="media"):
    action: str
    url_hash: str


bot_router = Router(name="download")

# URL storage for callbacks (simple in-memory, consider Redis for production)
_pending_urls: dict[str, str] = {}


def get_url_pattern() -> str:
    """Combined pattern for all supported platforms."""
    return (
        r"https?://(?:www\.)?"
        r"(?:"
        r"soundcloud\.com/[\w-]+/[\w-]+|"
        r"on\.soundcloud\.com/[\w]+|"
        r"(?:tiktok\.com/@[\w.-]+/video/\d+|vm\.tiktok\.com/[\w]+|vt\.tiktok\.com/[\w]+)"
        r")"
    )


URL_PATTERN = get_url_pattern()


@bot_router.message(F.text.regexp(URL_PATTERN))
async def handle_media_link(message: Message) -> None:
    """Auto-detect platform and offer download options."""
    url_match = re.search(URL_PATTERN, message.text)
    if not url_match:
        return
    
    url = url_match.group(0)
    platform = download_router.get_platform(url)
    
    if not platform:
        return
    
    # Audio-only platforms
    if platform == "soundcloud":
        await process_download(message, url, "audio", platform="soundcloud", user_id=message.from_user.id)
        return
    
    # TikTok - offer choice
    url_hash = str(hash(url))[-8:]
    _pending_urls[url_hash] = url
    
    user_id = message.from_user.id
    builder = InlineKeyboardBuilder()
    builder.button(text=t(user_id, "btn_audio"), callback_data=MediaTypeCallback(action="audio", url_hash=url_hash))
    builder.button(text=t(user_id, "btn_video"), callback_data=MediaTypeCallback(action="video", url_hash=url_hash))
    builder.adjust(2)
    
    await message.answer(
        t(user_id, "format_choice"),
        reply_markup=builder.as_markup()
    )


@bot_router.callback_query(MediaTypeCallback.filter())
async def handle_media_type_callback(callback: CallbackQuery, callback_data: MediaTypeCallback) -> None:
    """Process format selection callback."""
    url = _pending_urls.pop(callback_data.url_hash, None)
    
    if not url:
        await callback.answer(t(callback.from_user.id, "link_expired"), show_alert=True)
        return
    
    await callback.answer()
    await callback.message.delete()
    await process_download(callback.message, url, callback_data.action, user_id=callback.from_user.id)


async def process_download(message: Message, url: str, media_type: str, platform: str = "", user_id: int = 0) -> None:
    """Download and send media."""
    status_msg = await message.answer(t(user_id, "downloading"))
    
    action = ChatAction.UPLOAD_VOICE if media_type == "audio" else ChatAction.UPLOAD_VIDEO
    await message.bot.send_chat_action(chat_id=message.chat.id, action=action)
    
    result = await download_router.download(url, media_type)
    
    if not result.success:
        await status_msg.edit_text(f"❌ {result.error}")
        return
    
    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_DOCUMENT)
        
        if result.media_type == "audio":
            ext = result.file_path.suffix or ".mp3"
            audio_file = FSInputFile(
                path=result.file_path,
                filename=f"{result.author} - {result.title}{ext}"
            )
            
            # Get resized thumbnail for Telegram (320x320 JPEG)
            thumb_data = await mp3tools.get_thumbnail_for_telegram(result.file_path) if platform == "soundcloud" else None
            thumbnail = None
            thumb_path = None
            if thumb_data:
                thumb_path = result.file_path.parent / f"{result.file_path.stem}_thumb.jpg"
                thumb_path.write_bytes(thumb_data)
                thumbnail = FSInputFile(path=thumb_path)
            
            await message.answer_audio(
                audio=audio_file,
                title=result.title,
                performer=result.author,
                duration=result.duration,
                thumbnail=thumbnail
            )
            
            # Cleanup thumbnail
            if thumb_path and thumb_path.exists():
                thumb_path.unlink()
            
            # For SoundCloud: offer MP3 Tools
            if platform == "soundcloud":
                file_id = uuid.uuid4().hex[:8]
                _file_storage[file_id] = result.file_path
                
                await status_msg.edit_text(
                    t(user_id, "edit_prompt"),
                    reply_markup=get_mp3tools_keyboard(file_id, user_id).as_markup()
                )
                return  # Don't cleanup - file is now managed by mp3tools
        else:
            video_file = FSInputFile(
                path=result.file_path,
                filename=f"{result.title}.mp4"
            )
            await message.answer_video(
                video=video_file
            )
        
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"{t(user_id, 'error_send')}: {str(e)[:50]}")
    finally:
        # Cleanup only if not SoundCloud (which keeps file for editing)
        if platform != "soundcloud":
            await BaseDownloader.cleanup(result.file_path)
