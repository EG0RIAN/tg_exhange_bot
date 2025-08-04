-- FAQ схема

-- Категории FAQ
CREATE TABLE IF NOT EXISTS faq_categories (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  sort_order INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Вопросы FAQ
CREATE TABLE IF NOT EXISTS faq_questions (
  id BIGSERIAL PRIMARY KEY,
  category_id BIGINT REFERENCES faq_categories(id) ON DELETE CASCADE,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  sort_order INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Добавляем данные по умолчанию
INSERT INTO faq_categories (name, sort_order) VALUES
  ('Общие вопросы', 1),
  ('Оплата и курсы', 2),
  ('Безопасность', 3)
ON CONFLICT DO NOTHING;

-- Добавляем вопросы по умолчанию
INSERT INTO faq_questions (category_id, question, answer, sort_order)
SELECT c.id, 'Как работает обмен валют?', 'Мы предлагаем быстрый и безопасный обмен валют через наш Telegram бот. Просто выберите валютную пару, укажите сумму и способ выплаты.', 1
FROM faq_categories c WHERE c.name = 'Общие вопросы'
UNION ALL
SELECT c.id, 'Какие валюты поддерживаются?', 'Мы поддерживаем основные валюты: USD, EUR, RUB, а также криптовалюты. Полный список доступен в разделе "Курсы".', 2
FROM faq_categories c WHERE c.name = 'Общие вопросы'
UNION ALL
SELECT c.id, 'Как узнать актуальный курс?', 'Актуальные курсы отображаются в разделе "Курсы" в боте. Курсы обновляются автоматически каждую минуту.', 1
FROM faq_categories c WHERE c.name = 'Оплата и курсы'
UNION ALL
SELECT c.id, 'Какие способы выплаты доступны?', 'Доступны выплаты на карты РФ и EU, криптовалюты (Bitcoin, USDT), а также наличные в Москве и LA.', 2
FROM faq_categories c WHERE c.name = 'Оплата и курсы'
UNION ALL
SELECT c.id, 'Безопасны ли мои данные?', 'Да, мы используем современные методы шифрования и не храним конфиденциальные данные пользователей.', 1
FROM faq_categories c WHERE c.name = 'Безопасность'
ON CONFLICT DO NOTHING; 