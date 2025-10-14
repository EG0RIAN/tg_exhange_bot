-- Миграция: Наценки на уровне город+пара
-- Дата: 2025-10-14

CREATE TABLE IF NOT EXISTS city_pair_markups (
    id SERIAL PRIMARY KEY,
    city_id INTEGER NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
    pair_symbol VARCHAR(50) NOT NULL,  -- USDT/RUB, BTC/USDT
    markup_percent DECIMAL(10, 4) NOT NULL DEFAULT 0,
    markup_fixed DECIMAL(20, 8) NOT NULL DEFAULT 0,
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(city_id, pair_symbol)
);

-- Триггер для updated_at
CREATE TRIGGER update_city_pair_markups_updated_at 
    BEFORE UPDATE ON city_pair_markups 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Индекс для быстрого поиска
CREATE INDEX idx_city_pair_markups_lookup ON city_pair_markups(city_id, pair_symbol) WHERE enabled = true;

-- Комментарии
COMMENT ON TABLE city_pair_markups IS 'Наценки на уровне город + торговая пара (переопределяют базовую наценку города)';
COMMENT ON COLUMN city_pair_markups.pair_symbol IS 'Символ торговой пары (USDT/RUB, BTC/USDT)';
COMMENT ON COLUMN city_pair_markups.markup_percent IS 'Процентная наценка для этой пары в этом городе';

-- Мигрируем существующие наценки городов как базовые для всех пар
-- (можно потом переопределить для конкретных пар)

