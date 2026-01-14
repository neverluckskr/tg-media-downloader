from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command."""
    await message.answer(
        "🎵 <b>Media Downloader Bot</b>\n\n"
        "Отправь мне ссылку и я скачаю для тебя!\n\n"
        "<b>Поддерживаемые платформы:</b>\n"
        "• SoundCloud (аудио)\n"
        "• TikTok (аудио/видео)\n\n"
        "<b>Инструменты:</b>\n"
        "• /mp3tools — редактор MP3 тегов и обложек\n\n"
        "Используй /help для подробностей.",
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    await message.answer(
        "📖 <b>Как использовать:</b>\n\n"
        "<b>Скачивание:</b>\n"
        "1. Отправь ссылку на трек/видео\n"
        "2. Выбери формат (для TikTok)\n"
        "3. Получи файл!\n\n"
        "<b>Примеры ссылок:</b>\n"
        "• <code>https://soundcloud.com/artist/track</code>\n"
        "• <code>https://vm.tiktok.com/...</code>\n\n"
        "<b>MP3 Tools (/mp3tools):</b>\n"
        "• ✏️ Tag Editor — редактирование тегов\n"
        "• 🖼 Album Art — смена обложки\n\n"
        "<b>Ограничения:</b>\n"
        "• Только публичный контент\n"
        "• Макс. размер: 50 MB\n\n"
        "⚠️ Уважайте авторские права.",
        parse_mode="HTML"
    )
