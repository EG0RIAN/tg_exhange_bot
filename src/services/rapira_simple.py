"""
Упрощенный клиент Rapira - получение базовых курсов
с последующим применением наценок по городам
"""

import os
import httpx
import asyncio
import logging
from typing import Dict, Optional
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)

# Конфигурация
RAPIRA_API_BASE = os.getenv("RAPIRA_API_BASE", "https://api.rapira.net")
RAPIRA_TIMEOUT = int(os.getenv("RAPIRA_TIMEOUT", 10))
RAPIRA_MAX_RETRIES = int(os.getenv("RAPIRA_MAX_RETRIES", 3))


class RapiraSimpleClient:
    """Упрощенный клиент для Rapira - только получение базовых курсов"""
    
    def __init__(self):
        self.base_url = RAPIRA_API_BASE
        self._error_count = 0
        self._last_error = None
    
    async def get_base_rate(self, symbol: str) -> Optional[Dict]:
        """
        Получает базовый курс (московский) из Rapira
        
        Args:
            symbol: Символ пары, например "USDT/RUB"
            
        Returns:
            {
                'symbol': 'USDT/RUB',
                'best_ask': 81.83,  # цена покупки (клиент покупает USDT)
                'best_bid': 81.50,  # цена продажи (клиент продает USDT)
                'timestamp': datetime
            }
        """
        try:
            url = f"{self.base_url}/market/exchange-plate-mini"
            params = {"symbol": symbol}
            
            async with httpx.AsyncClient(timeout=RAPIRA_TIMEOUT) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            # Извлекаем лучшие цены
            result = {
                'symbol': symbol,
                'best_ask': None,
                'best_bid': None,
                'timestamp': datetime.now()
            }
            
            # Best Ask - цена по которой клиент может купить USDT (самая низкая ask)
            # Берем из items[0], т.к. lowestPrice может быть placeholder (99999)
            if 'ask' in data and 'items' in data['ask'] and len(data['ask']['items']) > 0:
                result['best_ask'] = Decimal(str(data['ask']['items'][0]['price']))
            elif 'ask' in data and 'lowestPrice' in data['ask']:
                price = Decimal(str(data['ask']['lowestPrice']))
                # Игнорируем явные placeholder значения
                if price < 90000:
                    result['best_ask'] = price
            
            # Best Bid - цена по которой клиент может продать USDT (самая высокая bid)
            # Берем из items[0], т.к. highestPrice может быть placeholder
            if 'bid' in data and 'items' in data['bid'] and len(data['bid']['items']) > 0:
                result['best_bid'] = Decimal(str(data['bid']['items'][0]['price']))
            elif 'bid' in data and 'highestPrice' in data['bid']:
                result['best_bid'] = Decimal(str(data['bid']['highestPrice']))
            
            self._error_count = 0
            self._last_error = None
            
            logger.info(f"Rapira base rate for {symbol}: ask={result['best_ask']}, bid={result['best_bid']}")
            return result
            
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            logger.error(f"Failed to get Rapira base rate for {symbol}: {e}")
            return None
    
    async def get_multiple_rates(self, symbols: list[str]) -> Dict[str, Dict]:
        """
        Получает базовые курсы для нескольких пар
        
        Args:
            symbols: Список символов, например ["USDT/RUB", "BTC/USDT"]
            
        Returns:
            {'USDT/RUB': {...}, 'BTC/USDT': {...}}
        """
        results = {}
        
        for symbol in symbols:
            rate = await self.get_base_rate(symbol)
            if rate:
                results[symbol] = rate
            # Небольшая пауза между запросами
            await asyncio.sleep(0.1)
        
        return results
    
    def get_error_count(self) -> int:
        """Возвращает количество ошибок"""
        return self._error_count
    
    def get_last_error(self) -> Optional[str]:
        """Возвращает последнюю ошибку"""
        return self._last_error


# Глобальный экземпляр
_rapira_simple_client: Optional[RapiraSimpleClient] = None


async def get_rapira_simple_client() -> RapiraSimpleClient:
    """Получает глобальный экземпляр упрощенного клиента"""
    global _rapira_simple_client
    if not _rapira_simple_client:
        _rapira_simple_client = RapiraSimpleClient()
    return _rapira_simple_client


