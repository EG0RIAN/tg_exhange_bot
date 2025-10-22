"""
Обработчики для пути "Оплатить инвойс"
Клиент оплачивает инвойс наличными или USDT
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter, Command

from src.fsm import PayInvoiceStates
from src.keyboards import (
    get_invoice_purposes_keyboard,
    get_payment_methods_keyboard,
    get_priority_cities_keyboard,
    get_all_cities_keyboard,
    get_amount_keyboard_v2,
    get_confirm_keyboard_v2,
    get_currencies_keyboard,
    main_menu
)
from src.db import get_pg_pool
import logging
from src.utils.logger import log_handler, log_user_action, log_order_event

router = Router()
logger = logging.getLogger(__name__)

MANAGER_USERNAME = "@btc_otc"


# ============================================================================
# Универсальный обработчик /start для сброса состояния
# ============================================================================

@router.message(Command("start"), StateFilter(PayInvoiceStates))
async def reset_to_start(message: Message, state: FSMContext):
    """Сброс состояния и возврат в главное меню"""
    await state.clear()
    from src.i18n import _, detect_user_lang
    from src.db import get_pg_pool
    pool = await get_pg_pool()
    lang = await detect_user_lang(message.from_user, db_pool=pool)
    from src.keyboards import main_menu
    await message.answer(_("start_message", lang=lang), reply_markup=main_menu)


# ============================================================================
# Шаг 1: Выбор цели
# ============================================================================

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


@router.callback_query(PayInvoiceStates.choose_purpose, F.data == "back")
async def back_from_purpose(callback: CallbackQuery, state: FSMContext):
    """Назад из выбора цели - возврат в главное меню"""
    await state.clear()
    from src.i18n import _, detect_user_lang
    pool = await get_pg_pool()
    lang = await detect_user_lang(callback.from_user, db_pool=pool)
    await callback.message.edit_text(_("start_message", lang=lang))
    await callback.message.answer("Главное меню:", reply_markup=main_menu)
    await callback.answer()


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


# ============================================================================
# Шаг 2: Выбор способа оплаты
# ============================================================================

@router.callback_query(PayInvoiceStates.choose_payment_method, F.data == "back")
async def back_from_payment_method(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору цели"""
    await state.set_state(PayInvoiceStates.choose_purpose)
    
    await callback.message.edit_text(
        "🎯 <b>Выберите цель оплаты:</b>",
        reply_markup=get_invoice_purposes_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(PayInvoiceStates.choose_payment_method, F.data.startswith("payment:"))
async def choose_payment_method(callback: CallbackQuery, state: FSMContext):
    """Выбор способа оплаты"""
    payment_method = callback.data.split(":", 1)[1]
    
    await state.update_data(payment_method=payment_method)
    await state.set_state(PayInvoiceStates.enter_amount)
    
    payment_text = "💵 Наличные" if payment_method == "cash" else "💎 USDT"
    
    await callback.message.edit_text(
        f"✅ Способ оплаты: {payment_text}\n\n"
        "💰 <b>Введите Сумму:</b>\n\n"
        "(Минимальная сумма для заявки 2500 Usdt)",
        reply_markup=get_amount_keyboard_v2(),
        parse_mode="HTML"
    )
    await callback.answer()


# ============================================================================
# Шаг 3: Ввод суммы
# ============================================================================

@router.callback_query(PayInvoiceStates.enter_amount, F.data == "back")
async def back_from_amount(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору способа оплаты"""
    await state.set_state(PayInvoiceStates.choose_payment_method)
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"✅ Цель: {data.get('purpose_name')}\n\n"
        "💳 <b>Выберите способ оплаты:</b>",
        reply_markup=get_payment_methods_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()




@router.message(PayInvoiceStates.enter_amount, F.text)
@log_handler("enter_amount")
async def enter_custom_amount(message: Message, state: FSMContext):
    """Ввод произвольной суммы"""
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            logger.warning(f"User {message.from_user.id} entered invalid amount: {amount}")
            await message.answer("⚠️ Сумма должна быть больше нуля. Попробуйте еще раз:")
            return
        
        # Проверка минимальной суммы
        if amount < 2500:
            logger.warning(f"User {message.from_user.id} entered amount below minimum: {amount}")
            await message.answer(
                "⚠️ <b>Минимальная сумма для заявки: 2500 USDT</b>\n\n"
                "Пожалуйста, введите сумму не менее 2500 USDT:",
                parse_mode="HTML"
            )
            return
        
        log_user_action(logger, message.from_user.id, "entered amount", amount=amount)
        await state.update_data(amount=str(amount))
        data = await state.get_data()
        
        # Если наличные - выбираем валюту, если USDT - прикрепляем инвойс
        if data.get('payment_method') == 'cash':
            await state.set_state(PayInvoiceStates.choose_currency)
            await message.answer(
                f"✅ Способ оплаты: 💵 Наличные\n"
                f"✅ Сумма: ${amount}\n\n"
                "💱 <b>Выберите валюту:</b>",
                reply_markup=get_currencies_keyboard(),
                parse_mode="HTML"
            )
        else:
            await state.set_state(PayInvoiceStates.attach_invoice)
            await message.answer(
                f"✅ Способ оплаты: 💎 USDT\n"
                f"✅ Сумма: ${amount}\n\n"
                "📎 <b>Прикрепите инвойс (файл или фото):</b>",
                parse_mode="HTML"
            )
    except ValueError:
        await message.answer("⚠️ Неверный формат суммы. Введите число (например: 100 или 100.5):")


# ============================================================================
# Шаг 4: Выбор валюты (только для наличных)
# ============================================================================

@router.callback_query(PayInvoiceStates.choose_currency, F.data == "back")
async def back_from_currency(callback: CallbackQuery, state: FSMContext):
    """Назад к вводу суммы"""
    await state.set_state(PayInvoiceStates.enter_amount)
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"✅ Способ оплаты: 💵 Наличные\n\n"
        "💰 <b>Введите Сумму:</b>\n\n"
        "(Минимальная сумма для заявки 2500 Usdt)",
        reply_markup=get_amount_keyboard_v2(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(PayInvoiceStates.choose_currency, F.data.startswith("currency:"))
async def choose_currency(callback: CallbackQuery, state: FSMContext):
    """Выбор валюты"""
    currency = callback.data.split(":", 1)[1]
    
    await state.update_data(currency=currency)
    await state.set_state(PayInvoiceStates.choose_city)
    
    await callback.message.edit_text(
        f"✅ Способ оплаты: 💵 Наличные\n"
        f"✅ Сумма: ${(await state.get_data()).get('amount')}\n"
        f"✅ Валюта: {currency}\n\n"
        "🏙 <b>Выберите город:</b>",
        reply_markup=await get_priority_cities_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# ============================================================================
# Шаг 5: Выбор города (только для наличных)
# ============================================================================

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


@router.callback_query(PayInvoiceStates.choose_city, F.data == "back")
async def back_from_city(callback: CallbackQuery, state: FSMContext):
    """Назад к выбору валюты"""
    await state.set_state(PayInvoiceStates.choose_currency)
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"✅ Способ оплаты: 💵 Наличные\n"
        f"✅ Сумма: ${data.get('amount')}\n\n"
        "💱 <b>Выберите валюту:</b>",
        reply_markup=get_currencies_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(PayInvoiceStates.choose_city, F.data.startswith("city:"))
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
    await state.set_state(PayInvoiceStates.attach_invoice)
    
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"✅ Способ оплаты: 💵 Наличные\n"
        f"✅ Сумма: ${data.get('amount')}\n"
        f"✅ Валюта: {data.get('currency')}\n"
        f"✅ Город: {city_name}\n\n"
        "📎 <b>Прикрепите инвойс (файл или фото):</b>",
        parse_mode="HTML"
    )
    await callback.answer()


# ============================================================================
# Шаг 5: Прикрепление инвойса
# ============================================================================

@router.message(PayInvoiceStates.attach_invoice, F.document | F.photo)
async def attach_invoice_file(message: Message, state: FSMContext):
    """Прикрепление файла или фото инвойса"""
    data = await state.get_data()
    
    # Сохраняем file_id
    if message.document:
        file_id = message.document.file_id
    elif message.photo:
        file_id = message.photo[-1].file_id
    else:
        await message.answer("⚠️ Пожалуйста, отправьте файл или фото инвойса.")
        return
    
    await state.update_data(invoice_file_id=file_id)
    await state.set_state(PayInvoiceStates.enter_username)
    
    await message.answer(
        "✅ Инвойс прикреплен\n\n"
        "👤 <b>Напишите свой телеграм-юзернейм через @:</b>\n"
        "(пример: @btc_otc)",
        parse_mode="HTML"
    )


# ============================================================================
# Шаг 6: Ввод username
# ============================================================================

@router.message(PayInvoiceStates.enter_username, F.text)
async def enter_username(message: Message, state: FSMContext):
    """Ввод username"""
    username = message.text.strip()
    
    await state.update_data(username=username)
    await state.set_state(PayInvoiceStates.confirm)
    
    data = await state.get_data()
    
    # Получаем курс для отображения (если наличные)
    amount = float(data.get('amount', 0))
    currency = data.get('currency', 'RUB')
    
    if data.get('payment_method') == 'cash':
        # Для наличных - показываем курс и расчёт
        from src.services.best_rate import get_best_city_rate
        
        city = data.get('city', 'moscow')
        # Получаем курс USDT/RUB для покупки (клиент покупает USDT за рубли)
        rate_info = await get_best_city_rate('USDT/RUB', city, 'buy')
        
        if rate_info:
            rate = rate_info['final_rate']
            # Рассчитываем сколько USDT получит клиент за рубли
            usdt_amount = amount / rate
            
            summary = (
                f"📋 <b>Заявка #{message.from_user.id}</b>\n\n"
                f"🔄 Операция: <b>Оплата инвойса</b>\n"
                f"💰 Отдаете: {amount:,.0f} {currency}\n"
                f"💎 Получаете: {usdt_amount:,.2f} USDT\n"
                f"📊 Курс: 1 USDT = {rate:,.2f} {currency}\n"
                f"🏙 Город: {data.get('city_name', 'N/A')}\n"
                f"🎯 Цель: {data.get('purpose_name', 'N/A')}\n"
                f"💳 Способ оплаты: 💵 Наличные\n"
                f"📎 Инвойс: прикреплен\n"
                f"👤 Username: {username}\n\n"
                "Всё верно?"
            )
        else:
            # Fallback если курс не получен
            summary = (
                "📋 <b>Проверьте вашу заявку:</b>\n\n"
                f"🔄 Операция: <b>Оплата инвойса</b>\n"
                f"💰 Сумма: ${amount}\n"
                f"🏙 Город: {data.get('city_name', 'N/A')}\n"
                f"🎯 Цель: {data.get('purpose_name', 'N/A')}\n"
                f"💳 Способ оплаты: 💵 Наличные\n"
                f"📎 Инвойс: прикреплен\n"
                f"👤 Username: {username}\n\n"
                "Всё верно?"
            )
    else:
        # Для USDT - просто показываем сумму
        summary = (
            f"📋 <b>Заявка #{message.from_user.id}</b>\n\n"
            f"🔄 Операция: <b>Оплата инвойса</b>\n"
            f"💎 Сумма: {amount:,.2f} USDT\n"
            f"🎯 Цель: {data.get('purpose_name', 'N/A')}\n"
            f"💳 Способ оплаты: 💎 USDT\n"
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
        
        # Создаем заявку
        order_id = await conn.fetchval("""
            INSERT INTO orders (
                user_id, 
                order_type, 
                city, 
                payment_method, 
                purpose, 
                amount, 
                invoice_file_id,
                status, 
                username
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        """,
            user_id,
            'pay_invoice',
            data.get('city'),  # может быть None если USDT
            data.get('payment_method'),
            data.get('purpose'),
            float(data.get('amount', 0)),
            data.get('invoice_file_id'),
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
    await callback.answer()


@router.callback_query(F.data == "contact_manager")
async def contact_manager(callback: CallbackQuery, state: FSMContext):
    """Связаться с менеджером на любом этапе"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    contact_message = (
        "👨‍💼 Контакты менеджера\n\n"
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
