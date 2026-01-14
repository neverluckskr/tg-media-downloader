"""Search handler for SoundCloud."""
import asyncio
import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.i18n import t
from app.database import db
from app.services.ytdlp_wrapper import get_ytdlp_path

router = Router(name="search")


class SearchCallback(CallbackData, prefix="search"):
    url: str


async def search_soundcloud(query: str, limit: int = 5) -> list[dict]:
    """Search SoundCloud using yt-dlp."""
    cmd = [
        get_ytdlp_path(),
        "--dump-json",
        "--flat-playlist",
        "--no-download",
        f"scsearch{limit}:{query}"
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, _ = await process.communicate()
    
    results = []
    for line in stdout.decode().strip().split('\n'):
        if line:
            try:
                data = json.loads(line)
                results.append({
                    "title": data.get("title", "Unknown"),
                    "url": data.get("url") or data.get("webpage_url", ""),
                    "uploader": data.get("uploader", "Unknown"),
                    "duration": data.get("duration", 0)
                })
            except json.JSONDecodeError:
                continue
    
    return results


@router.message(Command("search"))
async def cmd_search(message: Message) -> None:
    """Handle /search command."""
    user_id = message.from_user.id
    
    # Check rate limit
    allowed, _ = await db.check_rate_limit(user_id)
    if not allowed:
        await message.answer(t(user_id, "rate_limit"))
        return
    
    # Get search query
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(t(user_id, "search_usage"), parse_mode="HTML")
        return
    
    query = args[1].strip()
    
    status = await message.answer(t(user_id, "searching"))
    
    try:
        results = await search_soundcloud(query)
        
        if not results:
            await status.edit_text(t(user_id, "no_results"))
            return
        
        # Build results keyboard
        builder = InlineKeyboardBuilder()
        for r in results:
            title = r["title"][:30] + "..." if len(r["title"]) > 30 else r["title"]
            # Store URL in callback - truncate if too long
            url = r["url"][:60] if r["url"] else ""
            builder.button(
                text=f"🎵 {title}",
                callback_data=SearchCallback(url=url)
            )
        builder.adjust(1)
        
        # Format results text
        text = "🔍 <b>SoundCloud:</b>\n\n"
        for i, r in enumerate(results, 1):
            duration = f"{r['duration'] // 60}:{r['duration'] % 60:02d}" if r['duration'] else "?"
            text += f"{i}. <b>{r['title']}</b>\n   {r['uploader']} • {duration}\n\n"
        
        await status.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        
    except Exception as e:
        await status.edit_text(f"{t(user_id, 'search_error')}: {str(e)[:50]}")


@router.callback_query(SearchCallback.filter())
async def handle_search_result(callback: CallbackQuery, callback_data: SearchCallback) -> None:
    """Handle search result selection."""
    from app.handlers.download import process_download
    
    await callback.answer()
    await callback.message.delete()
    
    # Download the selected track
    await process_download(
        callback.message,
        callback_data.url,
        "audio",
        platform="soundcloud",
        user_id=callback.from_user.id
    )
