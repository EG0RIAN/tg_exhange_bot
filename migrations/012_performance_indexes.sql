-- Миграция для добавления индексов производительности
-- Оптимизирует часто используемые запросы

-- Индексы для таблицы cities
CREATE INDEX IF NOT EXISTS idx_cities_code ON cities(code) WHERE enabled = true;
CREATE INDEX IF NOT EXISTS idx_cities_enabled ON cities(enabled);

-- Индексы для таблицы orders
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_city ON orders(city);
CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status);

-- Индексы для таблицы users
CREATE INDEX IF NOT EXISTS idx_users_tg_id ON users(tg_id);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON orders(created_at DESC);

-- Индексы для таблицы fx_final_rate
CREATE INDEX IF NOT EXISTS idx_fx_final_rate_source_pair ON fx_final_rate(source_id, source_pair_id);
CREATE INDEX IF NOT EXISTS idx_fx_final_rate_stale ON fx_final_rate(stale);
CREATE INDEX IF NOT EXISTS idx_fx_final_rate_calculated_at ON fx_final_rate(calculated_at DESC);

-- Индексы для таблицы fx_source
CREATE INDEX IF NOT EXISTS idx_fx_source_code ON fx_source(code) WHERE enabled = true;
CREATE INDEX IF NOT EXISTS idx_fx_source_enabled ON fx_source(enabled);

-- Индексы для таблицы fx_source_pair
CREATE INDEX IF NOT EXISTS idx_fx_source_pair_source_id ON fx_source_pair(source_id) WHERE enabled = true;
CREATE INDEX IF NOT EXISTS idx_fx_source_pair_symbol ON fx_source_pair(internal_symbol);

-- Индексы для таблицы city_pair_markups
CREATE INDEX IF NOT EXISTS idx_city_pair_markups_city_id ON city_pair_markups(city_id) WHERE enabled = true;
CREATE INDEX IF NOT EXISTS idx_city_pair_markups_symbol ON city_pair_markups(pair_symbol);

-- Индексы для таблицы fx_markup_rule
CREATE INDEX IF NOT EXISTS idx_fx_markup_rule_enabled ON fx_markup_rule(enabled) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_fx_markup_rule_level ON fx_markup_rule(level);

-- Индексы для таблицы trading_pairs
CREATE INDEX IF NOT EXISTS idx_trading_pairs_enabled ON trading_pairs(enabled);

-- Индексы для таблицы rates
CREATE INDEX IF NOT EXISTS idx_rates_pair ON rates(pair);
CREATE INDEX IF NOT EXISTS idx_rates_updated_at ON rates(updated_at DESC);

-- Комментарии для документации
COMMENT ON INDEX idx_cities_code IS 'Ускоряет поиск городов по коду';
COMMENT ON INDEX idx_orders_user_status IS 'Композитный индекс для фильтрации заказов по пользователю и статусу';
COMMENT ON INDEX idx_fx_final_rate_source_pair IS 'Композитный индекс для быстрого поиска финальных курсов';

