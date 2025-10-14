-- Модуль "Валютные курсы" с интеграцией бирж и наценками
-- Миграция 004: FX Rates System

-- Источники (биржи)
CREATE TABLE IF NOT EXISTS fx_source (
  id SERIAL PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,      -- 'grinex', 'rapira'
  name TEXT NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  auth_type TEXT NOT NULL DEFAULT 'public', -- 'public'|'hmac'|'bearer'
  api_base_url TEXT,              -- базовый URL API
  config JSONB DEFAULT '{}',      -- дополнительная конфигурация (таймауты, ретраи и т.д.)
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Пары источника (маппинг на нашу систему)
CREATE TABLE IF NOT EXISTS fx_source_pair (
  id SERIAL PRIMARY KEY,
  source_id INT NOT NULL REFERENCES fx_source(id) ON DELETE CASCADE,
  source_symbol TEXT NOT NULL,            -- напр. 'usdtrub', 'BTCUSDT'
  base_currency TEXT NOT NULL,            -- 'USDT', 'BTC'
  quote_currency TEXT NOT NULL,           -- 'RUB', 'USDT'
  internal_symbol TEXT NOT NULL,          -- наш код: 'USDT/RUB', 'BTC/USDT'
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  config JSONB DEFAULT '{}',              -- доп. параметры (precision и т.д.)
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_id, source_symbol)
);

-- Сырые курсы (последние значения)
CREATE TABLE IF NOT EXISTS fx_raw_rate (
  id BIGSERIAL PRIMARY KEY,
  source_id INT NOT NULL REFERENCES fx_source(id) ON DELETE CASCADE,
  source_pair_id INT NOT NULL REFERENCES fx_source_pair(id) ON DELETE CASCADE,
  raw_price NUMERIC(20,10) NOT NULL,      -- сырая цена из биржи
  bid_price NUMERIC(20,10),               -- опционально: bid
  ask_price NUMERIC(20,10),               -- опционально: ask
  volume_24h NUMERIC(20,10),              -- опционально: объем за 24ч
  metadata JSONB DEFAULT '{}',            -- дополнительные данные
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_id, source_pair_id)
);

-- Индекс для быстрого поиска актуальных курсов
CREATE INDEX IF NOT EXISTS idx_fx_raw_rate_lookup ON fx_raw_rate(source_id, source_pair_id, received_at DESC);

-- Правила наценки
CREATE TABLE IF NOT EXISTS fx_markup_rule (
  id SERIAL PRIMARY KEY,
  level TEXT NOT NULL CHECK (level IN ('global','source','pair')),
  source_id INT REFERENCES fx_source(id) ON DELETE CASCADE,
  source_pair_id INT REFERENCES fx_source_pair(id) ON DELETE CASCADE,
  percent NUMERIC(9,4) NOT NULL DEFAULT 0,     -- может быть <0 (скидка)
  fixed NUMERIC(20,10) NOT NULL DEFAULT 0,     -- в валюте котировки
  rounding_mode TEXT NOT NULL DEFAULT 'ROUND_HALF_UP', -- ROUND_HALF_UP, DOWN, UP, BANKERS
  round_to INT NOT NULL DEFAULT 4,             -- знаков после запятой
  valid_from TIMESTAMPTZ,
  valid_to TIMESTAMPTZ,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  deleted_at TIMESTAMPTZ,                      -- мягкое удаление
  description TEXT,                            -- описание правила
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- Проверки консистентности
  CHECK (
    (level = 'global' AND source_id IS NULL AND source_pair_id IS NULL) OR
    (level = 'source' AND source_id IS NOT NULL AND source_pair_id IS NULL) OR
    (level = 'pair' AND source_id IS NOT NULL AND source_pair_id IS NOT NULL)
  )
);

-- Индексы для быстрого поиска правил
CREATE INDEX IF NOT EXISTS idx_fx_markup_rule_level ON fx_markup_rule(level, enabled) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_fx_markup_rule_source ON fx_markup_rule(source_id, enabled) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_fx_markup_rule_pair ON fx_markup_rule(source_pair_id, enabled) WHERE deleted_at IS NULL;

-- Итоговые курсы (кэш/снапшот с примененной наценкой)
CREATE TABLE IF NOT EXISTS fx_final_rate (
  id BIGSERIAL PRIMARY KEY,
  source_id INT NOT NULL REFERENCES fx_source(id) ON DELETE CASCADE,
  source_pair_id INT NOT NULL REFERENCES fx_source_pair(id) ON DELETE CASCADE,
  raw_price NUMERIC(20,10) NOT NULL,          -- исходная цена
  final_price NUMERIC(20,10) NOT NULL,        -- цена с наценкой
  applied_rule_id INT REFERENCES fx_markup_rule(id),
  markup_percent NUMERIC(9,4),                -- примененный процент
  markup_fixed NUMERIC(20,10),                -- примененная фикс. наценка
  calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  stale BOOLEAN NOT NULL DEFAULT FALSE,       -- данные устарели
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_id, source_pair_id)
);

-- Индекс для быстрого получения актуальных курсов
CREATE INDEX IF NOT EXISTS idx_fx_final_rate_lookup ON fx_final_rate(source_id, source_pair_id, stale);

