"""SQLite database for user settings and download history."""
import sqlite3
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

DB_PATH = Path(__file__).parent.parent / "data" / "bot.db"


@dataclass
class DownloadRecord:
    id: int
    user_id: int
    platform: str
    url: str
    title: str
    artist: str
    downloaded_at: datetime


class Database:
    def __init__(self):
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = asyncio.Lock()
    
    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._init_tables()
        return self._conn
    
    def _init_tables(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT DEFAULT 'ru',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT,
                artist TEXT,
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
            
            CREATE TABLE IF NOT EXISTS rate_limits (
                user_id INTEGER PRIMARY KEY,
                request_count INTEGER DEFAULT 0,
                window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_downloads_user ON downloads(user_id);
            CREATE INDEX IF NOT EXISTS idx_downloads_date ON downloads(downloaded_at);
            
            CREATE TABLE IF NOT EXISTS file_cache (
                url_hash TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                file_type TEXT NOT NULL,
                title TEXT,
                artist TEXT,
                duration INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
    
    # ============ USER SETTINGS ============
    
    async def get_user_lang(self, user_id: int) -> str:
        async with self._lock:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT language FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            return row["language"] if row else "ru"
    
    async def set_user_lang(self, user_id: int, lang: str):
        async with self._lock:
            conn = self._get_conn()
            conn.execute("""
                INSERT INTO users (user_id, language, last_active)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    language = excluded.language,
                    last_active = CURRENT_TIMESTAMP
            """, (user_id, lang))
            conn.commit()
    
    async def update_last_active(self, user_id: int):
        async with self._lock:
            conn = self._get_conn()
            conn.execute("""
                INSERT INTO users (user_id) VALUES (?)
                ON CONFLICT(user_id) DO UPDATE SET last_active = CURRENT_TIMESTAMP
            """, (user_id,))
            conn.commit()
    
    # ============ RATE LIMITING ============
    
    async def check_rate_limit(self, user_id: int, max_requests: int = 10, window_seconds: int = 60) -> tuple[bool, int]:
        """Check if user is within rate limit. Returns (allowed, remaining)."""
        async with self._lock:
            conn = self._get_conn()
            now = datetime.now()
            
            row = conn.execute(
                "SELECT request_count, window_start FROM rate_limits WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            if row:
                window_start = datetime.fromisoformat(row["window_start"])
                if now - window_start > timedelta(seconds=window_seconds):
                    # Reset window
                    conn.execute("""
                        UPDATE rate_limits SET request_count = 1, window_start = ?
                        WHERE user_id = ?
                    """, (now.isoformat(), user_id))
                    conn.commit()
                    return True, max_requests - 1
                else:
                    count = row["request_count"]
                    if count >= max_requests:
                        return False, 0
                    conn.execute(
                        "UPDATE rate_limits SET request_count = request_count + 1 WHERE user_id = ?",
                        (user_id,)
                    )
                    conn.commit()
                    return True, max_requests - count - 1
            else:
                conn.execute(
                    "INSERT INTO rate_limits (user_id, request_count, window_start) VALUES (?, 1, ?)",
                    (user_id, now.isoformat())
                )
                conn.commit()
                return True, max_requests - 1
    
    # ============ DOWNLOAD HISTORY ============
    
    async def add_download(self, user_id: int, platform: str, url: str, title: str, artist: str):
        async with self._lock:
            conn = self._get_conn()
            conn.execute("""
                INSERT INTO downloads (user_id, platform, url, title, artist)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, platform, url, title, artist))
            conn.commit()
    
    async def get_user_history(self, user_id: int, limit: int = 10) -> list[DownloadRecord]:
        async with self._lock:
            conn = self._get_conn()
            rows = conn.execute("""
                SELECT id, user_id, platform, url, title, artist, downloaded_at
                FROM downloads WHERE user_id = ? ORDER BY downloaded_at DESC LIMIT ?
            """, (user_id, limit)).fetchall()
            
            return [
                DownloadRecord(
                    id=r["id"],
                    user_id=r["user_id"],
                    platform=r["platform"],
                    url=r["url"],
                    title=r["title"],
                    artist=r["artist"],
                    downloaded_at=datetime.fromisoformat(r["downloaded_at"])
                )
                for r in rows
            ]
    
    # ============ ANALYTICS ============
    
    async def get_stats(self) -> dict:
        async with self._lock:
            conn = self._get_conn()
            
            total_downloads = conn.execute("SELECT COUNT(*) FROM downloads").fetchone()[0]
            total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            
            today = datetime.now().date().isoformat()
            today_downloads = conn.execute(
                "SELECT COUNT(*) FROM downloads WHERE DATE(downloaded_at) = ?",
                (today,)
            ).fetchone()[0]
            
            popular = conn.execute("""
                SELECT title, artist, COUNT(*) as cnt
                FROM downloads
                GROUP BY title, artist
                ORDER BY cnt DESC
                LIMIT 5
            """).fetchall()
            
            return {
                "total_downloads": total_downloads,
                "total_users": total_users,
                "today_downloads": today_downloads,
                "popular_tracks": [(r["title"], r["artist"], r["cnt"]) for r in popular]
            }
    
    # ============ FILE CACHE ============
    
    async def get_cached_file(self, url: str) -> Optional[dict]:
        """Get cached file_id for URL."""
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        async with self._lock:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT file_id, file_type, title, artist, duration FROM file_cache WHERE url_hash = ?",
                (url_hash,)
            ).fetchone()
            
            if row:
                return {
                    "file_id": row["file_id"],
                    "file_type": row["file_type"],
                    "title": row["title"],
                    "artist": row["artist"],
                    "duration": row["duration"]
                }
            return None
    
    async def cache_file(self, url: str, file_id: str, file_type: str, title: str = "", artist: str = "", duration: int = 0):
        """Cache file_id for URL."""
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        async with self._lock:
            conn = self._get_conn()
            conn.execute("""
                INSERT INTO file_cache (url_hash, file_id, file_type, title, artist, duration)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(url_hash) DO UPDATE SET
                    file_id = excluded.file_id,
                    file_type = excluded.file_type
            """, (url_hash, file_id, file_type, title, artist, duration))
            conn.commit()


# Global instance
db = Database()
