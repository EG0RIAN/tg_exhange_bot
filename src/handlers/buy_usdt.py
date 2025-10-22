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
from src.utils.logger import log_handler, log_user_action, log_order_event

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
@log_handler("start_buy_usdt")
async def start_buy_usdt(message: Message, state: FSMContext):
    """Начало пути покупки USDT - ввод суммы"""
    log_user_action(logger, message.from_user.id, "started buy USDT flow")
    await state.clear()
    await state.set_state(BuyUSDTStates.enter_amount)
    
    await message.answer(
        "💰 <b>Введите Сумму USDT:</b>\n\n"
        "(Минимальная сумма для заявки 2500 Usdt)",
        reply_markup=get_amount_keyboard_v2(),
        parse_mode="HTML"
    )


# ============================================================================
# Шаг 2: Ввод суммы
# ============================================================================

@router.callback_query(BuyUSDTStates.enter_amount, F.data == "back")
async def back_from_amount(callback: CallbackQuery, state: FSMContext):
    """Назад из ввода суммы - возврат в главное меню"""
    await state.clear()
    from src.i18n import _, detect_user_lang
    pool = await get_pg_pool()
    lang = await detect_user_lang(callback.from_user, db_pool=pool)
    await callback.message.edit_text(_("start_message", lang=lang))
    await callback.message.answer("Главное меню:", reply_markup=main_menu)
    await callback.answer()


