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
from app.i18n import t


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


def get_mp3tools_keyboard(file_id: str, user_id: int = 0) -> InlineKeyboardBuilder:
    """Keyboard after SoundCloud download."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t(user_id, "btn_tags"), callback_data=MP3ToolsCallback(action="edit", file_id=file_id))
    builder.button(text=t(user_id, "btn_cover"), callback_data=MP3ToolsCallback(action="album_art", file_id=file_id))
    builder.button(text=t(user_id, "btn_done"), callback_data=MP3ToolsCallback(action="save", file_id=file_id))
    builder.button(text=t(user_id, "btn_cancel"), callback_data=MP3ToolsCallback(action="cancel", file_id=file_id))
    builder.adjust(2, 2)
    return builder


def get_back_keyboard(file_id: str, user_id: int = 0) -> InlineKeyboardBuilder:
    """Back button keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t(user_id, "btn_back"), callback_data=MP3ToolsCallback(action="back", file_id=file_id))
    return builder


@router.message(Command("mp3tools"))
async def cmd_mp3tools(message: Message, state: FSMContext) -> None:
    """Start MP3 Tools - ask for MP3 file."""
    await state.set_state(MP3States.waiting_for_mp3)
    await message.answer(t(message.from_user.id, "mp3tools_send"))


