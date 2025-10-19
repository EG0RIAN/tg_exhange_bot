from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from src.i18n import _
from src.db import get_pg_pool

router = Router()

def get_language_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора языка"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
        ]
    )

@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message, state: FSMContext):
    await message.answer("Выберите язык / Choose language:", reply_markup=get_language_keyboard())

@router.callback_query(F.data.startswith("lang_"))
async def settings_set_lang(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]  # lang_ru -> ru, lang_en -> en
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET lang=$1 WHERE tg_id=$2", lang, callback.from_user.id)
    
    await callback.message.edit_text(_("language_set", lang=lang))
    await callback.answer() 