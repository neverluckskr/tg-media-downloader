import uuid
from pathlib import Path

from aiogram import Router, F
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
    waiting_for_title = State()
    waiting_for_artist = State()
    waiting_for_art = State()


# Storage for file paths (in production use Redis)
_file_storage: dict[str, Path] = {}


def get_mp3tools_keyboard(file_id: str) -> InlineKeyboardBuilder:
    """Keyboard after SoundCloud download."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Редактировать", callback_data=MP3ToolsCallback(action="edit", file_id=file_id))
    builder.button(text="🖼 Album Art", callback_data=MP3ToolsCallback(action="album_art", file_id=file_id))
    builder.button(text="💾 Сохранить", callback_data=MP3ToolsCallback(action="save", file_id=file_id))
    builder.button(text="❌ Отмена", callback_data=MP3ToolsCallback(action="cancel", file_id=file_id))
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
    await state.clear()
    
    # Get current tags
    tags = await mp3tools.get_tags(file_path)
    
    await status.edit_text(
        f"🎵 <b>MP3 Tools</b>\n\n"
        f"<b>Title:</b> {tags.title or '—'}\n"
        f"<b>Artist:</b> {tags.artist or '—'}\n\n"
        f"Выбери действие:",
        reply_markup=get_mp3tools_keyboard(file_id).as_markup(),
        parse_mode="HTML"
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Cancel current operation."""
    await state.clear()
    await message.answer("❌ Отменено.")


# ============ EDIT: Title -> Artist ============

@router.callback_query(MP3ToolsCallback.filter(F.action == "edit"))
async def handle_edit(callback: CallbackQuery, callback_data: MP3ToolsCallback, state: FSMContext) -> None:
    """Start editing - ask for title."""
    await state.set_state(MP3States.waiting_for_title)
    await state.update_data(file_id=callback_data.file_id)
    
    await callback.answer()
    await callback.message.edit_text(
        "✏️ <b>Редактирование</b>\n\n"
        "Напиши <b>название трека</b>:\n"
        "(например: Карты)\n\n"
        "/cancel — отмена",
        parse_mode="HTML"
    )


@router.message(MP3States.waiting_for_title, F.text)
async def handle_title_input(message: Message, state: FSMContext) -> None:
    """Process title input, ask for artist."""
    if message.text.startswith("/"):
        await state.clear()
        await message.answer("❌ Отменено.")
        return
    
    title = message.text.strip()
    await state.update_data(title=title)
    await state.set_state(MP3States.waiting_for_artist)
    
    await message.answer(
        f"✅ Название: <b>{title}</b>\n\n"
        "Теперь напиши <b>автора</b>:\n"
        "(например: GATASKI & Whole Lotta Swag)\n\n"
        "/cancel — отмена",
        parse_mode="HTML"
    )


@router.message(MP3States.waiting_for_artist, F.text)
async def handle_artist_input(message: Message, state: FSMContext) -> None:
    """Process artist input, save tags."""
    if message.text.startswith("/"):
        await state.clear()
        await message.answer("❌ Отменено.")
        return
    
    data = await state.get_data()
    file_id = data.get("file_id")
    title = data.get("title")
    artist = message.text.strip()
    
    file_path = _file_storage.get(file_id)
    
    if not file_path or not file_path.exists():
        await state.clear()
        await message.answer("❌ Файл не найден. Начни заново: /mp3tools")
        return
    
    # Save tags
    tags = MP3Tags(title=title, artist=artist)
    success = await mp3tools.set_tags(file_path, tags)
    
    await state.clear()
    
    if success:
        await message.answer(
            f"✅ Теги сохранены!\n\n"
            f"<b>Title:</b> {title}\n"
            f"<b>Artist:</b> {artist}\n\n"
            f"Выбери действие:",
            reply_markup=get_mp3tools_keyboard(file_id).as_markup(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ Ошибка при сохранении тегов.",
            reply_markup=get_mp3tools_keyboard(file_id).as_markup()
        )


# ============ ALBUM ART ============

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
            "Отправь фото для установки\n"
            "/cancel — отмена",
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
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    
    from io import BytesIO
    photo_bytes = BytesIO()
    await message.bot.download_file(file.file_path, photo_bytes)
    
    success = await mp3tools.set_album_art(file_path, photo_bytes.getvalue())
    
    await state.clear()
    
    if success:
        await message.answer(
            "✅ Обложка обновлена!",
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
            "✅ Обложка удалена!",
            reply_markup=get_mp3tools_keyboard(file_id).as_markup()
        )
    else:
        await message.answer(
            "❌ Ошибка при удалении обложки.",
            reply_markup=get_mp3tools_keyboard(file_id).as_markup()
        )


# ============ SAVE & CANCEL ============

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
        thumb_data = await mp3tools.get_thumbnail_for_telegram(file_path)
        
        audio_file = FSInputFile(
            path=file_path,
            filename=f"{tags.artist or 'Unknown'} - {tags.title or 'Unknown'}.mp3"
        )
        
        # Save resized thumbnail to temp file
        thumbnail = None
        if thumb_data:
            thumb_path = file_path.parent / f"{callback_data.file_id}_thumb.jpg"
            thumb_path.write_bytes(thumb_data)
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
    await callback.message.edit_text("❌ Отменено. Файл удалён.")