@router.message(MP3States.waiting_for_mp3, F.audio)
async def handle_mp3_upload(message: Message, state: FSMContext) -> None:
    """Handle MP3 file upload."""
    user_id = message.from_user.id
    if not message.audio.mime_type or "audio" not in message.audio.mime_type:
        await message.answer(t(user_id, "mp3tools_send_file"))
        return
    
    status = await message.answer(t(user_id, "loading"))
    
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
        f"{tags.title or 'Track'} — {tags.artist or 'Artist'}",
        reply_markup=get_mp3tools_keyboard(file_id, user_id).as_markup()
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Cancel current operation."""
    await state.clear()
    await message.answer(t(message.from_user.id, "cancelled"))


# ============ BACK ============

@router.callback_query(MP3ToolsCallback.filter(F.action == "back"))
async def handle_back(callback: CallbackQuery, callback_data: MP3ToolsCallback, state: FSMContext) -> None:
    """Go back to main menu."""
    await state.clear()
    
    user_id = callback.from_user.id
    file_path = _file_storage.get(callback_data.file_id)
    if not file_path:
        await callback.answer(t(user_id, "file_not_found"), show_alert=True)
        return
    
    if not file_path.exists():
        await callback.answer(t(user_id, "file_deleted"), show_alert=True)
        return
    
    tags = await mp3tools.get_tags(file_path)
    
    await callback.answer()
    
    chat_id = callback.message.chat.id
    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.bot.send_message(
        chat_id=chat_id,
        text=f"{tags.title or 'Track'} — {tags.artist or 'Artist'}",
        reply_markup=get_mp3tools_keyboard(callback_data.file_id, user_id).as_markup()
    )


# ============ EDIT: Title -> Artist ============

@router.callback_query(MP3ToolsCallback.filter(F.action == "edit"))
async def handle_edit(callback: CallbackQuery, callback_data: MP3ToolsCallback, state: FSMContext) -> None:
    """Start editing - ask for title."""
    await state.set_state(MP3States.waiting_for_title)
    await state.update_data(file_id=callback_data.file_id)
    
    user_id = callback.from_user.id
    await callback.answer()
    await callback.message.edit_text(
        t(user_id, "enter_title"),
        reply_markup=get_back_keyboard(callback_data.file_id, user_id).as_markup()
    )


@router.message(MP3States.waiting_for_title, F.text)
async def handle_title_input(message: Message, state: FSMContext) -> None:
    """Process title input, ask for artist."""
    user_id = message.from_user.id
    if message.text.startswith("/"):
        await state.clear()
        await message.answer(t(user_id, "cancelled"))
        return
    
    title = message.text.strip()
    await state.update_data(title=title)
    await state.set_state(MP3States.waiting_for_artist)
    
    data = await state.get_data()
    file_id = data.get("file_id")
    await message.answer(t(user_id, "enter_artist"), reply_markup=get_back_keyboard(file_id, user_id).as_markup())


@router.message(MP3States.waiting_for_artist, F.text)
async def handle_artist_input(message: Message, state: FSMContext) -> None:
    """Process artist input, save tags."""
    user_id = message.from_user.id
    if message.text.startswith("/"):
        await state.clear()
        await message.answer(t(user_id, "cancelled"))
        return
    
    data = await state.get_data()
    file_id = data.get("file_id")
    title = data.get("title")
    artist = message.text.strip()
    
    file_path = _file_storage.get(file_id)
    
    if not file_path or not file_path.exists():
        await state.clear()
        await message.answer(t(user_id, "file_not_found"))
        return
    
    tags = MP3Tags(title=title, artist=artist)
    success = await mp3tools.set_tags(file_path, tags)
    
    await state.clear()
    
    if success:
        await message.answer(
            f"{t(user_id, 'tags_saved')} {title} — {artist}",
            reply_markup=get_mp3tools_keyboard(file_id, user_id).as_markup()
        )
    else:
        await message.answer(
            t(user_id, "error"),
            reply_markup=get_mp3tools_keyboard(file_id, user_id).as_markup()
        )


# ============ ALBUM ART ============

@router.callback_query(MP3ToolsCallback.filter(F.action == "album_art"))
async def handle_album_art(callback: CallbackQuery, callback_data: MP3ToolsCallback, state: FSMContext) -> None:
    """Show album art options."""
    user_id = callback.from_user.id
    file_path = _file_storage.get(callback_data.file_id)
    
    if not file_path or not file_path.exists():
        await callback.answer(t(user_id, "file_not_found"), show_alert=True)
        return
    
    await state.set_state(MP3States.waiting_for_art)
    await state.update_data(file_id=callback_data.file_id)
    
    art_data = await mp3tools.get_album_art(file_path)
    
    await callback.answer()
    
    if art_data:
        await callback.message.answer_photo(
            photo=BufferedInputFile(art_data, filename="cover.jpg"),
            caption=t(user_id, "send_new_cover"),
            reply_markup=get_back_keyboard(callback_data.file_id, user_id).as_markup()
        )
        await callback.message.delete()
    else:
        await callback.message.edit_text(
            t(user_id, "send_cover"),
            reply_markup=get_back_keyboard(callback_data.file_id, user_id).as_markup()
        )


@router.message(MP3States.waiting_for_art, F.photo)
async def handle_art_upload(message: Message, state: FSMContext) -> None:
    """Handle album art upload."""
    user_id = message.from_user.id
    data = await state.get_data()
    file_id = data.get("file_id")
    file_path = _file_storage.get(file_id)
    
    if not file_path or not file_path.exists():
        await state.clear()
        await message.answer(t(user_id, "file_not_found"))
        return
    
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    
    from io import BytesIO
    photo_bytes = BytesIO()
    await message.bot.download_file(file.file_path, photo_bytes)
    
    success = await mp3tools.set_album_art(file_path, photo_bytes.getvalue())
    
    await state.clear()
    
    if success:
        await message.answer(t(user_id, "cover_updated"), reply_markup=get_mp3tools_keyboard(file_id, user_id).as_markup())
    else:
        await message.answer(t(user_id, "error"), reply_markup=get_mp3tools_keyboard(file_id, user_id).as_markup())


@router.message(MP3States.waiting_for_art, Command("delete_art"))
async def handle_delete_art(message: Message, state: FSMContext) -> None:
    """Delete album art."""
    user_id = message.from_user.id
    data = await state.get_data()
    file_id = data.get("file_id")
    file_path = _file_storage.get(file_id)
    
    if not file_path or not file_path.exists():
        await state.clear()
        await message.answer(t(user_id, "file_not_found"))
        return
    
    success = await mp3tools.delete_album_art(file_path)
    
    await state.clear()
    
    if success:
        await message.answer(t(user_id, "cover_updated"), reply_markup=get_mp3tools_keyboard(file_id, user_id).as_markup())
    else:
        await message.answer(t(user_id, "error"), reply_markup=get_mp3tools_keyboard(file_id, user_id).as_markup())


# ============ SAVE & CANCEL ============

@router.callback_query(MP3ToolsCallback.filter(F.action == "save"))
async def handle_save(callback: CallbackQuery, callback_data: MP3ToolsCallback) -> None:
    """Save and send the edited MP3."""
    user_id = callback.from_user.id
    file_path = _file_storage.pop(callback_data.file_id, None)
    
    if not file_path or not file_path.exists():
        await callback.answer(t(user_id, "file_not_found"), show_alert=True)
        return
    
    await callback.answer()
    await callback.message.edit_text(t(user_id, "sending"))
    
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
    await callback.message.delete()
