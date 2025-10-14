"""
Обработчики для пути "Оплатить инвойс"
Клиент оплачивает инвойс наличными или USDT
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from src.fsm import PayInvoiceStates
from src.keyboards import (
    get_invoice_purposes_keyboard,
    get_payment_methods_keyboard,
    get_countries_keyboard,
    get_priority_cities_keyboard,
    get_all_cities_keyboard,
    get_amount_keyboard_v2,
    get_confirm_keyboard_v2,
    main_menu
)
from src.db import get_pg_pool
import logging

router = Router()
logger = logging.getLogger(__name__)

MANAGER_USERNAME = "@btc_otc"


@router.message(F.text == "📄 Оплатить инвойс")
async def start_pay_invoice(message: Message, state: FSMContext):
    """Начало пути оплаты инвойса"""
    await state.clear()
    await state.set_state(PayInvoiceStates.choose_purpose)
    
    await message.answer(
        "🎯 <b>Выберите цель оплаты:</b>",
        reply_markup=get_invoice_purposes_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(PayInvoiceStates.choose_purpose, F.data.startswith("purpose:"))
async def choose_purpose(callback: CallbackQuery, state: FSMContext):
    """Выбор цели инвойса"""
    purpose = callback.data.split(":", 1)[1]
    
    purpose_names = {
        "services": "🏢 Оплата услуг",
        "goods": "🏬 Покупка товаров",
        "delivery": "📦 Доставка/логистика",
        "other": "💼 Прочее",
    }
    
    await state.update_data(purpose=purpose, purpose_name=purpose_names.get(purpose, purpose))
    await state.set_state(PayInvoiceStates.choose_payment_method)
    
    await callback.message.edit_text(
        f"✅ Цель: {purpose_names.get(purpose)}\n\n"
        "💳 <b>Выберите способ оплаты:</b>",
        reply_markup=get_payment_methods_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(PayInvoiceStates.choose_payment_method, F.data.startswith("payment:"))
async def choose_payment_method(callback: CallbackQuery, state: FSMContext):
    """Выбор способа оплаты"""
    payment_method = callback.data.split(":", 1)[1]
    
    await state.update_data(payment_method=payment_method)
    
    if payment_method == "cash":
        # Если наличные - выбираем страну
        await state.set_state(PayInvoiceStates.choose_country)
        await callback.message.edit_text(
            "✅ Способ оплаты: 💵 Наличные\n\n"
            "🌍 <b>Выберите страну:</b>",
            reply_markup=get_countries_keyboard(),
            parse_mode="HTML"
        )
    else:
        # Если USDT - сразу к сумме
        await state.set_state(PayInvoiceStates.enter_amount)
        await callback.message.edit_text(
            "✅ Способ оплаты: 💎 USDT\n\n"
            "💰 <b>Введите сумму:</b>",
            reply_markup=get_amount_keyboard_v2(),
            parse_mode="HTML"
        )
    
    await callback.answer()


# ============================================================================
# Ветка "Наличные" - выбор страны и города
# ============================================================================

@router.callback_query(PayInvoiceStates.choose_country, F.data.startswith("country:"))
async def choose_country(callback: CallbackQuery, state: FSMContext):
    """Выбор страны (только для наличных)"""
    country = callback.data.split(":", 1)[1]
    
    country_names = {
        "russia": "🇷🇺 Россия",
        "kazakhstan": "🇰🇿 Казахстан",
        "uzbekistan": "🇺🇿 Узбекистан",
        "azerbaijan": "🇦🇿 Азербайджан",
        "georgia": "🇬🇪 Грузия",
        "turkey": "🇹🇷 Турция",
        "uae": "🇦🇪 ОАЭ",
    }
    
    await state.update_data(country=country, country_name=country_names.get(country, country))
    await state.set_state(PayInvoiceStates.choose_city)
    
    await callback.message.edit_text(
        f"✅ Выбрана страна: {country_names.get(country)}\n\n"
        "🏙 <b>Выберите город:</b>",
        reply_markup=await get_priority_cities_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(PayInvoiceStates.choose_city, F.data == "city:other")
async def show_all_cities(callback: CallbackQuery):
    """Показать все города"""
    await callback.message.edit_text(
        "🌍 <b>Выберите город:</b>",
        reply_markup=await get_all_cities_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(PayInvoiceStates.choose_city, F.data == "back_to_priority_cities")
async def back_to_priority_cities(callback: CallbackQuery):
    """Вернуться к приоритетным городам"""
    await callback.message.edit_text(
        "🏙 <b>Выберите город:</b>",
        reply_markup=await get_priority_cities_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(PayInvoiceStates.choose_city, F.data.startswith("city:"))
async def choose_city(callback: CallbackQuery, state: FSMContext):
    """Выбор города (только для наличных)"""
    city_code = callback.data.split(":", 1)[1]
    
    if city_code == "other":
        return
    
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
    await state.set_state(PayInvoiceStates.enter_amount)
    
    await callback.message.edit_text(
        f"✅ Выбран город: {city_name}\n\n"
        "💰 <b>Введите сумму:</b>",
        reply_markup=get_amount_keyboard_v2(),
        parse_mode="HTML"
    )
    await callback.answer()


# ============================================================================
# Ввод суммы (общий для обеих веток)
# ============================================================================

@router.callback_query(PayInvoiceStates.enter_amount, F.data == "amount:custom")
async def amount_custom(callback: CallbackQuery):
    """Запрос ввода своей суммы"""
    await callback.message.answer(
        "📝 Введите сумму (например: 1000):"
    )
    await callback.answer()


@router.callback_query(PayInvoiceStates.enter_amount, F.data.startswith("amount:"))
async def amount_selected(callback: CallbackQuery, state: FSMContext):
    """Выбор суммы из предложенных"""
    amount = callback.data.split(":", 1)[1]
    
    if amount == "custom":
        return
    
    await state.update_data(amount=amount)
    await state.set_state(PayInvoiceStates.attach_invoice)
    
    await callback.message.edit_text(
        f"✅ Сумма: ${amount}\n\n"
        "📎 <b>Прикрепите файл инвойса</b>\n"
        "(фото, PDF или документ):",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(PayInvoiceStates.enter_amount, F.text)
async def amount_entered(message: Message, state: FSMContext):
    """Обработка введенной суммы"""
    try:
        amount = float(message.text.replace(",", ".").replace(" ", ""))
        if amount <= 0:
            raise ValueError
        
        await state.update_data(amount=str(int(amount)))
        await state.set_state(PayInvoiceStates.attach_invoice)
        
        await message.answer(
            f"✅ Сумма: ${int(amount)}\n\n"
            "📎 <b>Прикрепите файл инвойса</b>\n"
            "(фото, PDF или документ):",
            parse_mode="HTML"
        )
    except (ValueError, AttributeError):
        await message.answer(
            "❌ Неверный формат суммы. Введите число (например: 1000):"
        )


# ============================================================================
# Прикрепление инвойса
# ============================================================================

@router.message(PayInvoiceStates.attach_invoice, F.photo | F.document)
async def attach_invoice(message: Message, state: FSMContext):
    """Прикрепление файла инвойса"""
    
    # Получаем file_id
    if message.photo:
        file_id = message.photo[-1].file_id  # Берем самое большое фото
        file_type = "photo"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
    else:
        return
    
    await state.update_data(invoice_file_id=file_id, invoice_file_type=file_type)
    await state.set_state(PayInvoiceStates.enter_username)
    
    await message.answer(
        "✅ Инвойс получен!\n\n"
        "👤 <b>Оставьте ваш Telegram username:</b>\n"
        "(например: @yourname)",
        parse_mode="HTML"
    )


@router.message(PayInvoiceStates.attach_invoice)
async def invalid_invoice(message: Message):
    """Неверный формат инвойса"""
    await message.answer(
        "❌ Пожалуйста, прикрепите файл инвойса (фото, PDF или документ):"
    )


# ============================================================================
# Ввод username
# ============================================================================

@router.message(PayInvoiceStates.enter_username, F.text)
async def enter_username(message: Message, state: FSMContext):
    """Ввод username"""
    username = message.text.strip()
    
    await state.update_data(username=username)
    await state.set_state(PayInvoiceStates.confirm)
    
    data = await state.get_data()
    
    # Формируем резюме
    summary = (
        "📋 <b>Проверьте вашу заявку:</b>\n\n"
        f"🔄 Операция: <b>Оплата инвойса</b>\n"
        f"🎯 Цель: {data.get('purpose_name', 'N/A')}\n"
        f"💳 Способ оплаты: {'💵 Наличные' if data.get('payment_method') == 'cash' else '💎 USDT'}\n"
    )
    
    if data.get('payment_method') == 'cash':
        summary += (
            f"🌍 Страна: {data.get('country_name', 'N/A')}\n"
            f"🏙 Город: {data.get('city_name', 'N/A')}\n"
        )
    
    summary += (
        f"💰 Сумма: ${data.get('amount', 'N/A')}\n"
        f"📎 Инвойс: прикреплен\n"
        f"👤 Username: {username}\n\n"
        "Всё верно?"
    )
    
    await message.answer(
        summary,
        reply_markup=get_confirm_keyboard_v2(),
        parse_mode="HTML"
    )


# ============================================================================
# Подтверждение заявки
# ============================================================================

@router.callback_query(PayInvoiceStates.confirm, F.data == "confirm:yes")
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    """Подтверждение заявки"""
    data = await state.get_data()
    
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        order_id = await conn.fetchval("""
            INSERT INTO orders (
                user_id, username, order_type, 
                country, city, payment_method, purpose, 
                amount, invoice_file_id, invoice_file_type, 
                status, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW())
            RETURNING id
        """,
            callback.from_user.id,
            data.get('username'),
            'pay_invoice',
            data.get('country'),
            data.get('city'),
            data.get('payment_method'),
            data.get('purpose'),
            data.get('amount'),
            data.get('invoice_file_id'),
            data.get('invoice_file_type'),
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
    
    logger.info(f"Order #{order_id} created: pay_invoice, user={callback.from_user.id}")


@router.callback_query(PayInvoiceStates.confirm, F.data == "confirm:edit")
async def edit_order(callback: CallbackQuery, state: FSMContext):
    """Изменение заявки"""
    await state.set_state(PayInvoiceStates.choose_purpose)
    await callback.message.edit_text(
        "🔄 Начнем заново.\n\n"
        "🎯 <b>Выберите цель оплаты:</b>",
        reply_markup=get_invoice_purposes_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(PayInvoiceStates.confirm, F.data == "confirm:cancel")
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


@router.callback_query(F.data == "contact_manager")
async def contact_manager(callback: CallbackQuery, state: FSMContext):
    """Связаться с менеджером на любом этапе"""
    await callback.answer(
        f"Вы можете написать менеджеру: {MANAGER_USERNAME}",
        show_alert=True
    )

