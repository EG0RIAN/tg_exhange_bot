-- Расширенная схема для управления контентом

-- Способы выплаты
CREATE TABLE IF NOT EXISTS payout_methods (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  type VARCHAR(20) NOT NULL, -- card, crypto, cash
  is_active BOOLEAN DEFAULT TRUE,
  sort_order INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Торговые пары с детальной информацией
CREATE TABLE IF NOT EXISTS trading_pairs (
  id BIGSERIAL PRIMARY KEY,
  base_currency VARCHAR(10) NOT NULL,
  quote_currency VARCHAR(10) NOT NULL,
  base_name TEXT NOT NULL, -- например "USD (Cash LA)"
  quote_name TEXT NOT NULL, -- например "RUB (Card)"
  is_active BOOLEAN DEFAULT TRUE,
  sort_order INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(base_currency, quote_currency)
);

-- Курсы для разных объемов
CREATE TABLE IF NOT EXISTS rate_tiers (
  id BIGSERIAL PRIMARY KEY,
  pair_id BIGINT REFERENCES trading_pairs(id),
  min_amount NUMERIC(18,2) NOT NULL,
  max_amount NUMERIC(18,2),
  rate NUMERIC(18,8) NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Уведомления для операторов
CREATE TABLE IF NOT EXISTS operator_notifications (
  id BIGSERIAL PRIMARY KEY,
  type VARCHAR(50) NOT NULL, -- new_chat, new_order, etc.
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  is_read BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Добавляем данные по умолчанию
INSERT INTO payout_methods (name, type, sort_order) VALUES 
  ('Карта РФ', 'card', 1),
  ('Карта EU', 'card', 2),
  ('Bitcoin', 'crypto', 3),
  ('USDT', 'crypto', 4),
  ('Наличные Москва', 'cash', 5),
  ('Наличные LA', 'cash', 6)
ON CONFLICT DO NOTHING;

INSERT INTO trading_pairs (base_currency, quote_currency, base_name, quote_name, sort_order) VALUES 
  ('USD', 'RUB', 'USD (Cash LA)', 'RUB (Card)', 1),
  ('USD', 'RUB', 'USD (Cash LA)', 'RUB (Cash Moscow)', 2)
ON CONFLICT DO NOTHING;

-- Добавляем курсы по умолчанию
INSERT INTO rate_tiers (pair_id, min_amount, rate) 
SELECT tp.id, 100, 74.80 FROM trading_pairs tp WHERE tp.base_name = 'USD (Cash LA)' AND tp.quote_name = 'RUB (Card)'
UNION ALL
SELECT tp.id, 500, 75.60 FROM trading_pairs tp WHERE tp.base_name = 'USD (Cash LA)' AND tp.quote_name = 'RUB (Card)'
UNION ALL
SELECT tp.id, 1500, 76.30 FROM trading_pairs tp WHERE tp.base_name = 'USD (Cash LA)' AND tp.quote_name = 'RUB (Card)'
UNION ALL
SELECT tp.id, 5000, 76.70 FROM trading_pairs tp WHERE tp.base_name = 'USD (Cash LA)' AND tp.quote_name = 'RUB (Card)'
UNION ALL
SELECT tp.id, 10000, 76.70 FROM trading_pairs tp WHERE tp.base_name = 'USD (Cash LA)' AND tp.quote_name = 'RUB (Card)'
UNION ALL
SELECT tp.id, 10000, 76.70 FROM trading_pairs tp WHERE tp.base_name = 'USD (Cash LA)' AND tp.quote_name = 'RUB (Cash Moscow)'; 