@router.message(BuyUSDTStates.enter_amount, F.text)
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
        "(Минимальная сумма для заявки 2500 Usdt)",
        reply_markup=get_amount_keyboard_v2(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(BuyUSDTStates.choose_city, F.data.startswith("city:"))
@log_handler("choose_city")
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
        logger.warning(f"User {callback.from_user.id} selected invalid city: {city_code}")
        await callback.answer("❌ Город не найден", show_alert=True)
        return
    
    city_name = city_row['name']
    log_user_action(logger, callback.from_user.id, "chose city", city=city_name, code=city_code)
    
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
@log_handler("enter_username")
async def enter_username(message: Message, state: FSMContext):
    """Ввод username"""
    username = message.text.strip()
    log_user_action(logger, message.from_user.id, "entered username", username=username)
    
    await state.update_data(username=username)
    await state.set_state(BuyUSDTStates.attach_photo)
    
    await message.answer(
        "📸 <b>Прикрепите фото или документ:</b>\n\n"
        "Например: чек, квитанцию или скриншот\n\n"
        "💡 Если хотите пропустить, нажмите /skip",
        parse_mode="HTML"
    )


# ============================================================================
# Шаг 6: Прикрепление фото/документа
# ============================================================================

@router.message(BuyUSDTStates.attach_photo, F.document | F.photo)
@log_handler("attach_photo")
async def attach_photo_file(message: Message, state: FSMContext):
    """Прикрепление фото или документа"""
    log_user_action(logger, message.from_user.id, "attaching photo")
    
    # Сохраняем file_id и тип
    if message.document:
        file_id = message.document.file_id
        file_type = "document"
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
    else:
        await message.answer("⚠️ Пожалуйста, отправьте файл или фото.")
        return
    
    await state.update_data(photo_file_id=file_id, photo_file_type=file_type)
    await show_confirmation(message, state)


@router.message(BuyUSDTStates.attach_photo, Command("skip"))
@log_handler("skip_photo")
async def skip_photo(message: Message, state: FSMContext):
    """Пропустить прикрепление фото"""
    log_user_action(logger, message.from_user.id, "skipped photo")
    await show_confirmation(message, state)


async def show_confirmation(message: Message, state: FSMContext):
    """Показать подтверждение заявки"""
    await state.set_state(BuyUSDTStates.confirm)
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
@log_handler("confirm_order")
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    """Подтверждение заявки"""
    data = await state.get_data()
    log_user_action(
        logger, callback.from_user.id, "confirming buy order",
        amount=data.get('amount'),
        city=data.get('city'),
        currency=data.get('currency')
    )
    
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
                username,
                photo_file_id,
                photo_file_type
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        """,
            user_id,  # Используем id из таблицы users
            'buy_usdt',
            data.get('city'),
            data.get('currency'),
            float(data.get('amount', 0)),
            'new',
            data.get('username'),
            data.get('photo_file_id'),
            data.get('photo_file_type')
        )
    
    await state.clear()
    
    log_order_event(
        logger, order_id, "created",
        type="buy_usdt",
        user_id=callback.from_user.id,
        amount=data.get('amount'),
        city=data.get('city')
    )
    
    await callback.message.edit_text(
        f"✅ Ваша заявка #{order_id} принята!\n\n"
        f"Скоро пришлем контакты Вашего менеджера\n\n"
        "Спасибо за обращение!"
    )
    
    await callback.answer()


@router.callback_query(BuyUSDTStates.confirm, F.data == "confirm:edit")
async def edit_order(callback: CallbackQuery, state: FSMContext):
    """Изменение заявки"""
    await state.set_state(BuyUSDTStates.enter_amount)
    await callback.message.edit_text(
        "🔄 Начнем заново.\n\n"
        "💰 <b>Введите Сумму USDT:</b>\n\n"
        "(Минимальная сумма для заявки 2500 Usdt)",
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
    # Игнорируем callback от других состояний и служебные кнопки
    if callback.data.startswith(("city:", "currency:", "rate:", "confirm:", "back", "contact_manager")):
        return
    logger.warning(f"Unhandled callback in BuyUSDTStates.enter_amount: {callback.data}")
    await callback.answer("⚠️ Пожалуйста, введите сумму текстом", show_alert=True)


@router.callback_query(BuyUSDTStates.choose_city)
async def handle_unknown_choose_city(callback: CallbackQuery, state: FSMContext):
    """Обработчик для неизвестных callback в состоянии choose_city"""
    # Игнорируем callback от других состояний и служебные кнопки
    if callback.data.startswith(("currency:", "rate:", "amount:", "confirm:", "back", "contact_manager", "rates_back")):
        return
    logger.warning(f"Unhandled callback in BuyUSDTStates.choose_city: {callback.data}")
    await callback.answer("⚠️ Пожалуйста, выберите город из списка", show_alert=True)


@router.callback_query(BuyUSDTStates.confirm_rate)
async def handle_unknown_confirm_rate(callback: CallbackQuery, state: FSMContext):
    """Обработчик для неизвестных callback в состоянии confirm_rate"""
    # Игнорируем callback от других состояний и служебные кнопки
    if callback.data.startswith(("city:", "currency:", "amount:", "back", "contact_manager")):
        return
    logger.warning(f"Unhandled callback in BuyUSDTStates.confirm_rate: {callback.data}")
    await callback.answer("⚠️ Пожалуйста, подтвердите или отмените курс", show_alert=True)


@router.callback_query(BuyUSDTStates.choose_currency)
async def handle_unknown_choose_currency(callback: CallbackQuery, state: FSMContext):
    """Обработчик для неизвестных callback в состоянии choose_currency"""
    # Игнорируем callback от других состояний и служебные кнопки
    if callback.data.startswith(("city:", "rate:", "amount:", "confirm:", "back", "contact_manager")):
        return
    logger.warning(f"Unhandled callback in BuyUSDTStates.choose_currency: {callback.data}")
    await callback.answer("⚠️ Пожалуйста, выберите валюту", show_alert=True)


@router.callback_query(BuyUSDTStates.enter_username)
async def handle_unknown_enter_username(callback: CallbackQuery, state: FSMContext):
    """Обработчик для неизвестных callback в состоянии enter_username"""
    # Игнорируем callback от других состояний и служебные кнопки
    if callback.data.startswith(("city:", "currency:", "rate:", "amount:", "confirm:", "back", "contact_manager")):
        return
    logger.warning(f"Unhandled callback in BuyUSDTStates.enter_username: {callback.data}")
    await callback.answer("⚠️ Пожалуйста, введите username текстом", show_alert=True)


@router.callback_query(BuyUSDTStates.confirm)
async def handle_unknown_confirm_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик для неизвестных callback в состоянии confirm"""
    # Игнорируем callback от других состояний и служебные кнопки
    if callback.data.startswith(("city:", "currency:", "rate:", "amount:", "confirm:", "back", "contact_manager")):
        return
    logger.warning(f"Unhandled callback in BuyUSDTStates.confirm: {callback.data}")
    await callback.answer("⚠️ Неизвестная команда", show_alert=True)
