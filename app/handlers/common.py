from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.i18n import t, set_user_lang, detect_language
from app.database import db

router = Router(name="common")


class LangCallback(CallbackData, prefix="lang"):
    code: str


def get_main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    """Main reply keyboard with useful buttons."""
    lang = t(user_id, "lang_changed")
    is_ru = "Русский" in lang
    
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Поиск" if is_ru else "🔍 Search")],
            [
                KeyboardButton(text="📜 История" if is_ru else "📜 History"),
                KeyboardButton(text="📊 Статистика" if is_ru else "📊 Stats")
            ],
            [
                KeyboardButton(text="🎵 MP3 Tools"),
                KeyboardButton(text="🌐 Язык" if is_ru else "🌐 Language")
            ]
        ],
        resize_keyboard=True
    )


def get_lang_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 Русский", callback_data=LangCallback(code="ru"))
    builder.button(text="🇬🇧 English", callback_data=LangCallback(code="en"))
    builder.adjust(2)
    return builder


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command - auto-detect language or ask."""
    user_id = message.from_user.id
    
    # Auto-detect from Telegram settings and save to DB
    detected = detect_language(message.from_user.language_code)
    await db.set_user_lang(user_id, detected)
    set_user_lang(user_id, detected)  # Also cache in memory
    
    await message.answer(
        t(user_id, "welcome"),
        reply_markup=get_lang_keyboard().as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(LangCallback.filter())
async def handle_lang_choice(callback: CallbackQuery, callback_data: LangCallback) -> None:
    """Handle language selection."""
    user_id = callback.from_user.id
    await db.set_user_lang(user_id, callback_data.code)
    set_user_lang(user_id, callback_data.code)  # Also cache in memory
    
    await callback.answer(t(user_id, "lang_changed"))
    await callback.message.edit_text(
        t(user_id, "start"),
        parse_mode="HTML"
    )
    # Send keyboard
    await callback.message.answer("⌨️", reply_markup=get_main_keyboard(user_id))


@router.message(Command("lang"))
async def cmd_lang(message: Message) -> None:
    """Change language."""
    await message.answer(
        "🌐",
        reply_markup=get_lang_keyboard().as_markup()
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    user_id = message.from_user.id
    await message.answer(
        t(user_id, "help"),
        parse_mode="HTML"
    )


# ============ KEYBOARD BUTTON HANDLERS ============

@router.message(lambda m: m.text in ["🔍 Поиск", "🔍 Search"])
async def btn_search(message: Message, state) -> None:
    from app.handlers.search import SearchStates
    user_id = message.from_user.id
    lang = t(user_id, "lang_changed")
    is_ru = "Русский" in lang
    
    if is_ru:
        text = "🔎 <b>Поиск</b>\n\nИсточник: 🟠 SoundCloud\n\nВведи запрос:"
    else:
        text = "🔎 <b>Search</b>\n\nSource: 🟠 SoundCloud\n\nEnter your query:"
    
    await state.set_state(SearchStates.waiting_query)
    await message.answer(text, parse_mode="HTML")


@router.message(lambda m: m.text in ["📜 История", "📜 History"])
async def btn_history(message: Message) -> None:
    from app.handlers.history import cmd_history
    await cmd_history(message)


@router.message(lambda m: m.text in ["📊 Статистика", "📊 Stats"])
async def btn_stats(message: Message) -> None:
    from app.handlers.history import cmd_stats
    await cmd_stats(message)


@router.message(lambda m: m.text == "🎵 MP3 Tools")
async def btn_mp3tools(message: Message) -> None:
    await message.answer(t(message.from_user.id, "mp3tools_send"))


@router.message(lambda m: m.text in ["🌐 Язык", "🌐 Language"])
async def btn_lang(message: Message) -> None:
    await message.answer("🌐", reply_markup=get_lang_keyboard().as_markup())
