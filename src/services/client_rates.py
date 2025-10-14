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
    Получает курсы для клиента с учетом его города
    
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
    pairs = await get_available_pairs()
    result = {}
    
    for pair in pairs:
        try:
            # Курс покупки
            buy_rate = await get_best_city_rate(pair, city, "buy")
            # Курс продажи
            sell_rate = await get_best_city_rate(pair, city, "sell")
            
            if buy_rate and sell_rate:
                result[pair] = {
                    'buy': {
                        'rate': buy_rate['final_rate'],
                        'base_rate': buy_rate['base_rate'],
                        'source': buy_rate['best_source'],
                        'markup': buy_rate['markup_percent']
                    },
                    'sell': {
                        'rate': sell_rate['final_rate'],
                        'base_rate': sell_rate['base_rate'],
                        'source': sell_rate['best_source'],
                        'markup': sell_rate['markup_percent']
                    }
                }
        except Exception as e:
            logger.error(f"Failed to get rates for {pair} in city {city}: {e}")
            result[pair] = {
                'buy': {'rate': None, 'error': str(e)},
                'sell': {'rate': None, 'error': str(e)}
            }
    
    return result


async def format_rates_for_display(city: str, city_name: str) -> str:
    """
    Форматирует курсы для отображения клиенту
    
    Args:
        city: Код города
        city_name: Название города
        
    Returns:
        Отформатированная строка с курсами
    """
    rates = await get_client_rates(city)
    
    if not rates:
        return "Курсы временно недоступны. Попробуйте позже."
    
    from datetime import datetime
    text = f"💱 **Курсы для города: {city_name}**\n\n"
    
    for pair, rate_data in rates.items():
        text += f"**{pair}:**\n"
        
        buy_rate = rate_data.get('buy', {})
        sell_rate = rate_data.get('sell', {})
        
        if buy_rate.get('rate'):
            text += f"  Покупка: {buy_rate['rate']:.2f} ₽\n"
        else:
            text += f"  Покупка: _недоступен_\n"
        
        if sell_rate.get('rate'):
            text += f"  Продажа: {sell_rate['rate']:.2f} ₽\n"
        else:
            text += f"  Продажа: _недоступен_\n"
        
        # Показываем источник лучшего курса
        source = buy_rate.get('source', 'unknown').upper()
        text += f"  _Источник: {source}_\n"
        
        # Показываем наценку если она есть
        markup = buy_rate.get('markup', 0)
        if markup > 0:
            text += f"  _Наценка города: +{markup}%_\n"
        
        text += "\n"
    
    text += f"_Обновлено: {datetime.now().strftime('%H:%M')}_\n"
    text += f"_Курсы указаны для вашего города_"
    
    return text


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

