-- Миграция: Добавление колонки username в orders
-- Дата: 2025-10-14

-- Добавляем колонку username если её нет
ALTER TABLE orders ADD COLUMN IF NOT EXISTS username VARCHAR(255);

-- Комментарий
COMMENT ON COLUMN orders.username IS 'Telegram username пользователя';

-- Индекс для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_orders_username ON orders(username);

