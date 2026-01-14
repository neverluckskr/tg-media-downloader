"""Internationalization system for the bot."""
from typing import Optional
from pathlib import Path
import json

# User language storage (in production use Redis/DB)
_user_languages: dict[int, str] = {}

# Default language
DEFAULT_LANG = "ru"

# Translations
TRANSLATIONS = {
    "ru": {
        # Start & Help
        "welcome": "👋 Привет!\n\nВыбери язык / Choose language:",
        "start": "Кидай ссылку — скачаю:\n• <b>SoundCloud</b> → MP3\n• <b>TikTok</b> → видео или MP3",
        "help": "<b>Команды:</b>\n/mp3tools — редактор тегов\n/lang — сменить язык\n\n<b>Ссылки:</b>\n<code>soundcloud.com/...</code>\n<code>vm.tiktok.com/...</code>",
        
        # Download
        "downloading": "⏳",
        "error": "❌ Ошибка",
        "error_send": "❌ Ошибка отправки",
        "format_choice": "🎵 или 🎬 ?",
        "link_expired": "Ссылка устарела",
        "edit_prompt": "✏️ Редактировать?",
        
        # MP3 Tools
        "mp3tools_send": "🎵 Кидай MP3",
        "mp3tools_send_file": "❌ Отправь MP3 файл",
        "loading": "⏳",
        "sending": "⏳",
        
        # Buttons
        "btn_tags": "✏️ Теги",
        "btn_cover": "🖼 Обложка",
        "btn_done": "💾 Готово",
        "btn_cancel": "✖️",
        "btn_back": "⬅️ Назад",
        "btn_audio": "🎵 Audio",
        "btn_video": "🎬 Video",
        
        # Tag editing
        "enter_title": "Название трека:",
        "enter_artist": "Автор:",
        "tags_saved": "✅",
        
        # Album art
        "send_cover": "Кидай обложку",
        "send_new_cover": "Кидай новую обложку",
        "cover_updated": "✅",
        
        # Errors
        "file_not_found": "Файл не найден",
        "file_deleted": "Файл удалён",
        "cancelled": "❌",
        
        # Language
        "lang_changed": "🇷🇺 Русский",
    },
    "en": {
        # Start & Help
        "welcome": "👋 Hi!\n\nChoose language / Выбери язык:",
        "start": "Send a link — I'll download:\n• <b>SoundCloud</b> → MP3\n• <b>TikTok</b> → video or MP3",
        "help": "<b>Commands:</b>\n/mp3tools — tag editor\n/lang — change language\n\n<b>Links:</b>\n<code>soundcloud.com/...</code>\n<code>vm.tiktok.com/...</code>",
        
        # Download
        "downloading": "⏳",
        "error": "❌ Error",
        "error_send": "❌ Send error",
        "format_choice": "🎵 or 🎬 ?",
        "link_expired": "Link expired",
        "edit_prompt": "✏️ Edit?",
        
        # MP3 Tools
        "mp3tools_send": "🎵 Send MP3",
        "mp3tools_send_file": "❌ Send an MP3 file",
        "loading": "⏳",
        "sending": "⏳",
        
        # Buttons
        "btn_tags": "✏️ Tags",
        "btn_cover": "🖼 Cover",
        "btn_done": "💾 Done",
        "btn_cancel": "✖️",
        "btn_back": "⬅️ Back",
        "btn_audio": "🎵 Audio",
        "btn_video": "🎬 Video",
        
        # Tag editing
        "enter_title": "Track title:",
        "enter_artist": "Artist:",
        "tags_saved": "✅",
        
        # Album art
        "send_cover": "Send cover",
        "send_new_cover": "Send new cover",
        "cover_updated": "✅",
        
        # Errors
        "file_not_found": "File not found",
        "file_deleted": "File deleted",
        "cancelled": "❌",
        
        # Language
        "lang_changed": "🇬🇧 English",
    }
}


def get_user_lang(user_id: int) -> str:
    """Get user's language preference."""
    return _user_languages.get(user_id, DEFAULT_LANG)


def set_user_lang(user_id: int, lang: str) -> None:
    """Set user's language preference."""
    if lang in TRANSLATIONS:
        _user_languages[user_id] = lang


def t(user_id: int, key: str) -> str:
    """Get translated string for user."""
    lang = get_user_lang(user_id)
    return TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG]).get(key, key)


def detect_language(language_code: Optional[str]) -> str:
    """Detect language from Telegram language_code."""
    if not language_code:
        return DEFAULT_LANG
    
    lang = language_code.lower()[:2]
    if lang in TRANSLATIONS:
        return lang
    return DEFAULT_LANG
