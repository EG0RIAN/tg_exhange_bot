-- Миграция 006: Синхронизация trading_pairs с fx_source_pair
-- Унификация системы торговых пар

-- Добавляем отсутствующие пары из trading_pairs в fx_source_pair
-- Для каждого источника (Rapira и Grinex)

-- Получаем unique пары из trading_pairs и добавляем их в fx_source_pair
DO $$
DECLARE
    rapira_id INT;
    grinex_id INT;
    pair_record RECORD;
BEGIN
    -- Получаем ID источников
    SELECT id INTO rapira_id FROM fx_source WHERE code = 'rapira';
    SELECT id INTO grinex_id FROM fx_source WHERE code = 'grinex';
    
    -- Для каждой пары из trading_pairs
    FOR pair_record IN 
        SELECT DISTINCT base_currency, quote_currency 
        FROM trading_pairs 
        WHERE is_active = true
    LOOP
        -- Добавляем для Rapira (lowercase)
        INSERT INTO fx_source_pair 
        (source_id, source_symbol, base_currency, quote_currency, internal_symbol, enabled)
        VALUES (
            rapira_id,
            LOWER(pair_record.base_currency || pair_record.quote_currency),
            pair_record.base_currency,
            pair_record.quote_currency,
            pair_record.base_currency || '/' || pair_record.quote_currency,
            true
        )
        ON CONFLICT (source_id, source_symbol) DO NOTHING;
        
        -- Добавляем для Grinex (UPPERCASE)
        INSERT INTO fx_source_pair 
        (source_id, source_symbol, base_currency, quote_currency, internal_symbol, enabled)
        VALUES (
            grinex_id,
            UPPER(pair_record.base_currency || pair_record.quote_currency),
            pair_record.base_currency,
            pair_record.quote_currency,
            pair_record.base_currency || '/' || pair_record.quote_currency,
            true
        )
        ON CONFLICT (source_id, source_symbol) DO NOTHING;
    END LOOP;
END $$;

-- Комментарий
COMMENT ON TABLE fx_source_pair IS 'Торговые пары источников (единая таблица для всех пар)';
COMMENT ON TABLE trading_pairs IS 'Legacy таблица торговых пар (deprecated, использовать fx_source_pair)';

