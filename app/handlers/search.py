"""Search handler for SoundCloud."""
import asyncio
import json
import hashlib
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.i18n import t
from app.database import db
from app.services.ytdlp_wrapper import get_ytdlp_path

router = Router(name="search")

# Store search results URLs (hash -> url)
_search_urls: dict[str, str] = {}


class SearchStates(StatesGroup):
    waiting_query = State()


class SearchCallback(CallbackData, prefix="src"):
    h: str  # URL hash


async def search_soundcloud(query: str, limit: int = 10, timeout: int = 15) -> list[dict]:
    """Search SoundCloud using yt-dlp with timeout."""
    cmd = [
        get_ytdlp_path(),
        "-j",
        "--no-download",
        "--socket-timeout", "10",
        f"scsearch{limit}:{query}"
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    try:
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        process.kill()
        return []
    
    results = []
    for line in stdout.decode().strip().split('\n'):
        if line:
            try:
                data = json.loads(line)
                # webpage_url is the proper soundcloud.com URL
                url = data.get("webpage_url", "")
                if url and "soundcloud.com" in url and "api.soundcloud" not in url:
                    results.append({
                        "title": data.get("title", "Unknown"),
                        "url": url,
                        "uploader": data.get("uploader", "Unknown"),
                        "duration": data.get("duration", 0)
                    })
            except json.JSONDecodeError:
                continue
    
    return results


async def do_search(message: Message, query: str, user_id: int) -> None:
    """Perform the actual search."""
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
            # Store URL with hash
            url_hash = hashlib.md5(r["url"].encode()).hexdigest()[:12]
            _search_urls[url_hash] = r["url"]
            builder.button(
                text=f"🎵 {title}",
                callback_data=SearchCallback(h=url_hash)
            )
        builder.adjust(1)
        
        # Format results text
        text = "🔍 <b>SoundCloud:</b>\n\n"
        for i, r in enumerate(results, 1):
            dur = r.get('duration') or 0
            if dur:
                duration = f"{int(dur) // 60}:{int(dur) % 60:02d}"
            else:
                duration = "?"
            text += f"{i}. <b>{r['title']}</b>\n   {r['uploader']} • {duration}\n\n"
        
        await status.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        
    except Exception as e:
        await status.edit_text(f"{t(user_id, 'search_error')}: {str(e)[:50]}")


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
    await do_search(message, query, user_id)


@router.message(SearchStates.waiting_query)
async def handle_search_query(message: Message, state: FSMContext) -> None:
    """Handle search query from FSM state."""
    await state.clear()
    user_id = message.from_user.id
    query = message.text.strip()
    
    if not query or len(query) < 2:
        return
    
    await do_search(message, query, user_id)


@router.callback_query(SearchCallback.filter())
async def handle_search_result(callback: CallbackQuery, callback_data: SearchCallback) -> None:
    """Handle search result selection."""
    from app.handlers.download import process_download
    
    url = _search_urls.pop(callback_data.h, None)
    if not url:
        await callback.answer(t(callback.from_user.id, "link_expired"), show_alert=True)
        return
    
    await callback.answer()
    await callback.message.delete()
    
    # Download the selected track
    await process_download(
        callback.message,
        url,
        "audio",
        platform="soundcloud",
        user_id=callback.from_user.id
    )
