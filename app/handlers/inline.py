"""Inline mode handler - @bot query in any chat."""
import asyncio
import json
import hashlib
from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from app.services.ytdlp_wrapper import get_ytdlp_path

router = Router(name="inline")


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


@router.inline_query()
async def handle_inline_query(inline_query: InlineQuery) -> None:
    """Handle inline queries - search SoundCloud."""
    query = inline_query.query.strip()
    
    if len(query) < 2:
        return
    
    try:
        results = await search_soundcloud(query, limit=10)
        
        articles = []
        for r in results:
            duration = f"{r['duration'] // 60}:{r['duration'] % 60:02d}" if r['duration'] else "?"
            result_id = hashlib.md5(r['url'].encode()).hexdigest()[:16]
            
            articles.append(
                InlineQueryResultArticle(
                    id=result_id,
                    title=r['title'],
                    description=f"{r['uploader']} • {duration}",
                    input_message_content=InputTextMessageContent(
                        message_text=r['url']
                    ),
                    thumbnail_url="https://soundcloud.com/favicon.ico"
                )
            )
        
        await inline_query.answer(articles, cache_time=60)
        
    except Exception:
        await inline_query.answer([], cache_time=10)
