import asyncio
import logging
import structlog
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.strategy import FSMStrategy
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
import os
from src.handlers.menu import router as menu_router
from src.handlers.fsm_request import router as fsm_request_router
from src.handlers.faq import router as faq_router
from src.handlers.livechat import router as livechat_router
from src.handlers.admin import router as admin_router
from src.handlers.admin_content import router as admin_content_router
from src.handlers.settings import router as settings_router
from src.scheduler import start_scheduler

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
storage = RedisStorage.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
dp = Dispatcher(storage=storage, fsm_strategy=FSMStrategy.CHAT)

async def main():
    structlog.configure(processors=[structlog.processors.JSONRenderer()])
    logging.basicConfig(level=logging.INFO)
    start_scheduler()
    dp.include_router(menu_router)
    dp.include_router(fsm_request_router)
    dp.include_router(faq_router)
    dp.include_router(settings_router)
    dp.include_router(livechat_router)
    dp.include_router(admin_router)
    dp.include_router(admin_content_router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 