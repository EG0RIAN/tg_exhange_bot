import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.strategy import FSMStrategy
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
import os
from src.handlers.menu import router as menu_router
from src.handlers.buy_usdt import router as buy_usdt_router
from src.handlers.sell_usdt import router as sell_usdt_router
from src.handlers.pay_invoice import router as pay_invoice_router
from src.handlers.faq import router as faq_router
from src.handlers.livechat import router as livechat_router
from src.handlers.admin import router as admin_router
from src.handlers.admin_content import router as admin_content_router
from src.handlers.admin_grinex import router as admin_grinex_router
from src.handlers.settings import router as settings_router
from src.scheduler import start_scheduler
from src.services.fx_scheduler import start_fx_scheduler, stop_fx_scheduler

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
storage = RedisStorage.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
dp = Dispatcher(storage=storage, fsm_strategy=FSMStrategy.CHAT)

async def main():
    # Инициализация улучшенного логирования
    from src.utils.logger import setup_logging
    log_level = os.getenv("LOG_LEVEL", "INFO")
    setup_logging(level=log_level, colored=True)
    
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 Starting Telegram bot with log level: {log_level}")
    
    start_scheduler()
    
    # Запускаем планировщик курсов FX
    await start_fx_scheduler()
    
    # FSM роутеры должны быть первыми (приоритет)
    dp.include_router(buy_usdt_router)
    dp.include_router(sell_usdt_router)
    dp.include_router(pay_invoice_router)
    
    # Обычные роутеры
    dp.include_router(menu_router)
    dp.include_router(faq_router)
    dp.include_router(settings_router)
    dp.include_router(livechat_router)
    
    # Админ роутеры
    dp.include_router(admin_router)
    dp.include_router(admin_content_router)
    dp.include_router(admin_grinex_router)
    
    try:
        await dp.start_polling(bot)
    finally:
        # Останавливаем планировщик при завершении
        await stop_fx_scheduler()

if __name__ == "__main__":
    asyncio.run(main()) 