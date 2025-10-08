import logging
from typing import Dict, Optional, List
from src.services.rates_calculator import (
    get_rates_calculator, 
    calculate_exchange_rate, 
    OperationType,
    RateCalculation
)

logger = logging.getLogger(__name__)

async def get_pairs():
    """Получает список доступных торговых пар"""
    # TODO: брать из БД
    return ["USDT/RUB", "BTC/USDT", "EUR/USDT"]

async def get_all_rates(page=1, page_size=10):
    """Получает все курсы с пагинацией"""
    from src.db import get_pg_pool
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM rates ORDER BY id LIMIT $1 OFFSET $2", page_size, (page-1)*page_size)
        total = await conn.fetchval("SELECT count(*) FROM rates")
        rates = [{"id": row["id"], "pair": row["pair"], "bid": row["bid"], "ask": row["ask"]} for row in rows]
        return rates, page, total 

async def update_rate(rate_id, ask, bid):
    """Обновляет курс вручную"""
    from src.db import get_pg_pool
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE rates SET ask=$1, bid=$2, source='manual', updated_at=now() WHERE id=$3", ask, bid, rate_id)

async def add_rate(pair, ask, bid):
    """Добавляет новый курс"""
    from src.db import get_pg_pool
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO rates (pair, ask, bid, source, updated_at) VALUES ($1, $2, $3, 'manual', now()) ON CONFLICT (pair) DO NOTHING", pair, ask, bid)

async def import_rapira_rates():
    """Импортирует курсы из Rapira API"""
    from src.db import get_pg_pool
    from src.services.rapira import get_rapira_provider
    
    try:
        provider = await get_rapira_provider()
        pool = await get_pg_pool()
        
        # Получаем все пары из БД
        async with pool.acquire() as conn:
            pairs = [row["pair"] for row in await conn.fetch("SELECT pair FROM rates")]
        
        updated_count = 0
        for pair in pairs:
            try:
                # Получаем актуальные курсы
                cash_in_rate = await calculate_exchange_rate(pair, OperationType.CASH_IN)
                cash_out_rate = await calculate_exchange_rate(pair, OperationType.CASH_OUT)
                
                # Обновляем БД
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE rates SET ask=$1, bid=$2, source='rapira', updated_at=now() WHERE pair=$3",
                        cash_out_rate.final_rate,  # ask для продажи USDT
                        cash_in_rate.final_rate,   # bid для покупки USDT
                        pair
                    )
                    updated_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to import rate for {pair}: {e}")
                continue
        
        logger.info(f"Successfully imported {updated_count}/{len(pairs)} rates from Rapira")
        return updated_count
        
    except Exception as e:
        logger.error(f"Failed to import Rapira rates: {e}")
        return 0

async def get_payout_methods(pair: str):
    """Получает доступные методы выплат для пары"""
    # В реальности — фильтрация по паре
    return ["Карта РФ", "Карта EU", "Crypto-addr", "Cash"]

async def get_current_rate(
    pair: str,
    operation: OperationType,
    amount_usd: Optional[float] = None,
    location: str = "moscow",
    use_vwap: bool = False
) -> RateCalculation:
    """
    Получает текущий курс для операции
    
    Args:
        pair: Торговая пара
        operation: Тип операции (CASH_IN или CASH_OUT)
        amount_usd: Сумма в USD для VWAP
        location: Локация
        use_vwap: Использовать VWAP
    
    Returns:
        RateCalculation с деталями курса
    """
    try:
        return await calculate_exchange_rate(
            pair=pair,
            operation=operation,
            amount_usd=amount_usd,
            location=location,
            use_vwap=use_vwap
        )
    except Exception as e:
        logger.error(f"Failed to get current rate for {pair} {operation.value}: {e}")
        raise

async def get_rates_for_pairs(
    pairs: List[str],
    operation: OperationType,
    location: str = "moscow"
) -> Dict[str, RateCalculation]:
    """
    Получает курсы для нескольких пар одновременно
    
    Args:
        pairs: Список торговых пар
        operation: Тип операции
        location: Локация
    
    Returns:
        Словарь {pair: RateCalculation}
    """
    rates = {}
    calculator = await get_rates_calculator()
    
    for pair in pairs:
        try:
            rate = await calculator.calculate_rate(
                pair=pair,
                operation=operation,
                location=location
            )
            rates[pair] = rate
        except Exception as e:
            logger.error(f"Failed to get rate for {pair}: {e}")
            continue
    
    return rates

async def get_rapira_health_status() -> Dict:
    """Получает статус здоровья Rapira API"""
    try:
        calculator = await get_rates_calculator()
        return calculator.get_health_status()
    except Exception as e:
        logger.error(f"Failed to get Rapira health status: {e}")
        return {
            "provider": "rapira",
            "status": "error",
            "error": str(e)
        }

async def calculate_vwap_rate(
    pair: str,
    operation: OperationType,
    amount_usd: float,
    location: str = "moscow"
) -> RateCalculation:
    """
    Рассчитывает VWAP курс для заданной суммы
    
    Args:
        pair: Торговая пара
        operation: Тип операции
        amount_usd: Сумма в USD
        location: Локация
    
    Returns:
        RateCalculation с VWAP курсом
    """
    try:
        return await calculate_exchange_rate(
            pair=pair,
            operation=operation,
            amount_usd=amount_usd,
            location=location,
            use_vwap=True
        )
    except Exception as e:
        logger.error(f"Failed to calculate VWAP rate for {pair}: {e}")
        raise 