-- Логи синхронизации
CREATE TABLE IF NOT EXISTS fx_sync_log (
  id BIGSERIAL PRIMARY KEY,
  source_id INT REFERENCES fx_source(id) ON DELETE SET NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  status TEXT NOT NULL CHECK (status IN ('running','success','error','partial')),
  pairs_processed INT DEFAULT 0,
  pairs_succeeded INT DEFAULT 0,
  pairs_failed INT DEFAULT 0,
  duration_ms INT,                            -- длительность в миллисекундах
  error_message TEXT,
  metadata JSONB DEFAULT '{}',                -- дополнительная информация
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Индекс для просмотра последних логов
CREATE INDEX IF NOT EXISTS idx_fx_sync_log_recent ON fx_sync_log(created_at DESC, source_id);

-- История снимков курсов (опционально, для аналитики)
CREATE TABLE IF NOT EXISTS fx_rate_snapshot (
  id BIGSERIAL PRIMARY KEY,
  source_id INT NOT NULL REFERENCES fx_source(id) ON DELETE CASCADE,
  source_pair_id INT NOT NULL REFERENCES fx_source_pair(id) ON DELETE CASCADE,
  raw_price NUMERIC(20,10) NOT NULL,
  final_price NUMERIC(20,10) NOT NULL,
  applied_rule_id INT REFERENCES fx_markup_rule(id),
  snapshot_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Партиционирование по времени для снимков (опционально)
CREATE INDEX IF NOT EXISTS idx_fx_rate_snapshot_time ON fx_rate_snapshot(snapshot_at DESC, source_pair_id);

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггеры для обновления updated_at
DROP TRIGGER IF EXISTS update_fx_source_updated_at ON fx_source;
CREATE TRIGGER update_fx_source_updated_at BEFORE UPDATE ON fx_source
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_fx_source_pair_updated_at ON fx_source_pair;
CREATE TRIGGER update_fx_source_pair_updated_at BEFORE UPDATE ON fx_source_pair
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_fx_markup_rule_updated_at ON fx_markup_rule;
CREATE TRIGGER update_fx_markup_rule_updated_at BEFORE UPDATE ON fx_markup_rule
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Вставка начальных данных
-- Источник: Grinex
INSERT INTO fx_source (code, name, enabled, auth_type, api_base_url, config) VALUES 
  ('grinex', 'Grinex Exchange', true, 'public', 'https://api.grinex.io', '{"timeout": 5000, "retries": 3}'),
  ('rapira', 'Rapira Exchange', true, 'public', 'https://api.rapira.net', '{"timeout": 5000, "retries": 3}')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  api_base_url = EXCLUDED.api_base_url,
  config = EXCLUDED.config;

-- Популярные пары для Grinex (примеры)
INSERT INTO fx_source_pair (source_id, source_symbol, base_currency, quote_currency, internal_symbol, enabled) 
SELECT 
  s.id,
  'USDTRUB',
  'USDT',
  'RUB',
  'USDT/RUB',
  true
FROM fx_source s WHERE s.code = 'grinex'
ON CONFLICT (source_id, source_symbol) DO NOTHING;

INSERT INTO fx_source_pair (source_id, source_symbol, base_currency, quote_currency, internal_symbol, enabled) 
SELECT 
  s.id,
  'BTCUSDT',
  'BTC',
  'USDT',
  'BTC/USDT',
  true
FROM fx_source s WHERE s.code = 'grinex'
ON CONFLICT (source_id, source_symbol) DO NOTHING;

-- Популярные пары для Rapira (примеры)
INSERT INTO fx_source_pair (source_id, source_symbol, base_currency, quote_currency, internal_symbol, enabled) 
SELECT 
  s.id,
  'usdtrub',
  'USDT',
  'RUB',
  'USDT/RUB',
  true
FROM fx_source s WHERE s.code = 'rapira'
ON CONFLICT (source_id, source_symbol) DO NOTHING;

INSERT INTO fx_source_pair (source_id, source_symbol, base_currency, quote_currency, internal_symbol, enabled) 
SELECT 
  s.id,
  'btcusdt',
  'BTC',
  'USDT',
  'BTC/USDT',
  true
FROM fx_source s WHERE s.code = 'rapira'
ON CONFLICT (source_id, source_symbol) DO NOTHING;

-- Глобальное правило наценки по умолчанию (0% и 0 fixed - без наценки)
INSERT INTO fx_markup_rule (level, percent, fixed, enabled, description) VALUES 
  ('global', 0.0, 0.0, true, 'Default global rule - no markup')
ON CONFLICT DO NOTHING;

-- Комментарии к таблицам
COMMENT ON TABLE fx_source IS 'Источники курсов (биржи)';
COMMENT ON TABLE fx_source_pair IS 'Торговые пары источников с маппингом на внутренние коды';
COMMENT ON TABLE fx_raw_rate IS 'Сырые курсы из источников';
COMMENT ON TABLE fx_markup_rule IS 'Правила наценки (глобальные, по источнику, по паре)';
COMMENT ON TABLE fx_final_rate IS 'Итоговые курсы с примененной наценкой';
COMMENT ON TABLE fx_sync_log IS 'Логи синхронизации курсов';
COMMENT ON TABLE fx_rate_snapshot IS 'История снимков курсов для аналитики';

