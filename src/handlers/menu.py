from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from src.keyboards import main_menu, get_trading_pairs_keyboard, get_rates_back_keyboard
from src.i18n import _, detect_user_lang
from src.db import get_pg_pool
from src.services.content import format_rates_display, get_pairs_for_fsm, get_trading_pairs, get_rate_tiers_for_pair
from src.services.faq import get_categories

router = Router()

@router.message(F.text == "/start")
async def menu_start(message: Message):
    pool = await get_pg_pool()
    lang = await detect_user_lang(message.from_user, db_pool=pool)
    await message.answer(_("start_message", lang=lang), reply_markup=main_menu)

# Обработчик FAQ перенесен в src/handlers/faq.py

@router.message(F.text == "💱 Курсы")
async def menu_rates(message: Message):
    pool = await get_pg_pool()
    lang = await detect_user_lang(message.from_user, db_pool=pool)
    pairs = await get_trading_pairs()
    
    if not pairs:
        await message.answer(_("no_rates_available", lang=lang))
        return
    
    await message.answer(
        _("select_trading_pair", lang=lang), 
        reply_markup=get_trading_pairs_keyboard(pairs)
    )

@router.callback_query(F.data.startswith("rates_pair:"))
async def show_pair_rates(callback: CallbackQuery):
    pair_id = int(callback.data.split(":", 1)[1])
    pool = await get_pg_pool()
    lang = await detect_user_lang(callback.from_user, db_pool=pool)
    
    # Получаем данные пары и курсы
    pairs = await get_trading_pairs()
    pair = next((p for p in pairs if p['id'] == pair_id), None)
    
    if not pair:
        await callback.answer(_("pair_not_found", lang=lang), show_alert=True)
        return
    
    tiers = await get_rate_tiers_for_pair(pair_id)
    
    if not tiers:
        await callback.answer(_("no_rates_for_pair", lang=lang), show_alert=True)
        return
    
    # Формируем текст с курсами
    from datetime import datetime
    today = datetime.now().strftime("%d %B")
    
    rates_text = f"**{today}**\n\n"
    rates_text += f"**{pair['base_name']} ➡️ {pair['quote_name']}:**\n"
    
    for tier in tiers:
        amount = f"${tier['min_amount']:,}".replace(',', ' ')
        rates_text += f"➖От {amount} ➡️ {tier['rate']}\n"
    
    await callback.message.edit_text(
        rates_text, 
        parse_mode="Markdown",
        reply_markup=get_rates_back_keyboard()
    )

@router.callback_query(F.data == "rates_back")
async def rates_back(callback: CallbackQuery):
    pool = await get_pg_pool()
    lang = await detect_user_lang(callback.from_user, db_pool=pool)
    pairs = await get_trading_pairs()
    
    await callback.message.edit_text(
        _("select_trading_pair", lang=lang), 
        reply_markup=get_trading_pairs_keyboard(pairs)
    )

# Обработчик менеджера перенесен в src/handlers/livechat.py

# Обработчик настроек перенесен в src/handlers/settings.py

@router.message(Command("health"))
async def cmd_health(message: Message):
    await message.answer("✅ Bot is alive!") 