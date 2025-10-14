-- Миграция: Раздельные наценки на покупку и продажу
-- Дата: 2025-10-14

-- Добавляем новые колонки в cities
ALTER TABLE cities ADD COLUMN IF NOT EXISTS markup_buy DECIMAL(10, 4) DEFAULT 0;
ALTER TABLE cities ADD COLUMN IF NOT EXISTS markup_sell DECIMAL(10, 4) DEFAULT 0;
ALTER TABLE cities ADD COLUMN IF NOT EXISTS preferred_source VARCHAR(20);  -- 'rapira', 'grinex', null=любой

-- Копируем старые значения markup_percent в обе колонки
UPDATE cities SET markup_buy = markup_percent, markup_sell = markup_percent WHERE markup_buy = 0 AND markup_sell = 0;

-- Удаляем старую колонку (опционально, оставим для совместимости)
-- ALTER TABLE cities DROP COLUMN markup_percent;

-- Аналогично для city_pair_markups
ALTER TABLE city_pair_markups ADD COLUMN IF NOT EXISTS markup_buy DECIMAL(10, 4) DEFAULT 0;
ALTER TABLE city_pair_markups ADD COLUMN IF NOT EXISTS markup_sell DECIMAL(10, 4) DEFAULT 0;

UPDATE city_pair_markups SET markup_buy = markup_percent, markup_sell = markup_percent WHERE markup_buy = 0 AND markup_sell = 0;

-- Комментарии
COMMENT ON COLUMN cities.markup_buy IS 'Наценка при покупке криптовалюты клиентом (может быть отрицательной)';
COMMENT ON COLUMN cities.markup_sell IS 'Наценка при продаже криптовалюты клиентом (может быть отрицательной)';
COMMENT ON COLUMN cities.preferred_source IS 'Предпочтительный источник курсов для города (rapira/grinex)';

-- Вставляем города из списка
INSERT INTO cities (code, name, markup_buy, markup_sell, preferred_source, sort_order) VALUES
    ('astrakhan', 'Астрахань', -1.9, 2.4, 'rapira', 10),
    ('barnaul', 'Барнаул', -1.5, 1.5, 'grinex', 11),
    ('blagoveshchensk', 'Благовещенск', -1.3, 1.3, 'rapira', 12),
    ('vladivostok', 'Владивосток', -1.3, 1.3, 'rapira', 13),
    ('volgograd', 'Волгоград', -1.2, 1.6, 'rapira', 14),
    ('voronezh', 'Воронеж', -1.0, 1.0, 'rapira', 15),
    ('izhevsk', 'Ижевск', -1.0, 1.2, 'rapira', 16),
    ('irkutsk', 'Иркутск', -1.0, 1.2, 'grinex', 17),
    ('kaliningrad', 'Калининград', -1.0, 1.1, 'rapira', 18),
    ('kemerovo', 'Кемерово', -1.3, 1.6, 'grinex', 19),
    ('krasnodar', 'Краснодар', -0.7, 1.0, 'rapira', 20),
    ('krasnoyarsk', 'Красноярск', 1.2, -1.2, 'rapira', 21),
    ('novosibirsk', 'Новосибирск', -1.2, 1.2, 'grinex', 22),
    ('omsk', 'Омск', -1.4, 1.4, 'grinex', 23),
    ('orenburg', 'Оренбург', -1.2, 1.4, 'rapira', 24),
    ('perm', 'Пермь', -1.4, 1.4, 'grinex', 25),
    ('pyatigorsk', 'Пятигорск', -1.0, 1.0, 'rapira', 26),
    ('samara', 'Самара', -1.1, 1.1, 'grinex', 27),
    ('saratov', 'Саратов', -1.2, 1.2, 'grinex', 28),
    ('sochi', 'Сочи', -0.8, 1.0, 'rapira', 29),
    ('simferopol', 'Симферополь', -1.5, 1.5, 'rapira', 30),
    ('stavropol', 'Ставрополь', -1.2, 1.2, 'rapira', 31),
    ('tomsk', 'Томск', 1.4, 1.4, 'grinex', 32),
    ('tyumen', 'Тюмень', -1.2, 1.2, 'grinex', 33),
    ('ufa', 'Уфа', -1.2, 1.2, 'rapira', 34),
    ('khabarovsk', 'Хабаровск', -1.2, 1.5, 'grinex', 35),
    ('cheboksary', 'Чебоксары', -1.4, 1.5, 'rapira', 36),
    ('chelyabinsk', 'Челябинск', -1.2, 1.2, 'rapira', 37)
ON CONFLICT (code) DO UPDATE SET
    markup_buy = EXCLUDED.markup_buy,
    markup_sell = EXCLUDED.markup_sell,
    preferred_source = EXCLUDED.preferred_source,
    sort_order = EXCLUDED.sort_order;

-- Обновляем существующие города
UPDATE cities SET markup_buy = -0.35, markup_sell = 0.35, sort_order = 1 WHERE code = 'moscow';
UPDATE cities SET markup_buy = -0.65, markup_sell = 0.7, sort_order = 2 WHERE code = 'spb';
UPDATE cities SET markup_buy = -1.2, markup_sell = 1.2, sort_order = 5, preferred_source = 'grinex' WHERE code = 'ekaterinburg';
UPDATE cities SET markup_buy = -0.75, markup_sell = 1.2, sort_order = 4, preferred_source = 'rapira' WHERE code = 'nizhniy_novgorod';
UPDATE cities SET markup_buy = -1.2, markup_sell = 1.2, sort_order = 6, preferred_source = 'rapira' WHERE code = 'kazan';
UPDATE cities SET markup_buy = -0.9, markup_sell = 0.9, sort_order = 3, preferred_source = 'rapira' WHERE code = 'rostov';

