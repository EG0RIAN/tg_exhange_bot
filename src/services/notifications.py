from src.db import get_pg_pool
import os

SUPPORT_CHAT_ID = int(os.getenv("SUPPORT_CHAT_ID", "0"))

async def notify_new_chat(user_id: int, user_name: str = None):
    """Уведомить операторов о новом чате"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO operator_notifications (type, title, message)
            VALUES ($1, $2, $3)
            """,
            "new_chat",
            "Новый чат",
            f"Пользователь {user_id} ({user_name or 'Без имени'}) начал чат"
        )

async def notify_new_order(order_id: int, user_id: int, amount: str, pair: str):
    """Уведомить операторов о новой заявке"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO operator_notifications (type, title, message)
            VALUES ($1, $2, $3)
            """,
            "new_order",
            "Новая заявка",
            f"Заявка #{order_id}: {amount} {pair} от пользователя {user_id}"
        )

async def get_unread_notifications():
    """Получить непрочитанные уведомления"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM operator_notifications WHERE is_read=false ORDER BY created_at DESC"
        )
        return [dict(row) for row in rows]

async def mark_notification_read(notification_id: int):
    """Отметить уведомление как прочитанное"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE operator_notifications SET is_read=true WHERE id=$1",
            notification_id
        ) 