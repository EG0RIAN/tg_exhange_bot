-- Миграция 005: Настройка наценок по городам для Rapira

-- Добавляем правила наценки для городов
-- Москва - базовый курс (0%)
INSERT INTO fx_markup_rule (level, percent, fixed, enabled, description, rounding_mode, round_to)
VALUES ('global', 0.0, 0, true, 'Наценка для города: moscow (Москва - базовый)', 'ROUND_HALF_UP', 2)
ON CONFLICT DO NOTHING;

-- Санкт-Петербург - +0.3%
INSERT INTO fx_markup_rule (level, percent, fixed, enabled, description, rounding_mode, round_to)
VALUES ('global', 0.3, 0, true, 'Наценка для города: spb (Санкт-Петербург)', 'ROUND_HALF_UP', 2)
ON CONFLICT DO NOTHING;

-- Ростов-на-Дону - +1%
INSERT INTO fx_markup_rule (level, percent, fixed, enabled, description, rounding_mode, round_to)
VALUES ('global', 1.0, 0, true, 'Наценка для города: rostov (Ростов-на-Дону)', 'ROUND_HALF_UP', 2)
ON CONFLICT DO NOTHING;

-- Нижний Новгород - +0.8%
INSERT INTO fx_markup_rule (level, percent, fixed, enabled, description, rounding_mode, round_to)
VALUES ('global', 0.8, 0, true, 'Наценка для города: nizhniy_novgorod (Нижний Новгород)', 'ROUND_HALF_UP', 2)
ON CONFLICT DO NOTHING;

-- Екатеринбург - +0.7%
INSERT INTO fx_markup_rule (level, percent, fixed, enabled, description, rounding_mode, round_to)
VALUES ('global', 0.7, 0, true, 'Наценка для города: ekaterinburg (Екатеринбург)', 'ROUND_HALF_UP', 2)
ON CONFLICT DO NOTHING;

-- Казань - +0.9%
INSERT INTO fx_markup_rule (level, percent, fixed, enabled, description, rounding_mode, round_to)
VALUES ('global', 0.9, 0, true, 'Наценка для города: kazan (Казань)', 'ROUND_HALF_UP', 2)
ON CONFLICT DO NOTHING;

-- Другие города - +1.5%
INSERT INTO fx_markup_rule (level, percent, fixed, enabled, description, rounding_mode, round_to)
VALUES ('global', 1.5, 0, true, 'Наценка для города: other (Другие города)', 'ROUND_HALF_UP', 2)
ON CONFLICT DO NOTHING;

-- Комментарий
COMMENT ON COLUMN fx_markup_rule.description IS 'Описание правила. Для городов формат: "Наценка для города: city_code (Название)"';

