"""
Общая логика для обработчиков покупки и продажи USDT
Устраняет дублирование кода между buy_usdt.py и sell_usdt.py
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from typing import Optional, Dict
import logging

from src.keyboards import (
    get_priority_cities_keyboard,
    get_all_cities_keyboard,
    get_currencies_keyboard,
    get_amount_keyboard_v2,
    get_confirm_keyboard_v2,
    get_rate_confirm_keyboard,
)
from src.db import get_pg_pool

logger = logging.getLogger(__name__)

MANAGER_USERNAME = "@btc_otc"


# ============================================================================
# Общие вспомогательные функции
# ============================================================================

async def handle_contact_manager(callback: CallbackQuery):
    """Универсальная функция для связи с менеджером"""
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


def get_operation_emoji(operation: str) -> str:
    """Возвращает emoji для типа операции"""
    return "💵" if operation == "buy" else "💸"


def get_operation_text(operation: str) -> str:
    """Возвращает текст для типа операции"""
    return "Покупка USDT" if operation == "buy" else "Продажа USDT"


def get_operation_action(operation: str) -> str:
    """Возвращает действие для типа операции"""
    return "Купить" if operation == "buy" else "Продать"


# ============================================================================
# Обработчик выбора города
# ============================================================================

async def handle_choose_city(
    callback: CallbackQuery,
    state: FSMContext,
    operation: str,
    next_state
):
    """Обработка выбора города"""
    city_code = callback.data.split(":", 1)[1]
    
    if city_code == "other":
        return  # Обработано в show_all_cities
    
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
    await state.set_state(next_state)
    
    # Получаем данные для расчета курса
    data = await state.get_data()
    amount = float(data.get('amount', 0))
    
    # Получаем курс USDT/RUB
    from src.services.best_rate import get_best_city_rate
    
    rate_info = await get_best_city_rate('USDT/RUB', city_code, operation)
    
    if rate_info:
        rate = rate_info['final_rate']
        rub_amount = amount * rate
        
        if operation == "buy":
            rate_text = (
                f"✅ Город: {city_name}\n"
                f"💰 Сумма: {amount:,.0f} USDT\n\n"
                f"📊 <b>Текущий курс:</b>\n"
                f"1 USDT = {rate:,.2f} RUB\n\n"
                f"💵 <b>К оплате:</b> {rub_amount:,.2f} RUB\n\n"
                "Подтверждаете курс?"
            )
        else:  # sell
            rate_text = (
                f"✅ Город: {city_name}\n"
                f"💰 Сумма: {amount:,.0f} USDT\n\n"
                f"📊 <b>Текущий курс:</b>\n"
                f"1 USDT = {rate:,.2f} RUB\n\n"
                f"💵 <b>Вы получите:</b> {rub_amount:,.2f} RUB\n\n"
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
# Обработчик подтверждения заявки
# ============================================================================

async def handle_confirm_order(
    callback: CallbackQuery,
    state: FSMContext,
    order_type: str
):
    """Подтверждение и создание заявки"""
    logger.info(f"Confirming {order_type} order from user {callback.from_user.id}")
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
            user_id,
            order_type,
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
    
    logger.info(f"Order #{order_id} created: {order_type}, user={callback.from_user.id}")


# ============================================================================
# Формирование итоговой заявки
# ============================================================================

async def format_order_summary(
    data: Dict,
    user_id: int,
    operation: str
) -> str:
    """Формирует текст итоговой заявки"""
    from src.services.best_rate import get_best_city_rate
    
    amount = float(data.get('amount', 0))
    city = data.get('city', 'moscow')
    currency = data.get('currency', 'RUB')
    username = data.get('username', 'N/A')
    city_name = data.get('city_name', 'N/A')
    
    # Получаем курс USDT/RUB
    rate_info = await get_best_city_rate('USDT/RUB', city, operation)
    
    if rate_info:
        rate = rate_info['final_rate']
        rub_amount = amount * rate
        
        if operation == "buy":
            summary = (
                f"📋 <b>Заявка #{user_id}</b>\n\n"
                f"🔄 Операция: <b>{get_operation_text(operation)}</b>\n"
                f"💰 Отдаете: {rub_amount:,.2f} {currency}\n"
                f"💎 Получаете: {amount:,.0f} USDT\n"
                f"📊 Курс: 1 USDT = {rate:,.2f} {currency}\n"
                f"🏙 Город: {city_name}\n"
                f"👤 Username: {username}\n\n"
                "Всё верно?"
            )
        else:  # sell
            summary = (
                f"📋 <b>Заявка #{user_id}</b>\n\n"
                f"🔄 Операция: <b>{get_operation_text(operation)}</b>\n"
                f"💎 Отдаете: {amount:,.0f} USDT\n"
                f"💰 Получаете: {rub_amount:,.0f} {currency}\n"
                f"📊 Курс: 1 USDT = {rate:,.2f} {currency}\n"
                f"🏙 Город: {city_name}\n"
                f"👤 Username: {username}\n\n"
                "Всё верно?"
            )
    else:
        # Fallback если курс не получен
        summary = (
            "📋 <b>Проверьте вашу заявку:</b>\n\n"
            f"🔄 Операция: <b>{get_operation_text(operation)}</b>\n"
            f"💰 Сумма: ${data.get('amount', 'N/A')} USDT\n"
            f"🏙 Город: {city_name}\n"
            f"💱 Валюта: {data.get('currency', 'N/A')}\n"
            f"👤 Username: {username}\n\n"
            "Всё верно?"
        )
    
    return summary

