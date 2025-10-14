"""
Планировщик синхронизации валютных курсов
"""

import os
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.services.fx_rates import get_fx_service
from src.db import get_pg_pool

logger = logging.getLogger(__name__)

# Конфигурация
FX_UPDATE_INTERVAL_SECONDS = int(os.getenv("FX_UPDATE_INTERVAL_SECONDS", 60))
FX_STALE_CHECK_INTERVAL = int(os.getenv("FX_STALE_CHECK_INTERVAL", 300))  # 5 минут
FX_STALE_THRESHOLD_SECONDS = int(os.getenv("FX_STALE_THRESHOLD_SECONDS", 180))  # 3 минуты


class FXRatesScheduler:
    """Планировщик обновления курсов"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._running = False
        self._last_sync: dict = {}  # {source_code: datetime}
    
    async def start(self):
        """Запускает планировщик"""
        if self._running:
            logger.warning("FX scheduler already running")
            return
        
        logger.info(f"Starting FX rates scheduler with {FX_UPDATE_INTERVAL_SECONDS}s interval")
        
        # Добавляем задачу синхронизации всех источников
        self.scheduler.add_job(
            self._sync_all_sources,
            trigger=IntervalTrigger(seconds=FX_UPDATE_INTERVAL_SECONDS),
            id='fx_sync_all',
            name='Sync all FX sources',
            replace_existing=True,
            max_instances=1  # Не запускать параллельно
        )
        
        # Добавляем задачу проверки устаревших данных
        self.scheduler.add_job(
            self._check_stale_rates,
            trigger=IntervalTrigger(seconds=FX_STALE_CHECK_INTERVAL),
            id='fx_check_stale',
            name='Check stale FX rates',
            replace_existing=True,
            max_instances=1
        )
        
        # Запускаем планировщик
        self.scheduler.start()
        self._running = True
        
        # Выполняем первую синхронизацию сразу
        asyncio.create_task(self._sync_all_sources())
        
        logger.info("FX rates scheduler started successfully")
    
    async def stop(self):
        """Останавливает планировщик"""
        if not self._running:
            return
        
        logger.info("Stopping FX rates scheduler")
        self.scheduler.shutdown(wait=False)
        self._running = False
        logger.info("FX rates scheduler stopped")
    
    async def _sync_all_sources(self):
        """Синхронизирует все активные источники"""
        try:
            fx_service = await get_fx_service()
            pool = await get_pg_pool()
            
            # Получаем список активных источников
            async with pool.acquire() as conn:
                sources = await conn.fetch("SELECT code, name FROM fx_source WHERE enabled = true")
            
            if not sources:
                logger.warning("No enabled FX sources found")
                return
            
            # Синхронизируем каждый источник
            for source in sources:
                source_code = source['code']
                try:
                    logger.debug(f"Syncing FX source: {source_code}")
                    result = await fx_service.sync_source_rates(source_code)
                    
                    self._last_sync[source_code] = datetime.now()
                    
                    if result['status'] == 'success':
                        logger.info(
                            f"FX sync {source_code}: {result['pairs_succeeded']}/{result['pairs_processed']} pairs, "
                            f"{result['duration_ms']}ms"
                        )
                    elif result['status'] == 'partial':
                        logger.warning(
                            f"FX sync {source_code} partial: {result['pairs_succeeded']}/{result['pairs_processed']} succeeded, "
                            f"{result['pairs_failed']} failed"
                        )
                    else:
                        logger.error(f"FX sync {source_code} failed: {result.get('errors', [])}")
                
                except Exception as e:
                    logger.error(f"Failed to sync FX source {source_code}: {e}", exc_info=True)
            
        except Exception as e:
            logger.error(f"Failed to sync FX sources: {e}", exc_info=True)
    
    async def _check_stale_rates(self):
        """Проверяет и помечает устаревшие курсы"""
        try:
            pool = await get_pg_pool()
            
            async with pool.acquire() as conn:
                # Помечаем курсы как stale если они старше порога
                result = await conn.execute(f"""
                    UPDATE fx_final_rate
                    SET stale = true
                    WHERE stale = false 
                        AND calculated_at < NOW() - INTERVAL '{FX_STALE_THRESHOLD_SECONDS} seconds'
                """)
                
                # Парсим результат (формат: "UPDATE N")
                rows_updated = int(result.split()[-1]) if result else 0
                
                if rows_updated > 0:
                    logger.warning(f"Marked {rows_updated} FX rates as stale")
                    
                    # Логируем какие пары устарели
                    stale_rates = await conn.fetch("""
                        SELECT s.code, sp.internal_symbol, fr.calculated_at
                        FROM fx_final_rate fr
                        JOIN fx_source s ON s.id = fr.source_id
                        JOIN fx_source_pair sp ON sp.id = fr.source_pair_id
                        WHERE fr.stale = true
                        ORDER BY fr.calculated_at
                        LIMIT 10
                    """)
                    
                    for rate in stale_rates:
                        logger.warning(
                            f"Stale rate: {rate['code']}/{rate['internal_symbol']} "
                            f"(last update: {rate['calculated_at']})"
                        )
        
        except Exception as e:
            logger.error(f"Failed to check stale rates: {e}", exc_info=True)
    
    async def trigger_sync(self, source_code: str = None):
        """Принудительно запускает синхронизацию"""
        if source_code:
            logger.info(f"Triggering manual FX sync for: {source_code}")
            fx_service = await get_fx_service()
            return await fx_service.sync_source_rates(source_code)
        else:
            logger.info("Triggering manual FX sync for all sources")
            await self._sync_all_sources()
            return {"status": "triggered"}
    
    def get_status(self) -> dict:
        """Возвращает статус планировщика"""
        jobs = []
        if self._running:
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None
                })
        
        return {
            'running': self._running,
            'jobs': jobs,
            'last_sync': {
                code: dt.isoformat() for code, dt in self._last_sync.items()
            },
            'config': {
                'update_interval_seconds': FX_UPDATE_INTERVAL_SECONDS,
                'stale_check_interval': FX_STALE_CHECK_INTERVAL,
                'stale_threshold_seconds': FX_STALE_THRESHOLD_SECONDS
            }
        }


# Глобальный экземпляр планировщика
_fx_scheduler: FXRatesScheduler = None


async def get_fx_scheduler() -> FXRatesScheduler:
    """Получает глобальный экземпляр планировщика"""
    global _fx_scheduler
    if not _fx_scheduler:
        _fx_scheduler = FXRatesScheduler()
    return _fx_scheduler


async def start_fx_scheduler():
    """Запускает планировщик курсов"""
    scheduler = await get_fx_scheduler()
    await scheduler.start()


async def stop_fx_scheduler():
    """Останавливает планировщик курсов"""
    global _fx_scheduler
    if _fx_scheduler:
        await _fx_scheduler.stop()
        _fx_scheduler = None

