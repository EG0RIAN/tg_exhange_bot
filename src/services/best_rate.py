"""
Сервис получения лучшего курса из Rapira + Grinex с наценкой по городу
"""

import logging
from decimal import Decimal
from typing import Optional, Dict
from src.services.rapira_simple import get_city_rate, get_rapira_simple_client
from src.services.grinex import get_grinex_client

logger = logging.getLogger(__name__)


async def get_best_city_rate(symbol: str, city: str, operation: str = "buy") -> Optional[Dict]:
    """
    Получает лучший курс из Rapira + Grinex с применением наценки города
    
    Args:
        symbol: Пара, например "USDT/RUB"
        city: Код города (moscow, rostov, nizhniy_novgorod и т.д.)
        operation: "buy" (клиент покупает) или "sell" (клиент продает)
        
    Returns:
        {
            'symbol': 'USDT/RUB',
            'city': 'rostov',
            'city_name': 'Ростов-на-Дону',
            'best_source': 'rapira',  # или 'grinex'
            'base_rate': 81.83,
            'final_rate': 82.65,
            'markup_percent': 1.0,
            'operation': 'buy',
            'rapira_rate': 81.83,     # для сравнения
            'grinex_rate': 81.85,     # для сравнения
            'timestamp': datetime
        }
    """
    
    rapira_rate = None
    grinex_rate = None
    base_rate = None
    best_source = None
    rapira_timestamp = None
    
    # Получаем курс из Rapira
    try:
        rapira_client = await get_rapira_simple_client()
        rapira_data = await rapira_client.get_base_rate(symbol)
        if rapira_data:
            rapira_timestamp = rapira_data.get('timestamp')
            # Для buy берем ask, для sell берем bid
            if operation == "buy" and rapira_data['best_ask']:
                rapira_rate = float(rapira_data['best_ask'])
            elif operation == "sell" and rapira_data['best_bid']:
                rapira_rate = float(rapira_data['best_bid'])
    except Exception as e:
        logger.warning(f"Failed to get Rapira rate: {e}")
    
    # Получаем курс из Grinex
    try:
        grinex_client = await get_grinex_client()
        
        # Преобразуем символ для Grinex (USDT/RUB → USDTRUB)
        grinex_symbol = symbol.replace("/", "")
        
        ticker = await grinex_client.get_ticker(grinex_symbol)
        if ticker:
            # Для buy берем ask, для sell берем bid
            if operation == "buy" and ticker.ask:
                grinex_rate = float(ticker.ask)
            elif operation == "sell" and ticker.bid:
                grinex_rate = float(ticker.bid)
            elif ticker.last_price:
                # Fallback на last_price
                grinex_rate = float(ticker.last_price)
    except Exception as e:
        logger.warning(f"Failed to get Grinex rate: {e}")
    
    # Выбираем лучший курс
    if operation == "buy":
        # Для покупки - чем ниже цена, тем лучше
        if rapira_rate and grinex_rate:
            if rapira_rate <= grinex_rate:
                base_rate = rapira_rate
                best_source = "rapira"
            else:
                base_rate = grinex_rate
                best_source = "grinex"
        elif rapira_rate:
            base_rate = rapira_rate
            best_source = "rapira"
        elif grinex_rate:
            base_rate = grinex_rate
            best_source = "grinex"
    else:
        # Для продажи - чем выше цена, тем лучше
        if rapira_rate and grinex_rate:
            if rapira_rate >= grinex_rate:
                base_rate = rapira_rate
                best_source = "rapira"
            else:
                base_rate = grinex_rate
                best_source = "grinex"
        elif rapira_rate:
            base_rate = rapira_rate
            best_source = "rapira"
        elif grinex_rate:
            base_rate = grinex_rate
            best_source = "grinex"
    
    if not base_rate:
        logger.error(f"No rates available for {symbol}")
        return None
    
    # Применяем наценку города из таблицы cities (раздельно на buy/sell)
    from src.db import get_pg_pool
    
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        city_data = await conn.fetchrow("""
            SELECT markup_buy, markup_sell, markup_fixed
            FROM cities
            WHERE code = $1 AND enabled = true
            LIMIT 1
        """, city)
        
        if city_data:
            # Выбираем наценку в зависимости от операции
            if operation == "buy":
                markup_percent = float(city_data['markup_buy'])
            else:
                markup_percent = float(city_data['markup_sell'])
            markup_fixed = float(city_data['markup_fixed'])
        else:
            logger.warning(f"City {city} not found in DB, using 0%")
            markup_percent = 0.0
            markup_fixed = 0.0
    
    # Применяем формулу
    final_rate = base_rate * (1 + markup_percent / 100) + markup_fixed
    # Округляем до 2 знаков
    final_rate = round(final_rate, 2)
    
    from src.services.rapira_simple import CITIES
    city_name = CITIES.get(city, city)
    
    return {
        'symbol': symbol,
        'city': city,
        'city_name': city_name,
        'best_source': best_source,
        'base_rate': base_rate,
        'final_rate': final_rate,
        'markup_percent': markup_percent,
        'markup_fixed': markup_fixed,
        'operation': operation,
        'rapira_rate': rapira_rate,
        'grinex_rate': grinex_rate,
        'timestamp': rapira_timestamp
    }

