from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command."""
    await message.answer(
        "👋 Привет!\n\n"
        "Кидай ссылку — скачаю:\n"
        "• <b>SoundCloud</b> → MP3\n"
        "• <b>TikTok</b> → MP3 или видео",
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    await message.answer(
        "<b>Команды:</b>\n"
        "/mp3tools — редактор тегов MP3\n\n"
        "<b>Ссылки:</b>\n"
        "<code>soundcloud.com/...</code>\n"
        "<code>vm.tiktok.com/...</code>\n\n"
        "Лимит: 50 MB",
        parse_mode="HTML"
    )
