from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import os
from src.services.rates import get_all_rates, update_rate, add_rate, import_rapira_rates
from src.keyboards import get_admin_menu_keyboard, get_rates_list_keyboard, get_admin_integrations_keyboard
from aiogram.fsm.state import StatesGroup, State
from src.services.faq import add_category, get_questions_in_category, add_question, update_question, delete_question, get_category_name
from src.keyboards import get_admin_faq_categories_keyboard, get_admin_faq_questions_keyboard, get_admin_faq_edit_keyboard
from src.services.orders import get_orders, get_order, update_order_status
from src.keyboards import get_admin_orders_keyboard, get_admin_order_status_keyboard
from src.services.broadcast import broadcast_message
from src.keyboards import get_broadcast_keyboard, get_broadcast_confirm_keyboard
from src.services.logs import get_logs
from src.keyboards import get_logs_filter_keyboard

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

router = Router()

# ACL фильтр
async def is_admin(obj):
    user_id = obj.from_user.id if hasattr(obj, 'from_user') else obj.message.from_user.id
    return user_id in ADMIN_IDS

@router.message(F.text == "/admin")
async def admin_menu(message: Message):
    if not await is_admin(message):
        await message.answer("Доступ запрещён.")
        return
    await message.answer("Админ-панель:", reply_markup=get_admin_menu_keyboard())

