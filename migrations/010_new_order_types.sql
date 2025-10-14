-- Миграция: Новая структура заявок для трех путей
-- Дата: 2025-10-14

-- Добавляем новые колонки в таблицу orders
ALTER TABLE orders ADD COLUMN IF NOT EXISTS order_type VARCHAR(20);  -- buy_usdt, sell_usdt, pay_invoice
ALTER TABLE orders ADD COLUMN IF NOT EXISTS country VARCHAR(50);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method VARCHAR(20);  -- cash, usdt
ALTER TABLE orders ADD COLUMN IF NOT EXISTS purpose VARCHAR(50);  -- services, goods, delivery, other
ALTER TABLE orders ADD COLUMN IF NOT EXISTS invoice_file_id VARCHAR(255);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS invoice_file_type VARCHAR(20);  -- photo, document
ALTER TABLE orders ADD COLUMN IF NOT EXISTS currency VARCHAR(10);  -- RUB, USD, EUR, etc

-- Комментарии
COMMENT ON COLUMN orders.order_type IS 'Тип заявки: buy_usdt, sell_usdt, pay_invoice';
COMMENT ON COLUMN orders.country IS 'Код страны';
COMMENT ON COLUMN orders.payment_method IS 'Способ оплаты для инвойсов: cash или usdt';
COMMENT ON COLUMN orders.purpose IS 'Цель оплаты инвойса';
COMMENT ON COLUMN orders.invoice_file_id IS 'Telegram file_id прикрепленного инвойса';
COMMENT ON COLUMN orders.invoice_file_type IS 'Тип файла инвойса: photo или document';
COMMENT ON COLUMN orders.currency IS 'Валюта для обмена (RUB, USD, EUR и т.п.)';

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_orders_order_type ON orders(order_type);
CREATE INDEX IF NOT EXISTS idx_orders_country ON orders(country);
CREATE INDEX IF NOT EXISTS idx_orders_currency ON orders(currency);

