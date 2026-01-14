from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.i18n import t, set_user_lang, detect_language
from app.database import db

router = Router(name="common")


class LangCallback(CallbackData, prefix="lang"):
    code: str


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
