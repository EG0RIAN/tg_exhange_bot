import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from src.services.rapira import get_rapira_provider
from src.services.rates import import_rapira_rates, get_rapira_health_status

logger = logging.getLogger(__name__)

class RatesScheduler:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._is_running = False
        self._update_interval = 5  # секунды
        self._last_update = None
        self._update_count = 0
        self._error_count = 0
        self._last_error = None
    
    async def start(self, update_interval: int = 5):
        """Запускает планировщик обновления курсов"""
        if self._is_running:
            logger.warning("Rates scheduler is already running")
            return
        
        self._update_interval = update_interval
        self._is_running = True
        
        logger.info(f"Starting rates scheduler with {update_interval}s interval")
        
        self._task = asyncio.create_task(self._scheduler_loop())
        
        # Первое обновление сразу
        await self._update_rates()
    
    async def stop(self):
        """Останавливает планировщик"""
        if not self._is_running:
            return
        
        self._is_running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Rates scheduler stopped")
    
    async def _scheduler_loop(self):
        """Основной цикл планировщика"""
        while self._is_running:
            try:
                await asyncio.sleep(self._update_interval)
                
                if self._is_running:
                    await self._update_rates()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                self._error_count += 1
                self._last_error = str(e)
                await asyncio.sleep(1)  # Пауза перед следующей попыткой
    
    async def _update_rates(self):
        """Выполняет обновление курсов"""
        try:
            start_time = datetime.now()
            
            logger.debug("Starting rates update from Rapira")
            
            # Обновляем курсы
            updated_count = await import_rapira_rates()
            
            # Обновляем статистику
            self._last_update = start_time
            self._update_count += 1
            
            if updated_count > 0:
                logger.info(f"Successfully updated {updated_count} rates from Rapira")
            else:
                logger.warning("No rates were updated from Rapira")
                
        except Exception as e:
            logger.error(f"Failed to update rates: {e}")
            self._error_count += 1
            self._last_error = str(e)
    
    async def force_update(self) -> Dict[str, Any]:
        """Принудительно обновляет курсы"""
        try:
            start_time = datetime.now()
            
            logger.info("Force updating rates from Rapira")
            
            updated_count = await import_rapira_rates()
            
            # Обновляем статистику
            self._last_update = start_time
            self._update_count += 1
            
            if updated_count > 0:
                logger.info(f"Force update: successfully updated {updated_count} rates from Rapira")
            else:
                logger.warning("Force update: no rates were updated from Rapira")
            
            return {
                "success": True,
                "updated_count": updated_count,
                "timestamp": start_time.isoformat()
            }
                
        except Exception as e:
            logger.error(f"Force update failed: {e}")
            self._error_count += 1
            self._last_error = str(e)
            
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            self._last_update = start_time
            self._update_count += 1
            
            return {
                "success": True,
                "updated_count": updated_count,
                "timestamp": start_time.isoformat(),
                "duration_ms": (datetime.now() - start_time).total_seconds() * 1000
            }
            
        except Exception as e:
            logger.error(f"Force update failed: {e}")
            self._error_count += 1
            self._last_error = str(e)
            
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус планировщика"""
        return {
            "is_running": self._is_running,
            "update_interval": self._update_interval,
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "update_count": self._update_count,
            "error_count": self._error_count,
            "last_error": self._last_error
        }
    
    async def get_full_status(self) -> Dict[str, Any]:
        """Возвращает полный статус включая здоровье Rapira API"""
        try:
            rapira_health = await get_rapira_health_status()
            
            status = self.get_status()
            status["rapira_health"] = rapira_health
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get full status: {e}")
            status = self.get_status()
            status["rapira_health"] = {"error": str(e)}
            return status

# Глобальный экземпляр планировщика
_scheduler = None

async def get_rates_scheduler() -> RatesScheduler:
    """Получает глобальный экземпляр планировщика"""
    global _scheduler
    if not _scheduler:
        _scheduler = RatesScheduler()
    return _scheduler

async def start_rates_scheduler(update_interval: int = 5):
    """Запускает глобальный планировщик курсов"""
    scheduler = await get_rates_scheduler()
    await scheduler.start(update_interval)

async def stop_rates_scheduler():
    """Останавливает глобальный планировщик курсов"""
    scheduler = await get_rates_scheduler()
    await scheduler.stop()

async def force_update_rates() -> Dict[str, Any]:
    """Принудительно обновляет курсы"""
    scheduler = await get_rates_scheduler()
    return await scheduler.force_update()

async def get_scheduler_status() -> Dict[str, Any]:
    """Получает статус планировщика"""
    scheduler = await get_rates_scheduler()
    return await scheduler.get_full_status()
