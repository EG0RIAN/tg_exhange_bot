"""
Сервис для получения курсов клиентами
Унифицированный источник курсов из Rapira + Grinex с наценками
"""

import logging
from typing import List, Optional, Dict
from src.services.best_rate import get_best_city_rate
from src.db import get_pg_pool

logger = logging.getLogger(__name__)


async def get_available_pairs() -> List[str]:
    """
    Получает список доступных торговых пар
    Берется из fx_source_pair (единый источник правды)
    """
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT DISTINCT internal_symbol
            FROM fx_source_pair
            WHERE enabled = true
            ORDER BY internal_symbol
        """)
    return [row['internal_symbol'] for row in rows]


async def get_client_rates(city: str) -> Dict[str, Dict]:
    """
    Получает курсы для клиента с учетом его города (ОПТИМИЗИРОВАННАЯ ВЕРСИЯ)
    
    Args:
        city: Код города (moscow, rostov и т.д.)
        
    Returns:
        {
            'USDT/RUB': {
                'buy': {'rate': 82.63, 'source': 'rapira'},
                'sell': {'rate': 82.57, 'source': 'rapira'}
            },
            'BTC/USDT': {...}
        }
    """
    from src.services.rapira_simple import get_rapira_simple_client
    from decimal import Decimal
    
    # Получаем все пары
    pairs = await get_available_pairs()
    if not pairs:
        return {}
    
    # Получаем курсы для всех пар ИЗ RAPIRA ОДИН РАЗ
    client = await get_rapira_simple_client()
    base_rates = await client.get_multiple_rates(pairs)
    
    # Получаем наценки города для всех пар ОДНИМ ЗАПРОСОМ
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        # Получаем базовую наценку города (раздельно на buy/sell)
        city_data = await conn.fetchrow("""
            SELECT id, name, markup_buy, markup_sell, markup_fixed
            FROM cities
            WHERE code = $1 AND enabled = true
        """, city)
        
        if not city_data:
            logger.warning(f"City {city} not found")
            return {}
        
        # Получаем специфичные наценки для всех пар
        pair_markups = await conn.fetch("""
            SELECT pair_symbol, markup_buy, markup_sell, markup_fixed
            FROM city_pair_markups
            WHERE city_id = $1 AND enabled = true
        """, city_data['id'])
        
        # Создаем словарь наценок по парам
        markups_dict = {pm['pair_symbol']: pm for pm in pair_markups}
    
    result = {}
    
    for pair in pairs:
        base_rate_data = base_rates.get(pair)
        if not base_rate_data:
            continue
        
        # Получаем наценки для этой пары (специфичные или базовые)
        if pair in markups_dict:
            markup_buy = float(markups_dict[pair]['markup_buy'])
            markup_sell = float(markups_dict[pair]['markup_sell'])
            markup_fixed = float(markups_dict[pair]['markup_fixed'])
        else:
            markup_buy = float(city_data['markup_buy'])
            markup_sell = float(city_data['markup_sell'])
            markup_fixed = float(city_data['markup_fixed'])
        
        # Курс покупки (ask) - клиент покупает крипту
        if base_rate_data.get('best_ask'):
            buy_base = float(base_rate_data['best_ask'])
            buy_final = buy_base * (1 + markup_buy / 100) + markup_fixed
            buy_final = round(buy_final, 2)
        else:
            buy_base = None
            buy_final = None
        
        # Курс продажи (bid) - клиент продает крипту
        if base_rate_data.get('best_bid'):
            sell_base = float(base_rate_data['best_bid'])
            sell_final = sell_base * (1 + markup_sell / 100) + markup_fixed
            sell_final = round(sell_final, 2)
        else:
            sell_base = None
            sell_final = None
        
        result[pair] = {
            'buy': {
                'rate': buy_final,
                'base_rate': buy_base,
                'source': 'rapira',
                'markup': markup_buy
            },
            'sell': {
                'rate': sell_final,
                'base_rate': sell_base,
                'source': 'rapira',
                'markup': markup_sell
            }
        }
    
    return result


async def get_rate_for_order(pair: str, city: str, operation: str = "buy") -> Optional[Dict]:
    """
    Получает курс для создания заявки
    
    Args:
        pair: Пара (USDT/RUB)
        city: Город клиента
        operation: buy или sell
        
    Returns:
        {
            'rate': 82.63,
            'base_rate': 81.81,
            'source': 'rapira',
            'markup': 1.0,
            'city': 'rostov',
            'city_name': 'Ростов-на-Дону'
        }
    """
    rate_info = await get_best_city_rate(pair, city, operation)
    
    if not rate_info:
        return None
    
    return {
        'rate': rate_info['final_rate'],
        'base_rate': rate_info['base_rate'],
        'source': rate_info['best_source'],
        'markup': rate_info['markup_percent'],
        'city': rate_info['city'],
        'city_name': rate_info['city_name']
    }

