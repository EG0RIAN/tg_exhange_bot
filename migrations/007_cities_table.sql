-- Миграция: Таблица городов для управления наценками
-- Дата: 2025-10-14

CREATE TABLE IF NOT EXISTS cities (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    markup_percent DECIMAL(10, 4) NOT NULL DEFAULT 0,
    markup_fixed DECIMAL(20, 8) NOT NULL DEFAULT 0,
    enabled BOOLEAN NOT NULL DEFAULT true,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Триггер для обновления updated_at
CREATE TRIGGER update_cities_updated_at 
    BEFORE UPDATE ON cities 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Вставляем существующие города
INSERT INTO cities (code, name, markup_percent, sort_order) VALUES
    ('moscow', 'Москва', 0.0, 1),
    ('spb', 'Санкт-Петербург', 0.3, 2),
    ('rostov', 'Ростов-на-Дону', 1.0, 3),
    ('nizhniy_novgorod', 'Нижний Новгород', 0.8, 4),
    ('ekaterinburg', 'Екатеринбург', 0.7, 5),
    ('kazan', 'Казань', 0.9, 6),
    ('other', 'Другие города', 1.5, 999)
ON CONFLICT (code) DO NOTHING;

-- Комментарии
COMMENT ON TABLE cities IS 'Города с настраиваемыми наценками на курсы валют';
COMMENT ON COLUMN cities.code IS 'Уникальный код города (для программного использования)';
COMMENT ON COLUMN cities.name IS 'Название города для отображения';
COMMENT ON COLUMN cities.markup_percent IS 'Процентная наценка для города';
COMMENT ON COLUMN cities.markup_fixed IS 'Фиксированная наценка для города';
COMMENT ON COLUMN cities.enabled IS 'Активен ли город';
COMMENT ON COLUMN cities.sort_order IS 'Порядок сортировки (меньше = выше)';

