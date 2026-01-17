"""Internationalization system for the bot."""
from typing import Optional

# In-memory cache (DB is primary storage)
_user_languages: dict[int, str] = {}

DEFAULT_LANG = "ru"

# Translations
TRANSLATIONS = {
    "ru": {
        # Start & Help
        "welcome": (
            "✨ <b>Media Downloader</b>\n\n"
            "🎵 Скачивай медиа с популярных платформ\n\n"
            "🌐 Выбери язык / Choose language:"
        ),
        "start": (
            "🚀 <b>Готов к работе!</b>\n\n"
            "📎 Просто отправь ссылку:\n\n"
            "  🟠 <b>SoundCloud</b> → музыка\n"
            "  🎵 <b>TikTok</b> → видео и фото\n"
            "  📌 <b>Pinterest</b> → фото и видео\n\n"
            "💡 <i>Или используй кнопки ниже</i>"
        ),
        "help": (
            "📖 <b>Справка</b>\n\n"
            "▸ <b>Команды:</b>\n"
            "  /search — поиск на SoundCloud\n"
            "  /mp3tools — редактор MP3 тегов\n"
            "  /history — история загрузок\n"
            "  /lang — сменить язык\n\n"
            "▸ <b>Поддерживаемые ссылки:</b>\n"
            "  • <code>soundcloud.com/...</code>\n"
            "  • <code>tiktok.com/...</code>\n"
            "  • <code>pinterest.com/...</code>\n"
            "  • <code>pin.it/...</code>"
        ),
        
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
        
        # Rate limit
        "rate_limit": "⏳ Подожди минуту",
        
        # Search
        "search_usage": "🔍 <code>/search название</code>",
        "searching": "🔍",
        "no_results": "Ничего не найдено",
        "search_error": "❌ Ошибка поиска",
        
        # History
        "history_empty": "История пуста",
        "history_title": "📜 <b>История:</b>",
        
        # Stats
        "stats_title": "📊 <b>Статистика</b>",
    },
    "en": {
        # Start & Help
        "welcome": (
            "✨ <b>Media Downloader</b>\n\n"
            "🎵 Download media from popular platforms\n\n"
            "🌐 Choose language / Выбери язык:"
        ),
        "start": (
            "🚀 <b>Ready to go!</b>\n\n"
            "📎 Just send a link:\n\n"
            "  🟠 <b>SoundCloud</b> → music\n"
            "  🎵 <b>TikTok</b> → video & photos\n"
            "  📌 <b>Pinterest</b> → photos & video\n\n"
            "💡 <i>Or use buttons below</i>"
        ),
        "help": (
            "📖 <b>Help</b>\n\n"
            "▸ <b>Commands:</b>\n"
            "  /search — search on SoundCloud\n"
            "  /mp3tools — MP3 tag editor\n"
            "  /history — download history\n"
            "  /lang — change language\n\n"
            "▸ <b>Supported links:</b>\n"
            "  • <code>soundcloud.com/...</code>\n"
            "  • <code>tiktok.com/...</code>\n"
            "  • <code>pinterest.com/...</code>\n"
            "  • <code>pin.it/...</code>"
        ),
        
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
        
        # Rate limit
        "rate_limit": "⏳ Wait a minute",
        
        # Search
        "search_usage": "🔍 <code>/search query</code>",
        "searching": "🔍",
        "no_results": "No results found",
        "search_error": "❌ Search error",
        
        # History
        "history_empty": "History is empty",
        "history_title": "📜 <b>History:</b>",
        
        # Stats
        "stats_title": "📊 <b>Stats</b>",
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
