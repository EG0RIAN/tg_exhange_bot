"""
Обработчики для пути "Купить USDT"
Клиент покупает USDT за наличные
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter, Command

from src.fsm import BuyUSDTStates
from src.keyboards import (
    get_priority_cities_keyboard,
    get_all_cities_keyboard,
    get_currencies_keyboard,
    get_amount_keyboard_v2,
    get_confirm_keyboard_v2,
    get_rate_confirm_keyboard,
    main_menu
)
from src.db import get_pg_pool
import logging

router = Router()
logger = logging.getLogger(__name__)

# Менеджер по умолчанию
MANAGER_USERNAME = "@btc_otc"


# ============================================================================
# Универсальный обработчик /start для сброса состояния
# ============================================================================

@router.message(Command("start"), StateFilter(BuyUSDTStates))
async def reset_to_start(message: Message, state: FSMContext):
    """Сброс состояния и возврат в главное меню"""
    await state.clear()
    from src.i18n import _, detect_user_lang
    pool = await get_pg_pool()
    lang = await detect_user_lang(message.from_user, db_pool=pool)
    await message.answer(_("start_message", lang=lang), reply_markup=main_menu)


# ============================================================================
# Шаг 1: Начало - кнопка "💵 Купить USDT" - Ввод суммы
# ============================================================================

@router.message(F.text == "💵 Купить USDT")
async def start_buy_usdt(message: Message, state: FSMContext):
    """Начало пути покупки USDT - ввод суммы"""
    await state.clear()
    await state.set_state(BuyUSDTStates.enter_amount)
    
    await message.answer(
        "💰 <b>Введите Сумму USDT:</b>\n\n"
        "Например: 100 или 1500.50",
        reply_markup=get_amount_keyboard_v2(),
        parse_mode="HTML"
    )


# ============================================================================
# Шаг 2: Ввод суммы
# ============================================================================



@router.message(BuyUSDTStates.enter_amount, F.text)
async def enter_custom_amount(message: Message, state: FSMContext):
    """Ввод произвольной суммы"""
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            await message.answer("⚠️ Сумма должна быть больше нуля. Попробуйте еще раз:")
            return
        
        await state.update_data(amount=str(amount))
        await state.set_state(BuyUSDTStates.choose_city)
        
        await message.answer(
            f"✅ Сумма: ${amount}\n\n"
            "🏙 <b>Выберите город:</b>",
            reply_markup=await get_priority_cities_keyboard(),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("⚠️ Неверный формат суммы. Введите число (например: 100 или 100.5):")


# ============================================================================
# Шаг 3: Выбор города
# ============================================================================

@router.callback_query(BuyUSDTStates.choose_city, F.data == "city:other")
async def show_all_cities(callback: CallbackQuery):
    """Показать все города"""
    await callback.message.edit_text(
        "🌍 <b>Выберите город:</b>",
        reply_markup=await get_all_cities_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(BuyUSDTStates.choose_city, F.data == "back_to_priority_cities")
async def back_to_priority_cities(callback: CallbackQuery):
    """Вернуться к приоритетным городам"""
    await callback.message.edit_text(
        "🏙 <b>Выберите город:</b>",
        reply_markup=await get_priority_cities_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(BuyUSDTStates.choose_city, F.data == "back")
async def back_from_city(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору суммы"""
    await state.set_state(BuyUSDTStates.enter_amount)
    
    await callback.message.edit_text(
        "💰 <b>Введите Сумму USDT:</b>\n\n"
        "Например: 100 или 1500.50",
        reply_markup=get_amount_keyboard_v2(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(BuyUSDTStates.choose_city, F.data.startswith("city:"))
async def choose_city(callback: CallbackQuery, state: FSMContext):
    """Выбор города"""
    city_code = callback.data.split(":", 1)[1]
    
    if city_code == "other":
        return  # Обработано выше
    
    # Получаем название города из БД
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        city_row = await conn.fetchrow(
            "SELECT name FROM cities WHERE code = $1 AND enabled = true",
            city_code
        )
    
    if not city_row:
        await callback.answer("❌ Город не найден", show_alert=True)
        return
    
    city_name = city_row['name']
    
    await state.update_data(city=city_code, city_name=city_name)
    await state.set_state(BuyUSDTStates.confirm_rate)
    
    # Получаем данные для расчета курса
    data = await state.get_data()
    amount = float(data.get('amount', 0))
    
    # Получаем курс USDT/RUB для покупки
    from src.services.best_rate import get_best_city_rate
    
    rate_info = await get_best_city_rate('USDT/RUB', city_code, 'buy')
    
    if rate_info:
        rate = rate_info['final_rate']
        # Рассчитываем сколько рублей нужно отдать за USDT
        rub_amount = amount * rate
        
        rate_text = (
            f"✅ Город: {city_name}\n"
            f"💰 Сумма: {amount:,.0f} USDT\n\n"
            f"📊 <b>Текущий курс:</b>\n"
            f"1 USDT = {rate:,.2f} RUB\n\n"
            f"💵 <b>К оплате:</b> {rub_amount:,.2f} RUB\n\n"
            "Подтверждаете курс?"
        )
    else:
        # Fallback если курс не получен
        rate_text = (
            f"✅ Город: {city_name}\n"
            f"💰 Сумма: {amount:,.0f} USDT\n\n"
            "⚠️ <b>Курс временно недоступен</b>\n\n"
            "Продолжить оформление заявки?"
        )
    
    await callback.message.edit_text(
        rate_text,
        reply_markup=get_rate_confirm_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ============================================================================
# Шаг 3.5: Подтверждение курса
# ============================================================================

@router.callback_query(BuyUSDTStates.confirm_rate, F.data == "back")
async def back_from_rate_confirm(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору города"""
    await state.set_state(BuyUSDTStates.choose_city)
    
    await callback.message.edit_text(
        "🏙 <b>Выберите город:</b>",
        reply_markup=await get_priority_cities_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(BuyUSDTStates.confirm_rate, F.data == "rate:confirm")
async def confirm_rate(callback: CallbackQuery, state: FSMContext):
    """Подтверждение курса - переход к выбору валюты"""
    await state.set_state(BuyUSDTStates.choose_currency)
    
    data = await state.get_data()
    city_code = data.get('city')
    city_name = data.get('city_name')
    
    await callback.message.edit_text(
        f"✅ Город: {city_name}\n\n"
        "💱 <b>Выберите валюту для оплаты:</b>",
        reply_markup=get_currencies_keyboard(city_code),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(BuyUSDTStates.confirm_rate, F.data == "rate:cancel")
async def cancel_rate(callback: CallbackQuery, state: FSMContext):
    """Отмена курса - возврат к выбору города"""
    await state.set_state(BuyUSDTStates.choose_city)
    
    await callback.message.edit_text(
        "🏙 <b>Выберите город:</b>",
        reply_markup=await get_priority_cities_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("Курс отменен. Выберите другой город или вернитесь назад.")


# ============================================================================
# Шаг 4: Выбор валюты
# ============================================================================

@router.callback_query(BuyUSDTStates.choose_currency, F.data == "back")
async def back_from_currency(callback: CallbackQuery, state: FSMContext):
    """Назад к подтверждению курса"""
    await state.set_state(BuyUSDTStates.confirm_rate)
    
    data = await state.get_data()
    amount = float(data.get('amount', 0))
    city_code = data.get('city')
    city_name = data.get('city_name')
    
    # Получаем курс USDT/RUB для покупки
    from src.services.best_rate import get_best_city_rate
    
    rate_info = await get_best_city_rate('USDT/RUB', city_code, 'buy')
    
    if rate_info:
        rate = rate_info['final_rate']
        rub_amount = amount * rate
        
        rate_text = (
            f"✅ Город: {city_name}\n"
            f"💰 Сумма: {amount:,.0f} USDT\n\n"
            f"📊 <b>Текущий курс:</b>\n"
            f"1 USDT = {rate:,.2f} RUB\n\n"
            f"💵 <b>К оплате:</b> {rub_amount:,.2f} RUB\n\n"
            "Подтверждаете курс?"
        )
    else:
        rate_text = (
            f"✅ Город: {city_name}\n"
            f"💰 Сумма: {amount:,.0f} USDT\n\n"
            "⚠️ <b>Курс временно недоступен</b>\n\n"
            "Продолжить оформление заявки?"
        )
    
    await callback.message.edit_text(
        rate_text,
        reply_markup=get_rate_confirm_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(BuyUSDTStates.choose_currency, F.data.startswith("currency:"))
async def choose_currency(callback: CallbackQuery, state: FSMContext):
    """Выбор валюты"""
    currency = callback.data.split(":", 1)[1]
    
    await state.update_data(currency=currency)
    await state.set_state(BuyUSDTStates.enter_username)
    
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"✅ Валюта: {currency}\n\n"
        "👤 <b>Напишите свой телеграм-юзернейм через @:</b>\n"
        "(пример: @btc_otc)",
        parse_mode="HTML"
    )
    await callback.answer()


# ============================================================================
# Шаг 5: Ввод username
# ============================================================================

@router.message(BuyUSDTStates.enter_username, F.text)
async def enter_username(message: Message, state: FSMContext):
    """Ввод username"""
    username = message.text.strip()
    
    await state.update_data(username=username)
    await state.set_state(BuyUSDTStates.confirm)
    
    # Формируем итоговую заявку
    data = await state.get_data()
    
    # Получаем курс для отображения
    from src.services.best_rate import get_best_city_rate
    
    amount = float(data.get('amount', 0))
    city = data.get('city', 'moscow')
    currency = data.get('currency', 'RUB')
    
    # Получаем курс USDT/RUB для покупки
    rate_info = await get_best_city_rate('USDT/RUB', city, 'buy')
    
    if rate_info:
        rate = rate_info['final_rate']
        # Рассчитываем сколько рублей нужно отдать за USDT
        rub_amount = amount * rate
        
        summary = (
            f"📋 <b>Заявка #{message.from_user.id}</b>\n\n"
            f"🔄 Операция: <b>Покупка USDT</b>\n"
            f"💰 Отдаете: {rub_amount:,.2f} {currency}\n"
            f"💎 Получаете: {amount:,.0f} USDT\n"
            f"📊 Курс: 1 USDT = {rate:,.2f} {currency}\n"
            f"🏙 Город: {data.get('city_name', 'N/A')}\n"
            f"👤 Username: {username}\n\n"
            "Всё верно?"
        )
    else:
        # Fallback если курс не получен
        summary = (
            "📋 <b>Проверьте вашу заявку:</b>\n\n"
            f"🔄 Операция: <b>Покупка USDT</b>\n"
            f"💎 Получаете: {amount:,.0f} USDT\n"
            f"🏙 Город: {data.get('city_name', 'N/A')}\n"
            f"💱 Валюта: {data.get('currency', 'N/A')}\n"
            f"👤 Username: {username}\n\n"
            "Всё верно?"
        )
    
    await message.answer(
        summary,
        reply_markup=get_confirm_keyboard_v2(),
        parse_mode="HTML"
    )


# ============================================================================
# Шаг 6: Подтверждение и создание заявки
# ============================================================================

@router.callback_query(BuyUSDTStates.confirm, F.data == "back")
async def back_from_confirm(callback: CallbackQuery, state: FSMContext):
    """Назад к вводу username"""
    await state.set_state(BuyUSDTStates.enter_username)
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"✅ Валюта: {data.get('currency', 'N/A')}\n\n"
        "👤 <b>Напишите свой телеграм-юзернейм через @:</b>\n"
        "(пример: @btc_otc)",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(BuyUSDTStates.confirm, F.data == "confirm:yes")
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    """Подтверждение заявки"""
    logger.info(f"Confirming buy_usdt order from user {callback.from_user.id}")
    data = await state.get_data()
    logger.info(f"Order data: {data}")
    
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        # Сначала убедимся что пользователь есть в БД и получаем его id
        user_id = await conn.fetchval("""
            INSERT INTO users (tg_id, username, first_name, lang)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (tg_id) DO UPDATE SET username = EXCLUDED.username
            RETURNING id
        """, 
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.first_name,
            callback.from_user.language_code or 'ru'
        )
        
        # Теперь создаем заявку с правильным user_id
        order_id = await conn.fetchval("""
            INSERT INTO orders (
                user_id, 
                order_type, 
                city, 
                currency, 
                amount, 
                status, 
                username
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        """,
            user_id,  # Используем id из таблицы users
            'buy_usdt',
            data.get('city'),
            data.get('currency'),
            float(data.get('amount', 0)),
            'new',
            data.get('username')
        )
    
    await state.clear()
    
    await callback.message.edit_text(
        f"✅ Ваша заявка #{order_id} принята!\n\n"
        f"Скоро пришлем контакты Вашего менеджера\n\n"
        "Спасибо за обращение!"
    )
    
    await callback.answer()
    
    logger.info(f"Order #{order_id} created: buy_usdt, user={callback.from_user.id}")


@router.callback_query(BuyUSDTStates.confirm, F.data == "confirm:edit")
async def edit_order(callback: CallbackQuery, state: FSMContext):
    """Изменение заявки"""
    await state.set_state(BuyUSDTStates.enter_amount)
    await callback.message.edit_text(
        "🔄 Начнем заново.\n\n"
        "💰 <b>Введите Сумму USDT:</b>\n\n"
        "Например: 100 или 1500.50",
        reply_markup=get_amount_keyboard_v2(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(BuyUSDTStates.confirm, F.data == "confirm:cancel")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    """Отмена заявки"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Заявка отменена.",
        parse_mode="HTML"
    )
    await callback.answer()


# ============================================================================
# Универсальный обработчик "Связаться с менеджером" для всех состояний
# ============================================================================

async def handle_contact_manager(callback: CallbackQuery):
    """Универсальная функция для связи с менеджером"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    contact_message = (
        "💬 Напишите нам для консультации\n\n"
        "Мы всегда рады помочь!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать менеджеру", url=f"https://t.me/{MANAGER_USERNAME[1:]}")],
    ])
    
    await callback.message.answer(
        contact_message,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(StateFilter(BuyUSDTStates), F.data == "contact_manager")
async def contact_manager_in_state(callback: CallbackQuery, state: FSMContext):
    """Связаться с менеджером в любом состоянии FSM"""
    await handle_contact_manager(callback)


@router.callback_query(F.data == "contact_manager")
async def contact_manager_no_state(callback: CallbackQuery):
    """Связаться с менеджером вне FSM"""
    await handle_contact_manager(callback)


# ============================================================================
# Обработчики неизвестных коллбэков (для отладки)
# ============================================================================

@router.callback_query(BuyUSDTStates.enter_amount)
async def handle_unknown_enter_amount(callback: CallbackQuery, state: FSMContext):
    """Обработчик для неизвестных callback в состоянии enter_amount"""
    logger.warning(f"Unhandled callback in BuyUSDTStates.enter_amount: {callback.data}")
    await callback.answer("⚠️ Пожалуйста, введите сумму текстом", show_alert=True)


@router.callback_query(BuyUSDTStates.choose_city)
async def handle_unknown_choose_city(callback: CallbackQuery, state: FSMContext):
    """Обработчик для неизвестных callback в состоянии choose_city"""
    logger.warning(f"Unhandled callback in BuyUSDTStates.choose_city: {callback.data}")
    await callback.answer("⚠️ Пожалуйста, выберите город из списка", show_alert=True)


@router.callback_query(BuyUSDTStates.confirm_rate)
async def handle_unknown_confirm_rate(callback: CallbackQuery, state: FSMContext):
    """Обработчик для неизвестных callback в состоянии confirm_rate"""
    logger.warning(f"Unhandled callback in BuyUSDTStates.confirm_rate: {callback.data}")
    await callback.answer("⚠️ Пожалуйста, подтвердите или отмените курс", show_alert=True)


@router.callback_query(BuyUSDTStates.choose_currency)
async def handle_unknown_choose_currency(callback: CallbackQuery, state: FSMContext):
    """Обработчик для неизвестных callback в состоянии choose_currency"""
    logger.warning(f"Unhandled callback in BuyUSDTStates.choose_currency: {callback.data}")
    await callback.answer("⚠️ Пожалуйста, выберите валюту", show_alert=True)


@router.callback_query(BuyUSDTStates.enter_username)
async def handle_unknown_enter_username(callback: CallbackQuery, state: FSMContext):
    """Обработчик для неизвестных callback в состоянии enter_username"""
    logger.warning(f"Unhandled callback in BuyUSDTStates.enter_username: {callback.data}")
    await callback.answer("⚠️ Пожалуйста, введите username текстом", show_alert=True)


@router.callback_query(BuyUSDTStates.confirm)
async def handle_unknown_confirm_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик для неизвестных callback в состоянии confirm"""
    logger.warning(f"Unhandled callback in BuyUSDTStates.confirm: {callback.data}")
    await callback.answer("⚠️ Неизвестная команда", show_alert=True)
