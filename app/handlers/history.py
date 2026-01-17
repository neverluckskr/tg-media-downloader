"""History and stats handlers."""
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from app.i18n import t
from app.database import db

router = Router(name="history")


@router.message(Command("history"))
async def cmd_history(message: Message) -> None:
    """Show user's download history."""
    user_id = message.from_user.id
    
    history = await db.get_user_history(user_id, limit=10)
    
    if not history:
        await message.answer(t(user_id, "history_empty"))
        return
    
    platform_emojis = {
        "soundcloud": "🟠",
        "tiktok": "🎵", 
        "pinterest": "📌"
    }
    
    text = t(user_id, "history_title") + "\n\n"
    for i, record in enumerate(history, 1):
        emoji = platform_emojis.get(record.platform, "📥")
        title = record.title[:40] + "..." if len(record.title) > 40 else record.title
        artist = record.artist[:30] if record.artist else ""
        text += f"{emoji} <b>{title}</b>\n    <i>{artist}</i>\n\n"
    
    await message.answer(text, parse_mode="HTML")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Show bot statistics (admin only for now, can add check later)."""
    user_id = message.from_user.id
    
    stats = await db.get_stats()
    
    text = t(user_id, "stats_title") + "\n\n"
    text += f"👥 Users: <b>{stats['total_users']}</b>\n"
    text += f"📥 Total: <b>{stats['total_downloads']}</b>\n"
    text += f"📅 Today: <b>{stats['today_downloads']}</b>\n\n"
    
    if stats['popular_tracks']:
        text += "🔥 <b>Top tracks:</b>\n"
        for title, artist, count in stats['popular_tracks'][:5]:
            text += f"• {title} — {artist} ({count})\n"
    
    await message.answer(text, parse_mode="HTML")
