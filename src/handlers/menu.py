from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from src.keyboards import main_menu, get_trading_pairs_keyboard, get_rates_back_keyboard, get_cities_keyboard
from src.i18n import _, detect_user_lang
from src.db import get_pg_pool
from src.services.content import format_rates_display, get_pairs_for_fsm, get_trading_pairs, get_rate_tiers_for_pair
from src.services.faq import get_categories
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "/start")
async def menu_start(message: Message):
    pool = await get_pg_pool()
    lang = await detect_user_lang(message.from_user, db_pool=pool)
    await message.answer(_("start_message", lang=lang), reply_markup=main_menu)

# Обработчик FAQ перенесен в src/handlers/faq.py

@router.message(F.text == "💱 Курсы")
async def menu_rates(message: Message):
    await message.answer("🌍 Выберите ваш город для просмотра курсов:", reply_markup=await get_cities_keyboard())

@router.callback_query(F.data.startswith("city:"))
async def show_city_rates(callback: CallbackQuery):
    city_code = callback.data.split(":", 1)[1]
    
    # Получаем название города из БД
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        city_row = await conn.fetchrow("SELECT name FROM cities WHERE code = $1 AND enabled = true", city_code)
        city_name = city_row['name'] if city_row else city_code
    
    # Используем унифицированный сервис
    from src.services.client_rates import format_rates_for_display
    
    rates_text = await format_rates_for_display(city_code, city_name)
    
    await callback.message.edit_text(
        rates_text,
        parse_mode="Markdown",
        reply_markup=get_rates_back_keyboard()
    )

@router.callback_query(F.data == "rates_back")
async def rates_back(callback: CallbackQuery):
    await callback.message.edit_text("🌍 Выберите ваш город для просмотра курсов:", reply_markup=await get_cities_keyboard())

# Обработчик менеджера перенесен в src/handlers/livechat.py

# Обработчик настроек перенесен в src/handlers/settings.py

@router.message(Command("health"))
async def cmd_health(message: Message):
    await message.answer("✅ Bot is alive!") 