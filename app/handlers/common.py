from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command."""
    await message.answer(
        "🎵 <b>SoundCloud Downloader Bot</b>\n\n"
        "Send me a SoundCloud track link and I'll download it for you!\n\n"
        "<b>Supported format:</b>\n"
        "<code>https://soundcloud.com/artist/track-name</code>\n\n"
        "Use /help for more info.",
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    await message.answer(
        "📖 <b>How to use:</b>\n\n"
        "1. Copy a SoundCloud track link\n"
        "2. Send it to this bot\n"
        "3. Wait for the download\n"
        "4. Receive your audio file!\n\n"
        "<b>Limitations:</b>\n"
        "• Only public tracks are supported\n"
        "• Max file size: 50 MB\n"
        "• Playlists are not supported (yet)\n\n"
        "⚠️ Please respect artist copyrights.",
        parse_mode="HTML"
    )
