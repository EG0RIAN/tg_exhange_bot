from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from src.keyboards import main_menu, get_trading_pairs_keyboard, get_rates_back_keyboard, get_cities_keyboard
from src.i18n import _, detect_user_lang
from src.db import get_pg_pool
from src.services.content import format_rates_display, get_trading_pairs, get_rate_tiers_for_pair
from src.services.faq import get_categories
import logging

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

@router.callback_query(F.data.startswith("city:"))
async def show_city_rates(callback: CallbackQuery, state: FSMContext):
    # Проверяем - если пользователь в FSM создания заявки, не обрабатываем здесь
    current_state = await state.get_state()
    if current_state is not None:
        # Пользователь в процессе создания заявки, пропускаем
        return
    
    city_code = callback.data.split(":", 1)[1]
    
    # Если выбрали "Остальные города", показываем их список
    if city_code == "other":
        from src.keyboards import get_all_cities_keyboard
        await callback.message.edit_text("🌍 Выберите город:", reply_markup=await get_all_cities_keyboard())
        return
    
    # Получаем название города из БД
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        city_row = await conn.fetchrow("SELECT name FROM cities WHERE code = $1 AND enabled = true", city_code)
        city_name = city_row['name'] if city_row else city_code
    
    # Сохраняем, был ли это приоритетный город
    priority_cities = ['moscow', 'spb', 'krasnodar', 'rostov']
    is_priority = city_code in priority_cities
    await state.update_data(rates_from_priority=is_priority)
    
    # Используем унифицированный сервис
    from src.services.client_rates import format_rates_for_display
    
    rates_text = await format_rates_for_display(city_code, city_name)
    
    await callback.message.edit_text(
        rates_text,
        parse_mode="Markdown",
        reply_markup=get_rates_back_keyboard()
    )

@router.callback_query(F.data == "rates_back")
async def rates_back(callback: CallbackQuery, state: FSMContext):
    # Проверяем, откуда пришел пользователь
    data = await state.get_data()
    from_priority = data.get('rates_from_priority', True)
    
    if from_priority:
        # Возвращаемся к приоритетным городам
        await callback.message.edit_text("🌍 Выберите ваш город для просмотра курсов:", reply_markup=await get_cities_keyboard())
    else:
        # Возвращаемся к списку всех городов
        from src.keyboards import get_all_cities_keyboard
        await callback.message.edit_text("🌍 Выберите город:", reply_markup=await get_all_cities_keyboard())
    
    # Очищаем флаг
    await state.update_data(rates_from_priority=None)

@router.callback_query(F.data == "back_to_priority_cities")
async def back_to_priority_cities(callback: CallbackQuery):
    """Вернуться к приоритетным городам"""
    await callback.message.edit_text("🌍 Выберите ваш город для просмотра курсов:", reply_markup=await get_cities_keyboard())

# Обработчик менеджера перенесен в src/handlers/livechat.py

# Обработчик настроек перенесен в src/handlers/settings.py

@router.message(Command("health"))
async def cmd_health(message: Message):
    await message.answer("✅ Bot is alive!") 