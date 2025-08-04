from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from src.keyboards import get_faq_categories_keyboard, get_faq_questions_keyboard, get_faq_answer_keyboard
from src.services.faq import get_categories, get_questions, get_answer

router = Router()

# Стек навигации FAQ
FAQ_STACK = {}

@router.message(F.text == "📖 FAQ")
async def faq_start(message: Message, state: FSMContext):
    categories = await get_categories()
    if not categories:
        await message.answer("FAQ пока не настроен. Обратитесь к администратору.")
        return
    
    FAQ_STACK[message.from_user.id] = ["categories"]
    await message.answer("Выберите категорию:", reply_markup=get_faq_categories_keyboard(categories))

@router.callback_query(F.data.startswith("faq_cat:"))
async def faq_category(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split(":", 1)[1])
    questions = await get_questions(category_id)
    
    if not questions:
        await callback.answer("В этой категории пока нет вопросов.", show_alert=True)
        return
    
    user_id = callback.from_user.id
    if user_id not in FAQ_STACK:
        FAQ_STACK[user_id] = []
    FAQ_STACK[user_id].append(f"category:{category_id}")
    
    await callback.message.edit_text("Выберите вопрос:", reply_markup=get_faq_questions_keyboard(questions))

@router.callback_query(F.data.startswith("faq_q:"))
async def faq_question(callback: CallbackQuery, state: FSMContext):
    question_id = int(callback.data.split(":", 1)[1])
    answer_data = await get_answer(question_id)
    
    if not answer_data:
        await callback.answer("Ответ не найден.", show_alert=True)
        return
    
    user_id = callback.from_user.id
    if user_id not in FAQ_STACK:
        FAQ_STACK[user_id] = []
    FAQ_STACK[user_id].append(f"question:{question_id}")
    
    await callback.message.edit_text(
        f"**Вопрос:** {answer_data['question']}\n\n**Ответ:** {answer_data['answer']}", 
        reply_markup=get_faq_answer_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "faq_back")
async def faq_back(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id not in FAQ_STACK or not FAQ_STACK[user_id]:
        await callback.message.edit_text("FAQ закрыт.")
        return
    
    # Убираем текущий уровень
    FAQ_STACK[user_id].pop()
    
    if not FAQ_STACK[user_id]:
        # Вернулись к началу - показываем категории
        categories = await get_categories()
        await callback.message.edit_text("Выберите категорию:", 
                                       reply_markup=get_faq_categories_keyboard(categories))
        return
    
    # Определяем предыдущий уровень
    prev_level = FAQ_STACK[user_id][-1]
    
    if prev_level.startswith("category:"):
        category_id = int(prev_level.split(":", 1)[1])
        questions = await get_questions(category_id)
        await callback.message.edit_text("Выберите вопрос:", 
                                       reply_markup=get_faq_questions_keyboard(questions))
    else:
        # Вернулись к категориям
        categories = await get_categories()
        await callback.message.edit_text("Выберите категорию:", 
                                       reply_markup=get_faq_categories_keyboard(categories)) 