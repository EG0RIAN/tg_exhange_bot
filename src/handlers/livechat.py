from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from src.db import get_pg_pool, start_live_chat, close_live_chat, is_live_chat_active
from src.keyboards import get_livechat_keyboard
from src.services.notifications import notify_new_chat
import os

SUPPORT_CHAT_ID = int(os.getenv("SUPPORT_CHAT_ID", "0"))

router = Router()

@router.message(F.text == "👨‍💼 Перейти к менеджеру")
async def livechat_start(message: Message, state: FSMContext):
    pool = await get_pg_pool()
    await start_live_chat(pool, message.from_user.id)
    
    # Уведомляем операторов о новом чате
    user_name = message.from_user.full_name or message.from_user.username or "Без имени"
    await notify_new_chat(message.from_user.id, user_name)
    
    # Отправляем уведомление в группу поддержки
    try:
        from aiogram import Bot
        bot = Bot(token=os.getenv("BOT_TOKEN"))
        await bot.send_message(
            SUPPORT_CHAT_ID,
            f"🆕 Новый чат!\nПользователь: {user_name}\nID: {message.from_user.id}\n\nОтправьте сообщение в ответ на это сообщение, чтобы начать диалог."
        )
        await bot.session.close()
    except Exception as e:
        print(f"Ошибка отправки уведомления в группу поддержки: {e}")
    
    await message.answer("Live-chat включён. Все ваши сообщения будут пересылаться оператору.", reply_markup=get_livechat_keyboard())

@router.callback_query(F.data == "livechat_off")
async def livechat_off(callback: CallbackQuery, state: FSMContext):
    pool = await get_pg_pool()
    await close_live_chat(pool, callback.from_user.id)
    await callback.message.edit_text("Live-chat отключён.")

@router.message(F.chat.id == SUPPORT_CHAT_ID, F.reply_to_message)
async def livechat_reply(message: Message):
    # Оператор отвечает reply на сообщение
    try:
        # Извлекаем ID пользователя из текста сообщения
        reply_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        user_id = None
        
        # Ищем ID пользователя в тексте
        if "🆔 ID:" in reply_text:
            try:
                user_id = int(reply_text.split("🆔 ID:")[1].split("\n")[0].strip())
            except Exception as e:
                pass
        
        if not user_id:
            await message.answer("❌ Не удалось определить пользователя. Ответьте на сообщение от пользователя.")
            return
        
        pool = await get_pg_pool()
        is_active = await is_live_chat_active(pool, user_id)
        
        if not is_active:
            await message.answer(f"❌ Чат с пользователем {user_id} неактивен.")
            return
        
        # Отправляем ответ пользователю
        from aiogram import Bot
        bot = Bot(token=os.getenv("BOT_TOKEN"))
        
        if message.text:
            await bot.send_message(user_id, f"👨‍💼 Оператор: {message.text}")
        elif message.photo:
            await bot.send_photo(user_id, message.photo[-1].file_id, caption=f"👨‍💼 Оператор: {message.caption or ''}")
        elif message.video:
            await bot.send_video(user_id, message.video.file_id, caption=f"👨‍💼 Оператор: {message.caption or ''}")
        elif message.document:
            await bot.send_document(user_id, message.document.file_id, caption=f"👨‍💼 Оператор: {message.caption or ''}")
        elif message.voice:
            await bot.send_voice(user_id, message.voice.file_id, caption="👨‍💼 Оператор")
        elif message.audio:
            await bot.send_audio(user_id, message.audio.file_id, caption=f"👨‍💼 Оператор: {message.caption or ''}")
        else:
            await bot.send_message(user_id, "👨‍💼 Оператор отправил сообщение")
        
        await bot.session.close()
        
        # Закрытие чата по #close
        if message.text and message.text.strip() == "#close":
            await close_live_chat(pool, user_id)
            await message.answer(f"✅ Чат с пользователем {user_id} закрыт.")
            await bot.send_message(user_id, "🔚 Чат с оператором завершен.")
            await bot.session.close()
            
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки ответа: {e}")

@router.message(F.chat.type.in_({"private"}))
async def livechat_forward(message: Message):
    # Проверяем, активен ли live-chat только для приватных чатов
    pool = await get_pg_pool()
    is_active = await is_live_chat_active(pool, message.from_user.id)
    
    if not is_active:
        return
    
    # Пересылаем в support-group
    try:
        from aiogram import Bot
        bot = Bot(token=os.getenv("BOT_TOKEN"))
        
        # Создаем информационное сообщение
        user_info = f"👤 {message.from_user.full_name or message.from_user.username or 'Без имени'}\n🆔 ID: {message.from_user.id}"
        
        # Отправляем сообщение пользователя
        if message.text:
            await bot.send_message(SUPPORT_CHAT_ID, f"{user_info}\n\n💬 {message.text}")
        elif message.photo:
            await bot.send_photo(SUPPORT_CHAT_ID, message.photo[-1].file_id, caption=f"{user_info}\n\n{message.caption or ''}")
        elif message.video:
            await bot.send_video(SUPPORT_CHAT_ID, message.video.file_id, caption=f"{user_info}\n\n{message.caption or ''}")
        elif message.document:
            await bot.send_document(SUPPORT_CHAT_ID, message.document.file_id, caption=f"{user_info}\n\n{message.caption or ''}")
        elif message.voice:
            await bot.send_voice(SUPPORT_CHAT_ID, message.voice.file_id, caption=f"{user_info}")
        elif message.audio:
            await bot.send_audio(SUPPORT_CHAT_ID, message.audio.file_id, caption=f"{user_info}\n\n{message.caption or ''}")
        else:
            await bot.send_message(SUPPORT_CHAT_ID, f"{user_info}\n\n📎 Неподдерживаемый тип сообщения")
        
        await bot.session.close()
    except Exception as e:
        print(f"Ошибка пересылки сообщения: {e}") 