from src.db import get_pg_pool

async def get_orders(status=None, page=1, page_size=10):
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if status:
            rows = await conn.fetch("SELECT * FROM orders WHERE status=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3", status, page_size, (page-1)*page_size)
            total = await conn.fetchval("SELECT count(*) FROM orders WHERE status=$1", status)
        else:
            rows = await conn.fetch("SELECT * FROM orders ORDER BY created_at DESC LIMIT $1 OFFSET $2", page_size, (page-1)*page_size)
            total = await conn.fetchval("SELECT count(*) FROM orders")
        orders = [dict(row) for row in rows]
        return orders, page, total

async def get_order(order_id):
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM orders WHERE id=$1", order_id)
        return dict(row) if row else None

async def update_order_status(order_id, status):
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE orders SET status=$1 WHERE id=$2", status, order_id) 