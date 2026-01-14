"""Inline mode handler - @bot query in any chat."""
import hashlib
from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from app.handlers.search import search_soundcloud

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
        # Fast search with timeout=10s, limit=8 results
        results = await search_soundcloud(query, limit=8, timeout=10)
        
        articles = []
        for r in results:
            dur = r.get('duration') or 0
            duration = f"{int(dur) // 60}:{int(dur) % 60:02d}" if dur else "?"
            result_id = hashlib.md5(r['url'].encode()).hexdigest()[:16]
            
            articles.append(
                InlineQueryResultArticle(
                    id=result_id,
                    title=f"🎵 {r['title']}",
                    description=f"{r['uploader']} • {duration}",
                    input_message_content=InputTextMessageContent(
                        message_text=r['url']
                    ),
                    thumbnail_url="https://a-v2.sndcdn.com/assets/images/sc-icons/favicon-2cadd14bdb.ico"
                )
            )
        
        await inline_query.answer(articles, cache_time=60)
        
    except Exception:
        await inline_query.answer([], cache_time=5)
