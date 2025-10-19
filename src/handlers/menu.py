from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from src.keyboards import main_menu
from src.i18n import _, detect_user_lang
from src.db import get_pg_pool
import logging
from src.utils.logger import log_handler, log_user_action

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start - сбрасывает FSM и возвращает в главное меню"""
    await state.clear()
    pool = await get_pg_pool()
    lang = await detect_user_lang(message.from_user, db_pool=pool)
    await message.answer(_("start_message", lang=lang), reply_markup=main_menu)

@router.message(F.text == "/start")
async def menu_start(message: Message, state: FSMContext):
    """Обработчик текста /start"""
    await state.clear()
    pool = await get_pg_pool()
    lang = await detect_user_lang(message.from_user, db_pool=pool)
    await message.answer(_("start_message", lang=lang), reply_markup=main_menu)

# Обработчик FAQ перенесен в src/handlers/faq.py

@router.message(F.text == "👨‍💼 Связаться с менеджером")
async def menu_contact_manager(message: Message):
    """Обработчик текстовой кнопки 'Связаться с менеджером' из главного меню"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    contact_message = (
        "💬 Напишите нам для консультации\n\n"
        "Мы всегда рады помочь!"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📱 Написать менеджеру", url="https://t.me/btc_otc")]
        ]
    )
    
    await message.answer(contact_message, reply_markup=keyboard)

# УДАЛЕНО: Функционал просмотра курсов для города
# Ранее здесь были обработчики:
# - show_city_rates
# - rates_back  
# - back_to_priority_cities

# Обработчик менеджера перенесен в src/handlers/livechat.py
# Обработчик настроек перенесен в src/handlers/settings.py

@router.message(Command("health"))
async def cmd_health(message: Message):
    await message.answer("✅ Bot is alive!") 