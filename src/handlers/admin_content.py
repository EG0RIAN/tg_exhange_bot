from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from src.db import get_pg_pool
from src.keyboards import get_admin_content_keyboard, get_trading_pairs_keyboard, get_rate_tiers_keyboard
import os

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

router = Router()

# ACL фильтр
async def is_admin(obj):
    user_id = obj.from_user.id if hasattr(obj, 'from_user') else obj.message.from_user.id
    return user_id in ADMIN_IDS

class ContentEditFSM(StatesGroup):
    AddPairBase = State()
    AddPairQuote = State()
    AddPairBaseName = State()
    AddPairQuoteName = State()
    AddRateTier = State()
    AddRateAmount = State()
    AddRateValue = State()
    AddPayoutMethod = State()
    AddPayoutType = State()

# --- Управление торговыми парами ---
@router.callback_query(F.data == "admin_content")
async def admin_content_menu(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    await callback.message.edit_text("Управление контентом:", reply_markup=get_admin_content_keyboard())

@router.callback_query(F.data == "admin_trading_pairs")
async def admin_trading_pairs(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        pairs = await conn.fetch("SELECT * FROM trading_pairs ORDER BY sort_order, id")
    
    text = "**Торговые пары:**\n"
    for pair in pairs:
        status = "✅" if pair['is_active'] else "❌"
        text += f"{status} {pair['base_name']} ➡️ {pair['quote_name']}\n"
    
    await callback.message.edit_text(text, reply_markup=get_trading_pairs_keyboard(pairs))

@router.callback_query(F.data == "admin_add_pair")
async def admin_add_pair_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите базовую валюту (например, USD):")
    await state.set_state(ContentEditFSM.AddPairBase)

@router.message(ContentEditFSM.AddPairBase)
async def admin_add_pair_base(message: Message, state: FSMContext):
    await state.update_data(base_currency=message.text.upper())
    await message.answer("Введите котируемую валюту (например, RUB):")
    await state.set_state(ContentEditFSM.AddPairQuote)

@router.message(ContentEditFSM.AddPairQuote)
async def admin_add_pair_quote(message: Message, state: FSMContext):
    await state.update_data(quote_currency=message.text.upper())
    await message.answer("Введите название базовой валюты (например, USD (Cash LA)):")
    await state.set_state(ContentEditFSM.AddPairBaseName)

@router.message(ContentEditFSM.AddPairBaseName)
async def admin_add_pair_base_name(message: Message, state: FSMContext):
    await state.update_data(base_name=message.text)
    await message.answer("Введите название котируемой валюты (например, RUB (Card)):")
    await state.set_state(ContentEditFSM.AddPairQuoteName)

@router.message(ContentEditFSM.AddPairQuoteName)
async def admin_add_pair_quote_name(message: Message, state: FSMContext):
    data = await state.get_data()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO trading_pairs (base_currency, quote_currency, base_name, quote_name)
            VALUES ($1, $2, $3, $4)
            """,
            data['base_currency'], data['quote_currency'], data['base_name'], message.text
        )
    await message.answer("Торговая пара добавлена!")
    await state.clear()

# --- Управление курсами ---
@router.callback_query(F.data.startswith("admin_pair_rates:"))
async def admin_pair_rates(callback: CallbackQuery, state: FSMContext):
    pair_id = int(callback.data.split(":", 1)[1])
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        pair = await conn.fetchrow("SELECT * FROM trading_pairs WHERE id=$1", pair_id)
        tiers = await conn.fetch("SELECT * FROM rate_tiers WHERE pair_id=$1 ORDER BY min_amount", pair_id)
    
    text = f"**Курсы для {pair['base_name']} ➡️ {pair['quote_name']}:**\n"
    for tier in tiers:
        status = "✅" if tier['is_active'] else "❌"
        text += f"{status} От ${tier['min_amount']:,} ➡️ {tier['rate']}\n"
    
    await callback.message.edit_text(text, reply_markup=get_rate_tiers_keyboard(pair_id, tiers))

@router.callback_query(F.data.startswith("admin_add_rate:"))
async def admin_add_rate_start(callback: CallbackQuery, state: FSMContext):
    pair_id = int(callback.data.split(":", 1)[1])
    await state.update_data(pair_id=pair_id)
    await callback.message.edit_text("Введите минимальную сумму (например, 100):")
    await state.set_state(ContentEditFSM.AddRateAmount)

@router.message(ContentEditFSM.AddRateAmount)
async def admin_add_rate_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
        await state.update_data(min_amount=amount)
        await message.answer("Введите курс (например, 74.80):")
        await state.set_state(ContentEditFSM.AddRateValue)
    except ValueError:
        await message.answer("Некорректная сумма. Попробуйте снова:")

@router.message(ContentEditFSM.AddRateValue)
async def admin_add_rate_value(message: Message, state: FSMContext):
    try:
        rate = float(message.text)
        data = await state.get_data()
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO rate_tiers (pair_id, min_amount, rate) VALUES ($1, $2, $3)",
                data['pair_id'], data['min_amount'], rate
            )
        await message.answer("Курс добавлен!")
        await state.clear()
    except ValueError:
        await message.answer("Некорректный курс. Попробуйте снова:")

# --- Управление способами выплаты ---
@router.callback_query(F.data == "admin_payout_methods")
async def admin_payout_methods(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        methods = await conn.fetch("SELECT * FROM payout_methods ORDER BY sort_order, id")
    
    text = "**Способы выплаты:**\n"
    for method in methods:
        status = "✅" if method['is_active'] else "❌"
        text += f"{status} {method['name']} ({method['type']})\n"
    
    await callback.message.edit_text(text, reply_markup=None) 