@router.callback_query(F.data == "admin_rates")
async def admin_rates(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    rates, page, total = await get_all_rates(page=1)
    await callback.message.edit_text(f"Курсы (стр. {page}):", reply_markup=get_rates_list_keyboard(rates, page, total))

@router.callback_query(F.data.startswith("admin_rates_page:"))
async def admin_rates_page(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    page = int(callback.data.split(":", 1)[1])
    rates, page, total = await get_all_rates(page=page)
    await callback.message.edit_text(f"Курсы (стр. {page}):", reply_markup=get_rates_list_keyboard(rates, page, total))

class RateEditFSM(StatesGroup):
    EditAsk = State()
    EditBid = State()
    AddPair = State()
    AddAsk = State()
    AddBid = State()

# --- Редактирование курса ---
@router.callback_query(F.data.startswith("admin_rate:"))
async def admin_rate_edit(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    rate_id = int(callback.data.split(":", 1)[1])
    await state.update_data(rate_id=rate_id)
    await callback.message.edit_text("Введите новое значение Ask:")
    await state.set_state(RateEditFSM.EditAsk)

@router.message(RateEditFSM.EditAsk)
async def admin_rate_edit_ask(message: Message, state: FSMContext):
    await state.update_data(ask=message.text)
    await message.answer("Введите новое значение Bid:")
    await state.set_state(RateEditFSM.EditBid)

@router.message(RateEditFSM.EditBid)
async def admin_rate_edit_bid(message: Message, state: FSMContext):
    data = await state.get_data()
    await update_rate(data['rate_id'], data['ask'], message.text)
    await message.answer("Курс обновлён.")
    await state.clear()

# --- Добавление курса ---
@router.callback_query(F.data == "admin_rate_add")
async def admin_rate_add(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите новую пару (например, BTC_USDT):")
    await state.set_state(RateEditFSM.AddPair)

@router.message(RateEditFSM.AddPair)
async def admin_rate_add_pair(message: Message, state: FSMContext):
    await state.update_data(pair=message.text)
    await message.answer("Введите Ask:")
    await state.set_state(RateEditFSM.AddAsk)

@router.message(RateEditFSM.AddAsk)
async def admin_rate_add_ask(message: Message, state: FSMContext):
    await state.update_data(ask=message.text)
    await message.answer("Введите Bid:")
    await state.set_state(RateEditFSM.AddBid)

@router.message(RateEditFSM.AddBid)
async def admin_rate_add_bid(message: Message, state: FSMContext):
    data = await state.get_data()
    await add_rate(data['pair'], data['ask'], message.text)
    await message.answer("Курс добавлен.")
    await state.clear()

# --- Импорт Rapira ---
@router.callback_query(F.data == "admin_rate_import")
async def admin_rate_import(callback: CallbackQuery, state: FSMContext):
    await import_rapira_rates()
    await callback.message.edit_text("Курсы обновлены из Rapira.") 

class FaqEditFSM(StatesGroup):
    AddCategory = State()
    AddQuestion = State()
    AddAnswer = State()
    EditQuestion = State()
    EditAnswer = State()

@router.callback_query(F.data == "admin_faq")
async def admin_faq(callback: CallbackQuery, state: FSMContext):
    # Список категорий
    from src.services.faq import get_categories
    categories = await get_categories()
    await callback.message.edit_text("Категории FAQ:", reply_markup=get_admin_faq_categories_keyboard(categories))

@router.callback_query(F.data == "admin_faq_cat_add")
async def admin_faq_cat_add(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите название новой категории:")
    await state.set_state(FaqEditFSM.AddCategory)

@router.message(FaqEditFSM.AddCategory)
async def admin_faq_cat_add_save(message: Message, state: FSMContext):
    await add_category(message.text)
    await message.answer("Категория добавлена.")
    await state.clear()

@router.callback_query(F.data.startswith("admin_faq_cat:"))
async def admin_faq_cat(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split(":", 1)[1])
    questions = await get_questions_in_category(category_id)
    category_name = await get_category_name(category_id)
    await callback.message.edit_text(f"Вопросы категории '{category_name}':", reply_markup=get_admin_faq_questions_keyboard(questions, category_id))
    await state.update_data(category_id=category_id)

@router.callback_query(F.data.startswith("admin_faq_q_add:"))
async def admin_faq_q_add(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split(":", 1)[1])
    await state.update_data(category_id=category_id)
    await callback.message.edit_text("Введите текст вопроса:")
    await state.set_state(FaqEditFSM.AddQuestion)

@router.message(FaqEditFSM.AddQuestion)
async def admin_faq_q_add_question(message: Message, state: FSMContext):
    await state.update_data(question=message.text)
    await message.answer("Введите ответ:")
    await state.set_state(FaqEditFSM.AddAnswer)

@router.message(FaqEditFSM.AddAnswer)
async def admin_faq_q_add_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    await add_question(data['category_id'], data['question'], message.text)
    await message.answer("Вопрос добавлен.")
    await state.clear()

@router.callback_query(F.data.startswith("admin_faq_q:"))
async def admin_faq_q_edit(callback: CallbackQuery, state: FSMContext):
    qid = int(callback.data.split(":", 1)[1])
    from src.services.faq import get_answer
    answer = await get_answer(qid)
    await state.update_data(faq_id=qid)
    await callback.message.edit_text(f"Редактирование вопроса (id={qid}):\n{answer}", reply_markup=get_admin_faq_edit_keyboard(qid))
    await state.set_state(FaqEditFSM.EditQuestion)

@router.callback_query(F.data.startswith("admin_faq_del:"))
async def admin_faq_q_delete(callback: CallbackQuery, state: FSMContext):
    qid = int(callback.data.split(":", 1)[1])
    await delete_question(qid)
    await callback.message.edit_text("Вопрос удалён.")
    await state.clear() 

@router.callback_query(F.data == "admin_orders")
async def admin_orders(callback: CallbackQuery, state: FSMContext):
    orders, page, total = await get_orders(page=1)
    await callback.message.edit_text("Заявки:", reply_markup=get_admin_orders_keyboard(orders, page, total))

@router.callback_query(F.data.startswith("admin_orders_page:"))
async def admin_orders_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":", 1)[1])
    orders, page, total = await get_orders(page=page)
    await callback.message.edit_text("Заявки:", reply_markup=get_admin_orders_keyboard(orders, page, total))

@router.callback_query(F.data.startswith("admin_order:"))
async def admin_order_view(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split(":", 1)[1])
    order = await get_order(order_id)
    if not order:
        await callback.message.edit_text("Заявка не найдена.")
        return
    text = f"Заявка #{order['id']}\nПара: {order['pair']}\nСумма: {order['amount']}\nВыплата: {order['payout_method']}\nКонтакт: {order['contact']}\nСтатус: {order['status']}"
    await callback.message.edit_text(text, reply_markup=get_admin_order_status_keyboard(order_id, order['status']))

@router.callback_query(F.data.startswith("admin_order_status:"))
async def admin_order_status(callback: CallbackQuery, state: FSMContext):
    _, _, order_id, status = callback.data.split(":", 3)
    await update_order_status(int(order_id), status)
    await callback.message.edit_text(f"Статус заявки обновлён на {status}.") 

class BroadcastFSM(StatesGroup):
    Draft = State()
    Preview = State()

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите текст рассылки:")
    await state.set_state(BroadcastFSM.Draft)

@router.message(BroadcastFSM.Draft)
async def admin_broadcast_draft(message: Message, state: FSMContext):
    await state.update_data(broadcast_text=message.text)
    await message.answer("Черновик сохранён. Предпросмотр:", reply_markup=get_broadcast_keyboard())
    await state.set_state(BroadcastFSM.Preview)

@router.callback_query(F.data == "admin_broadcast_preview")
async def admin_broadcast_preview(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    await callback.message.edit_text(f"Предпросмотр рассылки:\n{text}", reply_markup=get_broadcast_confirm_keyboard())

@router.callback_query(F.data == "admin_broadcast_send")
async def admin_broadcast_send(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    # Получаем bot из callback
    await broadcast_message(callback.bot, text)
    await callback.message.edit_text("Рассылка отправлена.")
    await state.clear() 

@router.callback_query(F.data == "admin_logs")
async def admin_logs(callback: CallbackQuery, state: FSMContext):
    logs = await get_logs(level="error")
    text = "\n".join([f"[{l['created_at']:%Y-%m-%d %H:%M}] {l['level'].upper()}: {l['message'][:80]}" for l in logs]) or "Нет ошибок."
    await callback.message.edit_text(f"Последние ошибки:\n{text}", reply_markup=get_logs_filter_keyboard())

@router.callback_query(F.data.startswith("admin_logs_"))
async def admin_logs_level(callback: CallbackQuery, state: FSMContext):
    level = callback.data.split("_", 2)[-1]
    logs = await get_logs(level=level)
    text = "\n".join([f"[{l['created_at']:%Y-%m-%d %H:%M}] {l['level'].upper()}: {l['message'][:80]}" for l in logs]) or "Нет записей."
    await callback.message.edit_text(f"Последние {level} логи:\n{text}", reply_markup=get_logs_filter_keyboard())

# --- Интеграции ---
@router.callback_query(F.data == "admin_integrations")
async def admin_integrations(callback: CallbackQuery):
    """Показывает меню интеграций"""
    if not await is_admin(callback):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    
    text = "🌐 **Интеграции с биржами**\n\n"
    text += "Выберите интеграцию для управления:"
    
    await callback.message.edit_text(text, reply_markup=get_admin_integrations_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data == "admin_grinex")
async def admin_grinex_redirect(callback: CallbackQuery):
    """Перенаправляет на статус Grinex"""
    if not await is_admin(callback):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    
    # Импортируем функцию из admin_grinex
    from src.handlers.admin_grinex import cmd_grinex_status
    await cmd_grinex_status(callback.message)

@router.callback_query(F.data == "admin_city_rates")
async def admin_city_rates_redirect(callback: CallbackQuery):
    """Перенаправляет на универсальную панель управления курсами"""
    if not await is_admin(callback):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    
    text = "💱 **Управление курсами**\n\n"
    text += "Универсальная панель для управления:\n"
    text += "• Текущими курсами\n"
    text += "• Городскими наценками\n"
    text += "• Источниками данных (Rapira, Grinex)\n\n"
    text += "📊 **Логика:**\n"
    text += "1. Базовый курс из Rapira/Grinex\n"
    text += "2. Применяем наценку города\n"
    text += "3. Отдаем финальный курс\n\n"
    text += "**Web Admin:**\n"
    text += "http://localhost:8000/admin/rates-management\n\n"
    text += "**Примеры наценок:**\n"
    text += "• Москва: 0% (базовый)\n"
    text += "• Ростов: +1%\n"
    text += "• Нижний Новгород: +0.8%\n"
    text += "• СПб: +0.3%"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_integrations")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data == "admin_fx_system")
async def admin_fx_system(callback: CallbackQuery):
    """Показывает статус FX системы"""
    if not await is_admin(callback):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return
    
    from src.services.fx_scheduler import get_fx_scheduler
    
    scheduler = await get_fx_scheduler()
    status = scheduler.get_status()
    
    text = "📊 **FX Rates System Status**\n\n"
    text += f"**Планировщик:** {'🟢 Работает' if status['running'] else '🔴 Остановлен'}\n\n"
    
    if status['last_sync']:
        text += "**Последние синхронизации:**\n"
        for source, time in status['last_sync'].items():
            text += f"• {source}: {time}\n"
    
    if status['config']:
        text += f"\n**Настройки:**\n"
        text += f"• Интервал: {status['config']['update_interval_seconds']}s\n"
        text += f"• Stale threshold: {status['config']['stale_threshold_seconds']}s\n"
    
    text += f"\n**Web Admin:** http://localhost:8000/admin/rates-management"
    text += f"\n\n💱 Универсальная панель управления курсами"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_integrations")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown") 