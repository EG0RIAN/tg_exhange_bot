"""
Модуль кэширования для оптимизации запросов к БД
"""

import asyncio
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TTLCache:
    """Простой кэш с TTL (Time To Live)"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша"""
        async with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Проверяем TTL
            if datetime.now() > entry['expires_at']:
                del self._cache[key]
                logger.debug(f"Cache expired for key: {key}")
                return None
            
            logger.debug(f"Cache hit for key: {key}")
            return entry['value']
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 60):
        """Сохранить значение в кэш с TTL"""
        async with self._lock:
            self._cache[key] = {
                'value': value,
                'expires_at': datetime.now() + timedelta(seconds=ttl_seconds),
                'created_at': datetime.now()
            }
            logger.debug(f"Cache set for key: {key}, TTL: {ttl_seconds}s")
    
    async def delete(self, key: str):
        """Удалить значение из кэша"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache deleted for key: {key}")
    
    async def clear(self):
        """Очистить весь кэш"""
        async with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")
    
    async def clear_expired(self):
        """Удалить все истекшие записи"""
        async with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now > entry['expires_at']
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.info(f"Cleared {len(expired_keys)} expired cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику кэша"""
        return {
            'total_entries': len(self._cache),
            'entries': [
                {
                    'key': key,
                    'created_at': entry['created_at'].isoformat(),
                    'expires_at': entry['expires_at'].isoformat(),
                    'ttl_remaining': int((entry['expires_at'] - datetime.now()).total_seconds())
                }
                for key, entry in self._cache.items()
            ]
        }


# Глобальный экземпляр кэша
_global_cache: Optional[TTLCache] = None


def get_cache() -> TTLCache:
    """Получить глобальный кэш"""
    global _global_cache
    if _global_cache is None:
        _global_cache = TTLCache()
    return _global_cache


async def cached_query(
    key: str,
    query_func: Callable,
    ttl_seconds: int = 60,
    force_refresh: bool = False
) -> Any:
    """
    Декоратор для кэширования результатов запросов
    
    Args:
        key: Ключ кэша
        query_func: Async функция для выполнения запроса
        ttl_seconds: Время жизни кэша в секундах
        force_refresh: Принудительно обновить кэш
        
    Returns:
        Результат запроса (из кэша или свежий)
    """
    cache = get_cache()
    
    if not force_refresh:
        cached_value = await cache.get(key)
        if cached_value is not None:
            return cached_value
    
    # Выполняем запрос
    logger.debug(f"Cache miss for key: {key}, executing query...")
    result = await query_func()
    
    # Сохраняем в кэш
    await cache.set(key, result, ttl_seconds)
    
    return result


# Периодическая очистка истекших записей
async def start_cache_cleaner(interval_seconds: int = 300):
    """Запускает периодическую очистку истекших записей кэша"""
    cache = get_cache()
    
    while True:
        await asyncio.sleep(interval_seconds)
        await cache.clear_expired()

