#!/usr/bin/env python3
"""
Скрипт для исправления Telegram conflict
Сбрасывает webhook и pending updates
"""

import asyncio
import os
from aiogram import Bot

async def fix_conflict():
    # Получаем токен из docker-compose.yml или .env
    # Для тестирования используем переменную окружения
    token = os.getenv('BOT_TOKEN')
    
    if not token:
        print("❌ BOT_TOKEN не найден в переменных окружения")
        print("Укажите токен:")
        token = input().strip()
    
    print(f"🔧 Исправление Telegram conflict для бота...")
    
    bot = Bot(token=token)
    
    try:
        # Получаем информацию о webhook
        webhook_info = await bot.get_webhook_info()
        print(f"\n📊 Текущий статус:")
        print(f"   Webhook URL: {webhook_info.url or '(не установлен)'}")
        print(f"   Pending updates: {webhook_info.pending_update_count}")
        
        # Удаляем webhook и все pending updates
        print(f"\n🧹 Очистка...")
        result = await bot.delete_webhook(drop_pending_updates=True)
        
        if result:
            print("✅ Webhook удален")
            print("✅ Pending updates сброшены")
        
        # Получаем информацию о боте
        me = await bot.get_me()
        print(f"\n🤖 Бот:")
        print(f"   Username: @{me.username}")
        print(f"   ID: {me.id}")
        print(f"   Name: {me.first_name}")
        
        print("\n✅ Conflict исправлен!")
        print("   Теперь можно запустить бота в режиме polling")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(fix_conflict())

