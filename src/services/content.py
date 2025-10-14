from src.db import get_pg_pool
from datetime import datetime

async def get_trading_pairs():
    """Получить все активные торговые пары"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM trading_pairs WHERE is_active=true ORDER BY sort_order, id"
        )
        return [dict(row) for row in rows]

async def get_rate_tiers_for_pair(pair_id):
    """Получить курсы для торговой пары"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT DISTINCT min_amount, rate FROM rate_tiers WHERE pair_id=$1 AND is_active=true ORDER BY min_amount",
            pair_id
        )
        return [dict(row) for row in rows]

async def get_payout_methods():
    """Получить все активные способы выплаты"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM payout_methods WHERE is_active=true ORDER BY sort_order, id"
        )
        return [dict(row) for row in rows]

async def format_rates_display():
    """Форматировать курсы для отображения пользователю"""
    pairs = await get_trading_pairs()
    result = []
    
    today = datetime.now().strftime("%d %B")
    result.append(f"**{today}**\n")
    
    for pair in pairs:
        tiers = await get_rate_tiers_for_pair(pair['id'])
        if tiers:
            result.append(f"**{pair['base_name']} ➡️ {pair['quote_name']}:**")
            for tier in tiers:
                amount = f"${tier['min_amount']:,}".replace(',', ' ')
                result.append(f"➖От {amount} ➡️ {tier['rate']}")
            result.append("")
    
    return "\n".join(result)

async def get_pairs_for_fsm():
    """Получить пары для FSM из fx_source_pair (унифицированный источник)"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        # Получаем уникальные internal_symbol из fx_source_pair
        rows = await conn.fetch("""
            SELECT DISTINCT internal_symbol
            FROM fx_source_pair
            WHERE enabled = true
            ORDER BY internal_symbol
        """)
        return [row['internal_symbol'] for row in rows]

async def get_payout_methods_for_pair(pair_code):
    """Получить способы выплаты для пары"""
    methods = await get_payout_methods()
    # В реальности здесь может быть логика фильтрации по паре
    return [m['name'] for m in methods] 