"""
Обработчики для пути "Купить USDT"
Клиент покупает USDT за наличные
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from src.fsm import BuyUSDTStates
from src.keyboards import (
    get_priority_cities_keyboard,
    get_all_cities_keyboard,
    get_currencies_keyboard,
    get_amount_keyboard_v2,
    get_confirm_keyboard_v2,
    main_menu
)
from src.db import get_pg_pool
import logging

router = Router()
logger = logging.getLogger(__name__)

# Менеджер по умолчанию
MANAGER_USERNAME = "@btc_otc"


# ============================================================================
# Шаг 1: Начало - кнопка "💵 Купить USDT"
# ============================================================================

@router.message(F.text == "💵 Купить USDT")
async def start_buy_usdt(message: Message, state: FSMContext):
    """Начало пути покупки USDT"""
    await state.clear()
    await state.set_state(BuyUSDTStates.choose_city)
    
    await message.answer(
        "🏙 <b>Выберите город:</b>",
        reply_markup=await get_priority_cities_keyboard(),
        parse_mode="HTML"
    )


# ============================================================================
# Шаг 2: Выбор города
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
    await state.set_state(BuyUSDTStates.choose_currency)
    
    await callback.message.edit_text(
        f"✅ Выбран город: {city_name}\n\n"
        "💱 <b>Выберите валюту для оплаты:</b>",
        reply_markup=get_currencies_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ============================================================================
# Шаг 4: Выбор валюты
# ============================================================================

@router.callback_query(BuyUSDTStates.choose_currency, F.data.startswith("currency:"))
async def choose_currency(callback: CallbackQuery, state: FSMContext):
    """Выбор валюты"""
    currency = callback.data.split(":", 1)[1]
    
    await state.update_data(currency=currency)
    await state.set_state(BuyUSDTStates.enter_amount)
    
    await callback.message.edit_text(
        f"✅ Выбрана валюта: {currency}\n\n"
        "💰 <b>Выберите сумму или введите свою:</b>",
        reply_markup=get_amount_keyboard_v2(),
        parse_mode="HTML"
    )
    await callback.answer()


# ============================================================================
# Шаг 5: Ввод суммы
# ============================================================================

@router.callback_query(BuyUSDTStates.enter_amount, F.data == "amount:custom")
async def amount_custom(callback: CallbackQuery):
    """Запрос ввода своей суммы"""
    await callback.message.answer(
        "📝 Введите сумму (например: 1000):"
    )
    await callback.answer()


@router.callback_query(BuyUSDTStates.enter_amount, F.data.startswith("amount:"))
async def amount_selected(callback: CallbackQuery, state: FSMContext):
    """Выбор суммы из предложенных"""
    amount = callback.data.split(":", 1)[1]
    
    if amount == "custom":
        return  # Обработано выше
    
    await state.update_data(amount=amount)
    await state.set_state(BuyUSDTStates.enter_username)
    
    await callback.message.edit_text(
        f"✅ Сумма: ${amount}\n\n"
        "👤 <b>Оставьте ваш Telegram username:</b>\n"
        "(например: @yourname)",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(BuyUSDTStates.enter_amount, F.text)
async def amount_entered(message: Message, state: FSMContext):
    """Обработка введенной суммы"""
    try:
        amount = float(message.text.replace(",", ".").replace(" ", ""))
        if amount <= 0:
            raise ValueError
        
        await state.update_data(amount=str(int(amount)))
        await state.set_state(BuyUSDTStates.enter_username)
        
        await message.answer(
            f"✅ Сумма: ${int(amount)}\n\n"
            "👤 <b>Оставьте ваш Telegram username:</b>\n"
            "(например: @yourname)",
            parse_mode="HTML"
        )
    except (ValueError, AttributeError):
        await message.answer(
            "❌ Неверный формат суммы. Введите число (например: 1000):"
        )


# ============================================================================
# Шаг 6: Ввод username
# ============================================================================

@router.message(BuyUSDTStates.enter_username, F.text)
async def enter_username(message: Message, state: FSMContext):
    """Ввод username"""
    username = message.text.strip()
    
    await state.update_data(username=username)
    await state.set_state(BuyUSDTStates.confirm)
    
    # Формируем итоговую заявку
    data = await state.get_data()
    
    summary = (
        "📋 <b>Проверьте вашу заявку:</b>\n\n"
        f"🔄 Операция: <b>Покупка USDT</b>\n"
        f"🏙 Город: {data.get('city_name', 'N/A')}\n"
        f"💱 Валюта: {data.get('currency', 'N/A')}\n"
        f"💰 Сумма: ${data.get('amount', 'N/A')}\n"
        f"👤 Username: {username}\n\n"
        "Всё верно?"
    )
    
    await message.answer(
        summary,
        reply_markup=get_confirm_keyboard_v2(),
        parse_mode="HTML"
    )


# ============================================================================
# Шаг 7: Подтверждение и создание заявки
# ============================================================================

@router.callback_query(BuyUSDTStates.confirm, F.data == "confirm:yes")
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    """Подтверждение заявки"""
    logger.info(f"Confirming buy_usdt order from user {callback.from_user.id}")
    data = await state.get_data()
    logger.info(f"Order data: {data}")
    
    # Сохраняем заявку в БД
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        order_id = await conn.fetchval("""
            INSERT INTO orders (
                user_id, username, order_type, city, currency, amount, status, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            RETURNING id
        """,
            callback.from_user.id,
            data.get('username'),
            'buy_usdt',
            data.get('city'),
            data.get('currency'),
            data.get('amount'),
            'new'
        )
    
    await state.clear()
    
    await callback.message.edit_text(
        f"✅ <b>Ваша заявка #{order_id} принята!</b>\n\n"
        f"🔄 С вами свяжется менеджер {MANAGER_USERNAME}\n\n"
        "Спасибо за обращение!",
        parse_mode="HTML"
    )
    
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=main_menu
    )
    
    await callback.answer()
    
    logger.info(f"Order #{order_id} created: buy_usdt, user={callback.from_user.id}")


@router.callback_query(BuyUSDTStates.confirm, F.data == "confirm:edit")
async def edit_order(callback: CallbackQuery, state: FSMContext):
    """Изменение заявки"""
    await state.set_state(BuyUSDTStates.choose_city)
    await callback.message.edit_text(
        "🔄 Начнем заново.\n\n"
        "🏙 <b>Выберите город:</b>",
        reply_markup=await get_priority_cities_keyboard(),
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
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=main_menu
    )
    await callback.answer()


# ============================================================================
# Универсальный обработчик "Связаться с менеджером"
# ============================================================================

@router.callback_query(F.data == "contact_manager")
async def contact_manager(callback: CallbackQuery, state: FSMContext):
    """Связаться с менеджером на любом этапе"""
    await callback.answer(
        f"Вы можете написать менеджеру: {MANAGER_USERNAME}",
        show_alert=True
    )


# ============================================================================
# Отладочный обработчик (ловит необработанные callback)
# ============================================================================

@router.callback_query(BuyUSDTStates())
async def debug_unhandled_callback(callback: CallbackQuery, state: FSMContext):
    """Отладка: ловит необработанные callback_query в процессе покупки"""
    current_state = await state.get_state()
    logger.warning(
        f"Unhandled callback in BuyUSDT flow: "
        f"data={callback.data}, state={current_state}, user={callback.from_user.id}"
    )
    await callback.answer("⚠️ Неизвестная команда", show_alert=True)

