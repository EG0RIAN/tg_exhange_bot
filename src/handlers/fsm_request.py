from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram import Bot
from src.fsm import RequestFSM
from src.keyboards import get_pairs_keyboard, get_amount_keyboard, get_payout_keyboard, get_confirm_keyboard
from src.services.content import get_pairs_for_fsm, get_payout_methods_for_pair
from src.services.notifications import notify_new_order
import re
from aiogram.filters import Command
from src.db import get_pg_pool, create_order
import asyncio

MAX_AMOUNT = 1000000

PROGRESS = ["▪️▫️▫️▫️", "▪️▪️▫️▫️", "▪️▪️▪️▫️", "▪️▪️▪️▪️"]

async def is_valid_amount(text):
    return re.match(r"^\d+(\.\d{1,8})?$", text) and float(text) <= MAX_AMOUNT

def is_valid_contact(text):
    return re.match(r"^\+\d{10,15}$", text) or re.match(r"^@[a-zA-Z0-9_]{5,32}$", text)

def escape_markdown(text):
    """Экранирует специальные символы для Markdown"""
    return text.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')

router = Router()

# --- TIMEOUT MANAGEMENT ---
async def start_timeout(state: FSMContext, chat_id: int, bot: Bot):
    # Устанавливаем время начала таймаута
    await state.update_data(timeout_start=asyncio.get_event_loop().time())

@router.message(F.text == "✉️ Оставить заявку")
async def start_request(message: Message, state: FSMContext):
    pairs = await get_pairs_for_fsm()
    if not pairs:
        await message.answer("Торговые пары не настроены. Обратитесь к администратору.")
        return
    await message.answer("Выберите валютную пару:", reply_markup=get_pairs_keyboard(pairs))
    await state.set_state(RequestFSM.ChoosePair)
    await start_timeout(state, message.chat.id, message.bot)

@router.callback_query(RequestFSM.ChoosePair, F.data.startswith("pair:"))
async def choose_pair(callback: CallbackQuery, state: FSMContext):
    pair = callback.data.split(":", 1)[1]
    await state.update_data(pair=pair)
    escaped_pair = escape_markdown(pair)
    await callback.message.edit_text(f"{PROGRESS[1]}\nПара выбрана: {escaped_pair}\nВведите сумму:", reply_markup=get_amount_keyboard())
    await state.set_state(RequestFSM.EnterAmount)
    await start_timeout(state, callback.message.chat.id, callback.bot)

@router.callback_query(RequestFSM.EnterAmount, F.data.startswith("amount:"))
async def choose_amount(callback: CallbackQuery, state: FSMContext):
    amount = callback.data.split(":", 1)[1]
    if amount == "custom":
        await callback.message.edit_text("Введите свою сумму:")
        return
    if not await is_valid_amount(amount):
        await callback.message.answer(f"Некорректная сумма. Введите число до {MAX_AMOUNT}.")
        return
    await state.update_data(amount=amount)
    data = await state.get_data()
    methods = await get_payout_methods_for_pair(data["pair"])
    await callback.message.edit_text(f"{PROGRESS[2]}\nВыберите способ выплаты:", reply_markup=get_payout_keyboard(methods))
    await state.set_state(RequestFSM.SelectPayout)
    await start_timeout(state, callback.message.chat.id, callback.bot)

@router.message(RequestFSM.EnterAmount)
async def enter_custom_amount(message: Message, state: FSMContext):
    if not await is_valid_amount(message.text):
        await message.answer(f"Некорректная сумма. Введите число до {MAX_AMOUNT}.")
        return
    await state.update_data(amount=message.text)
    data = await state.get_data()
    methods = await get_payout_methods_for_pair(data["pair"])
    await message.answer(f"{PROGRESS[2]}\nВыберите способ выплаты:", reply_markup=get_payout_keyboard(methods))
    await state.set_state(RequestFSM.SelectPayout)
    await start_timeout(state, message.chat.id, message.bot)

@router.callback_query(RequestFSM.SelectPayout, F.data.startswith("payout:"))
async def select_payout(callback: CallbackQuery, state: FSMContext):
    payout = callback.data.split(":", 1)[1]
    await state.update_data(payout_method=payout)
    await callback.message.edit_text(f"{PROGRESS[3]}\nВведите контакт (телефон в формате +79991234567 или @username):")
    await state.set_state(RequestFSM.ContactInfo)
    await start_timeout(state, callback.message.chat.id, callback.bot)

