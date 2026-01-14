"""Inline mode handler - @bot query in any chat."""
import hashlib
from aiogram import Router
from aiogram.types import (
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent,
    InlineQueryResultCachedAudio
)

from app.handlers.search import search_soundcloud
from app.database import db

router = Router(name="inline")


@router.inline_query()
async def handle_inline_query(inline_query: InlineQuery) -> None:
    """Handle inline queries - search SoundCloud."""
    query = inline_query.query.strip()
    
    if len(query) < 2:
        await inline_query.answer(
            [],
            switch_pm_text="🔎 Введите название трека",
            switch_pm_parameter="search",
            cache_time=5
        )
        return
    
    try:
        results = await search_soundcloud(query, limit=8, timeout=10)
        
        articles = []
        for r in results:
            dur = r.get('duration') or 0
            duration = f"{int(dur) // 60}:{int(dur) % 60:02d}" if dur else "?"
            result_id = hashlib.md5(r['url'].encode()).hexdigest()[:16]
            
            # Check if we have cached audio
            cached = await db.get_cached_file(r['url'])
            
            if cached and cached.get('file_id'):
                # Send cached audio directly! 🎵
                articles.append(
                    InlineQueryResultCachedAudio(
                        id=result_id,
                        audio_file_id=cached['file_id'],
                        caption=f"🎵 {r['uploader']}"
                    )
                )
            else:
                # Not cached - send link (bot will download and cache)
                articles.append(
                    InlineQueryResultArticle(
                        id=result_id,
                        title=f"🎵 {r['title']}",
                        description=f"{r['uploader']} • {duration} • Нажми чтобы скачать",
                        input_message_content=InputTextMessageContent(
                            message_text=r['url']
                        ),
                        thumbnail_url="https://a-v2.sndcdn.com/assets/images/sc-icons/favicon-2cadd14bdb.ico"
                    )
                )
        
        await inline_query.answer(articles, cache_time=30, is_personal=True)
        
    except Exception:
        await inline_query.answer([], cache_time=5)