async def get_city_rate(symbol: str, city: str, operation: str = "buy") -> Optional[Dict]:
    """
    Получает курс для конкретного города с наценкой
    
    Args:
        symbol: Пара, например "USDT/RUB"
        city: Город, например "moscow", "rostov", "nizhniy_novgorod"
        operation: Тип операции "buy" (клиент покупает) или "sell" (клиент продает)
        
    Returns:
        {
            'symbol': 'USDT/RUB',
            'city': 'rostov',
            'base_rate': 81.83,
            'markup_percent': 1.0,
            'final_rate': 82.65,
            'operation': 'buy',
            'timestamp': datetime
        }
    """
    from src.db import get_pg_pool
    
    # Получаем базовый курс
    client = await get_rapira_simple_client()
    base_data = await client.get_base_rate(symbol)
    
    if not base_data:
        logger.error(f"Failed to get base rate for {symbol}")
        return None
    
    # Выбираем базовую цену в зависимости от операции
    if operation == "buy":
        # Клиент покупает USDT - берем ask (цена продавца)
        base_rate = base_data['best_ask']
    else:
        # Клиент продает USDT - берем bid (цена покупателя)
        base_rate = base_data['best_bid']
    
    if not base_rate:
        logger.error(f"No base rate available for {symbol} operation {operation}")
        return None
    
    # Получаем наценку для города из таблицы cities
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        city_data = await conn.fetchrow("""
            SELECT markup_percent, markup_fixed
            FROM cities
            WHERE code = $1 AND enabled = true
            LIMIT 1
        """, city)
        
        if city_data:
            markup_percent = Decimal(str(city_data['markup_percent']))
            markup_fixed = Decimal(str(city_data['markup_fixed']))
        else:
            # Дефолтная наценка если город не найден
            logger.warning(f"City {city} not found in DB, using default 0%")
            markup_percent = Decimal('0')
            markup_fixed = Decimal('0')
    
    # Применяем наценку
    # Формула: final = base * (1 + percent/100) + fixed
    final_rate = base_rate * (Decimal('1') + markup_percent / Decimal('100')) + markup_fixed
    
    # Округляем до 2 знаков
    final_rate = final_rate.quantize(Decimal('0.01'))
    
    result = {
        'symbol': symbol,
        'city': city,
        'base_rate': float(base_rate),
        'markup_percent': float(markup_percent),
        'markup_fixed': float(markup_fixed),
        'final_rate': float(final_rate),
        'operation': operation,
        'timestamp': base_data['timestamp']
    }
    
    logger.info(f"City rate for {city}: {symbol} {operation} = {final_rate} (base: {base_rate}, markup: {markup_percent}%)")
    
    return result


# Кэш городов
_cities_cache = None
_cities_cache_time = None

async def get_cities_dict() -> Dict[str, str]:
    """
    Получает словарь городов из БД с кэшированием
    
    Returns:
        {'moscow': 'Москва', 'rostov': 'Ростов-на-Дону', ...}
    """
    global _cities_cache, _cities_cache_time
    
    # Кэш на 60 секунд
    if _cities_cache and _cities_cache_time:
        if (datetime.now() - _cities_cache_time).total_seconds() < 60:
            return _cities_cache
    
    from src.db import get_pg_pool
    
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT code, name 
            FROM cities 
            WHERE enabled = true
            ORDER BY sort_order, name
        """)
        
        _cities_cache = {r['code']: r['name'] for r in rows}
        _cities_cache_time = datetime.now()
        
        return _cities_cache

# Для обратной совместимости - статичный словарь как fallback
CITIES = {
    'moscow': 'Москва',
    'rostov': 'Ростов-на-Дону',
    'nizhniy_novgorod': 'Нижний Новгород',
    'spb': 'Санкт-Петербург',
    'ekaterinburg': 'Екатеринбург',
    'kazan': 'Казань',
    'other': 'Другие города'
}


async def setup_city_markups():
    """
    Создает начальные правила наценки для городов
    Запускается один раз при инициализации
    """
    from src.db import get_pg_pool
    
    default_markups = {
        'moscow': 0.0,          # Москва - базовый курс (0%)
        'spb': 0.3,             # СПб - +0.3%
        'rostov': 1.0,          # Ростов - +1%
        'nizhniy_novgorod': 0.8, # Нижний Новгород - +0.8%
        'ekaterinburg': 0.7,    # Екатеринбург - +0.7%
        'kazan': 0.9,           # Казань - +0.9%
        'other': 1.5            # Другие города - +1.5%
    }
    
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        for city_code, markup_percent in default_markups.items():
            city_name = CITIES.get(city_code, city_code)
            
            # Проверяем, есть ли уже правило
            existing = await conn.fetchrow("""
                SELECT id FROM fx_markup_rule
                WHERE description ILIKE $1
                LIMIT 1
            """, f"%город: {city_code}%")
            
            if not existing:
                await conn.execute("""
                    INSERT INTO fx_markup_rule 
                    (level, percent, fixed, enabled, description, rounding_mode, round_to)
                    VALUES ('global', $1, 0, true, $2, 'ROUND_HALF_UP', 2)
                """, markup_percent, f"Наценка для города: {city_code} ({city_name})")
                
                logger.info(f"Created markup rule for {city_name}: {markup_percent}%")

