import re
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.enums import ChatAction

from app.config import config
from app.services.downloader import soundcloud_downloader

router = Router(name="soundcloud")


@router.message(F.text.regexp(config.SOUNDCLOUD_PATTERN))
async def handle_soundcloud_link(message: Message) -> None:
    """Process SoundCloud links and send audio back."""
    url_match = re.search(config.SOUNDCLOUD_PATTERN, message.text)
    if not url_match:
        return
    
    url = url_match.group(0)
    status_msg = await message.answer("⏳ Downloading track...")
    
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_VOICE)
    
    result = await soundcloud_downloader.download(url)
    
    if not result.success:
        await status_msg.edit_text(f"❌ {result.error}")
        return
    
    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_DOCUMENT)
        
        audio_file = FSInputFile(
            path=result.file_path,
            filename=f"{result.artist} - {result.title}.mp3"
        )
        
        await message.answer_audio(
            audio=audio_file,
            title=result.title,
            performer=result.artist,
            duration=result.duration,
            caption=f"🎵 {result.artist} — {result.title}"
        )
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Failed to send audio: {str(e)}")
    finally:
        await soundcloud_downloader.cleanup(result.file_path)
