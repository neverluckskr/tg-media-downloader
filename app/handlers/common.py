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
        "• SoundCloud\n"
        "• YouTube / YouTube Music\n"
        "• TikTok\n"
        "• Instagram (Reels/Posts)\n\n"
        "Используй /help для подробностей.",
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    await message.answer(
        "📖 <b>Как использовать:</b>\n\n"
        "1. Скопируй ссылку на трек/видео\n"
        "2. Отправь её боту\n"
        "3. Выбери формат (аудио/видео)\n"
        "4. Получи файл!\n\n"
        "<b>Примеры ссылок:</b>\n"
        "• <code>https://soundcloud.com/artist/track</code>\n"
        "• <code>https://youtube.com/watch?v=...</code>\n"
        "• <code>https://vm.tiktok.com/...</code>\n"
        "• <code>https://instagram.com/reel/...</code>\n\n"
        "<b>Ограничения:</b>\n"
        "• Только публичный контент\n"
        "• Макс. размер: 50 MB\n"
        "• Плейлисты не поддерживаются\n\n"
        "⚠️ Уважайте авторские права.",
        parse_mode="HTML"
    )
