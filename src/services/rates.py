async def get_pairs():
    # TODO: брать из БД
    return ["USD_RUB", "BTC_USDT", "EUR_USDT"]

async def get_all_rates(page=1, page_size=10):
    from src.db import get_pg_pool
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM rates ORDER BY id LIMIT $1 OFFSET $2", page_size, (page-1)*page_size)
        total = await conn.fetchval("SELECT count(*) FROM rates")
        rates = [{"id": row["id"], "pair": row["pair"], "bid": row["bid"], "ask": row["ask"]} for row in rows]
        return rates, page, total 

async def update_rate(rate_id, ask, bid):
    from src.db import get_pg_pool
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE rates SET ask=$1, bid=$2, source='manual', updated_at=now() WHERE id=$3", ask, bid, rate_id)

async def add_rate(pair, ask, bid):
    from src.db import get_pg_pool
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO rates (pair, ask, bid, source, updated_at) VALUES ($1, $2, $3, 'manual', now()) ON CONFLICT (pair) DO NOTHING", pair, ask, bid)

async def import_rapira_rates():
    from src.db import get_pg_pool
    from src.services.rapira import get_rates
    pool = await get_pg_pool()
    # Получаем все пары из БД
    async with pool.acquire() as conn:
        pairs = [row["pair"] for row in await conn.fetch("SELECT pair FROM rates")]
    rapira = await get_rates(pairs)
    async with pool.acquire() as conn:
        for pair, data in rapira.items():
            await conn.execute("UPDATE rates SET ask=$1, bid=$2, source='rapira', updated_at=now() WHERE pair=$3", data['ask'], data['bid'], pair)

async def get_payout_methods(pair: str):
    # В реальности — фильтрация по паре
    return ["Карта РФ", "Карта EU", "Crypto-addr", "Cash"]            