import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.services.rates_scheduler import start_rates_scheduler, get_scheduler_status
from src.services.rates import import_rapira_rates

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

async def update_rates_job():
    """Legacy job для совместимости"""
    try:
        await import_rapira_rates()
        logger.info("[Scheduler] Курсы обновлены из Rapira (legacy)")
    except Exception as e:
        logger.error(f"[Scheduler] Ошибка обновления курсов (legacy): {e}")

async def start_rapira_scheduler():
    """Запускает планировщик Rapira API"""
    try:
        await start_rates_scheduler(update_interval=5)  # 5 секунд
        logger.info("[Scheduler] Rapira rates scheduler запущен")
    except Exception as e:
        logger.error(f"[Scheduler] Ошибка запуска Rapira scheduler: {e}")

async def get_rapira_scheduler_status():
    """Получает статус планировщика Rapira"""
    try:
        status = await get_scheduler_status()
        logger.info(f"[Scheduler] Rapira scheduler status: {status}")
        return status
    except Exception as e:
        logger.error(f"[Scheduler] Ошибка получения статуса Rapira scheduler: {e}")
        return None

# Добавляем legacy job (можно отключить позже)
scheduler.add_job(update_rates_job, "interval", seconds=60)

def start_scheduler():
    """Запускает все планировщики"""
    try:
        # Запускаем legacy scheduler
        scheduler.start()
        logger.info("[Scheduler] Legacy scheduler запущен")
        
        # Запускаем Rapira scheduler в отдельной задаче
        asyncio.create_task(start_rapira_scheduler())
        
    except Exception as e:
        logger.error(f"[Scheduler] Ошибка запуска планировщиков: {e}")

async def stop_scheduler():
    """Останавливает все планировщики"""
    try:
        scheduler.shutdown()
        logger.info("[Scheduler] Legacy scheduler остановлен")
        
        # Останавливаем Rapira scheduler
        from src.services.rates_scheduler import stop_rates_scheduler
        await stop_rates_scheduler()
        
    except Exception as e:
        logger.error(f"[Scheduler] Ошибка остановки планировщиков: {e}") 