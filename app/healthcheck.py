"""Healthcheck HTTP server for monitoring."""
import asyncio
from aiohttp import web
from datetime import datetime

from app.config import config
from app.database import db

start_time = datetime.now()


async def health_handler(request):
    """Health check endpoint."""
    stats = await db.get_stats()
    uptime = datetime.now() - start_time
    
    return web.json_response({
        "status": "ok",
        "uptime_seconds": int(uptime.total_seconds()),
        "total_users": stats["total_users"],
        "total_downloads": stats["total_downloads"],
        "today_downloads": stats["today_downloads"]
    })


async def start_healthcheck_server():
    """Start the healthcheck HTTP server."""
    app = web.Application()
    app.router.add_get("/", health_handler)
    app.router.add_get("/health", health_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, "0.0.0.0", config.HEALTH_PORT)
    await site.start()
    
    return runner
