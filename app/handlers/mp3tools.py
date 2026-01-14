import uuid
from pathlib import Path
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile, BufferedInputFile
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import config
from app.services.mp3tools import mp3tools, MP3Tags


router = Router(name="mp3tools")


class MP3ToolsCallback(CallbackData, prefix="mp3"):
    action: str
    file_id: str


class MP3States(StatesGroup):
    waiting_for_mp3 = State()
    waiting_for_tags = State()
    waiting_for_art = State()


# Storage for file paths (in production use Redis)
_file_storage: dict[str, Path] = {}


def get_mp3tools_keyboard(file_id: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Tag Editor", callback_data=MP3ToolsCallback(action="edit_tags", file_id=file_id))
    builder.button(text="🖼 Album Art", callback_data=MP3ToolsCallback(action="album_art", file_id=file_id))
    builder.button(text="💾 Save & Send", callback_data=MP3ToolsCallback(action="save", file_id=file_id))
    builder.button(text="❌ Cancel", callback_data=MP3ToolsCallback(action="cancel", file_id=file_id))
    builder.adjust(2, 2)
    return builder


@router.message(Command("mp3tools"))
async def cmd_mp3tools(message: Message, state: FSMContext) -> None:
    """Start MP3 Tools - ask for MP3 file."""
    await state.set_state(MP3States.waiting_for_mp3)
    await message.answer(
        "🎵 <b>MP3 Tools</b>\n\n"
        "Отправь мне MP3 файл для редактирования.",
        parse_mode="HTML"
    )


@router.message(MP3States.waiting_for_mp3, F.audio)
async def handle_mp3_upload(message: Message, state: FSMContext) -> None:
    """Handle MP3 file upload."""
    if not message.audio.mime_type or "audio" not in message.audio.mime_type:
        await message.answer("❌ Отправь MP3 файл.")
        return
    
    status = await message.answer("⏳ Загружаю файл...")
    
    # Download file
    file_id = uuid.uuid4().hex[:8]
    file_path = config.DOWNLOAD_DIR / f"mp3tools_{file_id}.mp3"
    config.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    file = await message.bot.get_file(message.audio.file_id)
    await message.bot.download_file(file.file_path, file_path)
    
    _file_storage[file_id] = file_path
    await state.update_data(file_id=file_id)
    await state.clear()
    
    # Get current tags
    tags = await mp3tools.get_tags(file_path)
    
    tags_text = (
        f"<b>Текущие теги:</b>\n"
        f"• Title: {tags.title or '—'}\n"
        f"• Artist: {tags.artist or '—'}\n"
        f"• Album: {tags.album or '—'}\n"
        f"• Genre: {tags.genre or '—'}\n"
        f"• Date: {tags.date or '—'}\n"
        f"• Track: {tags.track or '—'}"
    )
    
    await status.edit_text(
        f"🎵 <b>MP3 Tools</b>\n\n{tags_text}\n\nВыбери действие:",
        reply_markup=get_mp3tools_keyboard(file_id).as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(MP3ToolsCallback.filter(F.action == "edit_tags"))
async def handle_edit_tags(callback: CallbackQuery, callback_data: MP3ToolsCallback, state: FSMContext) -> None:
    """Start tag editing."""
    await state.set_state(MP3States.waiting_for_tags)
    await state.update_data(file_id=callback_data.file_id)
    
    await callback.answer()
    await callback.message.edit_text(
        "✏️ <b>Tag Editor</b>\n\n"
        "Отправь теги в формате:\n\n"
        "<b>Простой:</b> <code>title:artist</code>\n"
        "Пример: <code>Be My Lover:Inna</code>\n\n"
        "<b>Расширенный:</b>\n"
        "<code>title:Vaathi Coming\n"
        "artist:Anirudh Ravichander\n"
        "album:Master\n"
        "genre:Rock\n"
        "date:2020\n"
        "track:1</code>\n\n"
        "Или /cancel для отмены.",
        parse_mode="HTML"
    )


@router.message(MP3States.waiting_for_tags, F.text)
async def handle_tags_input(message: Message, state: FSMContext) -> None:
    """Process tags input."""
    if message.text.startswith("/"):
        await state.clear()
        await message.answer("❌ Отменено.")
        return
    
    data = await state.get_data()
    file_id = data.get("file_id")
    file_path = _file_storage.get(file_id)
    
    if not file_path or not file_path.exists():
        await state.clear()
        await message.answer("❌ Файл не найден. Начни заново: /mp3tools")
        return
    
    tags = mp3tools.parse_tags_input(message.text)
    success = await mp3tools.set_tags(file_path, tags)
    
    await state.clear()
    
    if success:
        # Show updated tags
        updated_tags = await mp3tools.get_tags(file_path)
        tags_text = (
            f"<b>Обновленные теги:</b>\n"
            f"• Title: {updated_tags.title or '—'}\n"
            f"• Artist: {updated_tags.artist or '—'}\n"
            f"• Album: {updated_tags.album or '—'}\n"
            f"• Genre: {updated_tags.genre or '—'}\n"
            f"• Date: {updated_tags.date or '—'}\n"
            f"• Track: {updated_tags.track or '—'}"
        )
        await message.answer(
            f"✅ Теги обновлены!\n\n{tags_text}\n\nВыбери действие:",
            reply_markup=get_mp3tools_keyboard(file_id).as_markup(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ Ошибка при сохранении тегов.",
            reply_markup=get_mp3tools_keyboard(file_id).as_markup()
        )


@router.callback_query(MP3ToolsCallback.filter(F.action == "album_art"))
async def handle_album_art(callback: CallbackQuery, callback_data: MP3ToolsCallback, state: FSMContext) -> None:
    """Show album art options."""
    file_path = _file_storage.get(callback_data.file_id)
    
    if not file_path or not file_path.exists():
        await callback.answer("Файл не найден", show_alert=True)
        return
    
    await state.set_state(MP3States.waiting_for_art)
    await state.update_data(file_id=callback_data.file_id)
    
    art_data = await mp3tools.get_album_art(file_path)
    
    await callback.answer()
    
    if art_data:
        await callback.message.answer_photo(
            photo=BufferedInputFile(art_data, filename="cover.jpg"),
            caption="🖼 <b>Текущая обложка</b>\n\n"
                    "Отправь новое фото для замены\n"
                    "/delete_art — удалить обложку\n"
                    "/cancel — отмена",
            parse_mode="HTML"
        )
        await callback.message.delete()
    else:
        await callback.message.edit_text(
            "🖼 <b>Album Art</b>\n\n"
            "Обложка отсутствует.\n\n"
            "Отправь фото для установки обложки\n"
            "Или /cancel для отмены.",
            parse_mode="HTML"
        )


@router.message(MP3States.waiting_for_art, F.photo)
async def handle_art_upload(message: Message, state: FSMContext) -> None:
    """Handle album art upload."""
    data = await state.get_data()
    file_id = data.get("file_id")
    file_path = _file_storage.get(file_id)
    
    if not file_path or not file_path.exists():
        await state.clear()
        await message.answer("❌ Файл не найден. Начни заново: /mp3tools")
        return
    
    # Download photo
    photo = message.photo[-1]  # Largest size
    file = await message.bot.get_file(photo.file_id)
    
    from io import BytesIO
    photo_bytes = BytesIO()
    await message.bot.download_file(file.file_path, photo_bytes)
    
    success = await mp3tools.set_album_art(file_path, photo_bytes.getvalue())
    
    await state.clear()
    
    if success:
        await message.answer(
            "✅ Обложка обновлена!\n\nВыбери действие:",
            reply_markup=get_mp3tools_keyboard(file_id).as_markup()
        )
    else:
        await message.answer(
            "❌ Ошибка при сохранении обложки.",
            reply_markup=get_mp3tools_keyboard(file_id).as_markup()
        )


@router.message(MP3States.waiting_for_art, Command("delete_art"))
async def handle_delete_art(message: Message, state: FSMContext) -> None:
    """Delete album art."""
    data = await state.get_data()
    file_id = data.get("file_id")
    file_path = _file_storage.get(file_id)
    
    if not file_path or not file_path.exists():
        await state.clear()
        await message.answer("❌ Файл не найден. Начни заново: /mp3tools")
        return
    
    success = await mp3tools.delete_album_art(file_path)
    
    await state.clear()
    
    if success:
        await message.answer(
            "✅ Обложка удалена!\n\nВыбери действие:",
            reply_markup=get_mp3tools_keyboard(file_id).as_markup()
        )
    else:
        await message.answer(
            "❌ Ошибка при удалении обложки.",
            reply_markup=get_mp3tools_keyboard(file_id).as_markup()
        )


@router.callback_query(MP3ToolsCallback.filter(F.action == "save"))
async def handle_save(callback: CallbackQuery, callback_data: MP3ToolsCallback) -> None:
    """Save and send the edited MP3."""
    file_path = _file_storage.pop(callback_data.file_id, None)
    
    if not file_path or not file_path.exists():
        await callback.answer("Файл не найден", show_alert=True)
        return
    
    await callback.answer()
    await callback.message.edit_text("⏳ Отправляю файл...")
    
    thumb_path = None
    try:
        tags = await mp3tools.get_tags(file_path)
        art_data = await mp3tools.get_album_art(file_path)
        
        audio_file = FSInputFile(
            path=file_path,
            filename=f"{tags.artist or 'Unknown'} - {tags.title or 'Unknown'}.mp3"
        )
        
        # Save thumbnail to temp file (Telegram works better with file input)
        thumbnail = None
        if art_data:
            thumb_path = file_path.parent / f"{callback_data.file_id}_thumb.jpg"
            thumb_path.write_bytes(art_data)
            thumbnail = FSInputFile(path=thumb_path)
        
        await callback.message.answer_audio(
            audio=audio_file,
            title=tags.title,
            performer=tags.artist,
            thumbnail=thumbnail
        )
        await callback.message.delete()
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {str(e)[:100]}")
    finally:
        if file_path.exists():
            file_path.unlink()
        if thumb_path and thumb_path.exists():
            thumb_path.unlink()


@router.callback_query(MP3ToolsCallback.filter(F.action == "cancel"))
async def handle_cancel(callback: CallbackQuery, callback_data: MP3ToolsCallback, state: FSMContext) -> None:
    """Cancel and cleanup."""
    file_path = _file_storage.pop(callback_data.file_id, None)
    
    if file_path and file_path.exists():
        file_path.unlink()
    
    await state.clear()
    await callback.answer()
    await callback.message.edit_text("❌ Отменено.")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Cancel current operation."""
    data = await state.get_data()
    file_id = data.get("file_id")
    
    if file_id:
        file_path = _file_storage.pop(file_id, None)
        if file_path and file_path.exists():
            file_path.unlink()
    
    await state.clear()
    await message.answer("❌ Отменено.")