@router.message(RequestFSM.ContactInfo)
async def enter_contact(message: Message, state: FSMContext):
    if not is_valid_contact(message.text):
        await message.answer("Некорректный контакт. Введите телефон в формате +79991234567 или @username.")
        return
    await state.update_data(contact=message.text)
    data = await state.get_data()
    escaped_pair = escape_markdown(data['pair'])
    escaped_payout = escape_markdown(data['payout_method'])
    escaped_contact = escape_markdown(data['contact'])
    summary = f"Пара: {escaped_pair}\nСумма: {data['amount']}\nВыплата: {escaped_payout}\nКонтакт: {escaped_contact}"
    await message.answer(f"Проверьте заявку:\n{summary}", reply_markup=get_confirm_keyboard())
    await state.set_state(RequestFSM.Confirm)
    await start_timeout(state, message.chat.id, message.bot)

@router.callback_query(RequestFSM.Confirm, F.data == "confirm")
async def confirm_request(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    print(f"Создание заявки: {data}")
    pool = await get_pg_pool()
    
    # Получаем users.id по tg_id
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT id FROM users WHERE tg_id = $1", callback.from_user.id)
        if not user:
            await callback.message.edit_text("❌ Ошибка: пользователь не найден в базе данных.")
            await state.clear()
            return
    
    print(f"User ID: {user['id']}, tg_id: {callback.from_user.id}")
    
    try:
        order_id = await create_order(pool, user_id=user['id'], pair=data['pair'], amount=data['amount'], payout_method=data['payout_method'], contact=data['contact'])
        print(f"Заявка создана с ID: {order_id}")
        
        # Уведомляем операторов о новой заявке
        await notify_new_order(order_id, callback.from_user.id, data['amount'], data['pair'])
        
        await callback.message.edit_text("✅ Заявка отправлена оператору!")
        await state.clear()
    except Exception as e:
        print(f"Ошибка создания заявки: {e}")
        await callback.message.edit_text("❌ Ошибка при создании заявки. Попробуйте позже.")
        await state.clear()

@router.callback_query(RequestFSM.Confirm, F.data == "cancel")
async def cancel_request(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Заявка отменена.")
    await state.clear()

@router.message(Command("cancel"))
async def cancel_any(message: Message, state: FSMContext):
    await message.answer("❌ Заявка отменена.")
    await state.clear()

# BACK BUTTONS — тоже перезапускают таймаут
@router.callback_query(RequestFSM.EnterAmount, F.data == "back")
async def back_to_pair(callback: CallbackQuery, state: FSMContext):
    pairs = await get_pairs_for_fsm()
    await callback.message.edit_text("Выберите валютную пару:", reply_markup=get_pairs_keyboard(pairs))
    await state.set_state(RequestFSM.ChoosePair)
    await start_timeout(state, callback.message.chat.id, callback.bot)

@router.callback_query(RequestFSM.SelectPayout, F.data == "back")
async def back_to_amount(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    escaped_pair = escape_markdown(data.get('pair', '?'))
    await callback.message.edit_text(f"{PROGRESS[1]}\nПара выбрана: {escaped_pair}\nВведите сумму:", reply_markup=get_amount_keyboard())
    await state.set_state(RequestFSM.EnterAmount)
    await start_timeout(state, callback.message.chat.id, callback.bot)

@router.callback_query(RequestFSM.ContactInfo, F.data == "back")
async def back_to_payout(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    methods = await get_payout_methods_for_pair(data.get("pair", ""))
    await callback.message.edit_text(f"{PROGRESS[2]}\nВыберите способ выплаты:", reply_markup=get_payout_keyboard(methods))
    await state.set_state(RequestFSM.SelectPayout)
    await start_timeout(state, callback.message.chat.id, callback.bot)

@router.callback_query(RequestFSM.Confirm, F.data == "back")
async def back_to_contact(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(f"{PROGRESS[3]}\nВведите контакт (телефон в формате +79991234567 или @username):")
    await state.set_state(RequestFSM.ContactInfo)
    await start_timeout(state, callback.message.chat.id, callback.bot) 