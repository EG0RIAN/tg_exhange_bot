from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.services.rates import import_rapira_rates
import logging

scheduler = AsyncIOScheduler()

async def update_rates_job():
    try:
        await import_rapira_rates()
        logging.info("[Scheduler] Курсы обновлены из Rapira")
    except Exception as e:
        logging.error(f"[Scheduler] Ошибка обновления курсов: {e}")

scheduler.add_job(update_rates_job, "interval", seconds=60)

def start_scheduler():
    scheduler.start() 