# Grinex Admin Guide - Управление в боте

## 🎯 Быстрый доступ

### Через админ-панель
1. Отправьте `/admin` в бот
2. Нажмите "🌐 Интеграции"
3. Выберите "🟢 Grinex Exchange"

### Прямые команды
- `/grinex_status` - Статус интеграции
- `/grinex_ticker` - Получить конкретный тикер
- `/grinex_help` - Справка

## 📊 Команда `/grinex_status`

Показывает:
- ✅ Статус Grinex API (активен/недоступен)
- ⏱ Задержка (latency) в миллисекундах
- 🔢 HTTP код последнего ответа
- 🕒 Время последнего обновления
- ❌ Количество ошибок
- 📅 Последняя синхронизация FX
- ⚙️ Интервал обновления курсов

### Доступные кнопки:

#### 🔄 Синхронизировать
- Принудительно запускает синхронизацию курсов из Grinex
- Показывает результат:
  - Обработано пар
  - Успешно синхронизировано
  - Количество ошибок
  - Длительность операции

#### 📊 Курсы
- Показывает текущие курсы из Grinex с наценками
- Для каждой пары отображается:
  - 🟢/🟡 Статус (актуальные/устаревшие)
  - Raw price (сырая цена)
  - Final price (финальная цена с наценкой)
  - Процент и фиксированная наценка
  - Время последнего обновления

#### 📈 Тикеры
- Показывает raw тикеры прямо из API Grinex
- Отображает:
  - Текущая цена (last_price)
  - Bid/Ask спред
  - Объем за 24 часа
  - Изменение цены за 24 часа
  - 🟢/🔴 Направление изменения

#### 🧪 Тест API
- Запускает комплексное тестирование:
  1. ✅ get_ticker('USDTRUB') - получение одного тикера
  2. ✅ get_all_tickers() - получение всех тикеров
  3. ✅ Health check - проверка состояния
  4. ✅ FX sync - тест синхронизации через FX сервис
- Показывает latency и timestamp

#### ⚙️ Настройки
- Показывает конфигурацию Grinex:
  - Base URL API
  - Timeout запросов
  - Max retries
  - FX планировщик настройки
- Дополнительные кнопки:
  - 📊 Статистика пар
  - 🔄 Планировщик

## 📈 Команда `/grinex_ticker`

Получает детальную информацию по конкретному тикеру:

**Пример использования:**
1. Отправьте `/grinex_ticker`
2. Введите символ пары: `USDTRUB` или `BTCUSDT`

**Отображаемая информация:**
- 💰 Price (текущая цена)
- 📊 Bid/Ask + спред
- 📈 Volume 24h
- 📉 High/Low 24h
- 🔄 Change 24h (с индикатором 🟢/🔴)
- 🕐 Timestamp

## 🔧 Настройка источника

### Через Web Admin
```
http://localhost:8000/admin/fx/sources
```
- Управление парами
- Просмотр raw данных
- Принудительная синхронизация

### Добавление новой пары (SQL)
```sql
INSERT INTO fx_source_pair (source_id, source_symbol, base_currency, quote_currency, internal_symbol, enabled)
SELECT id, 'ETHRUB', 'ETH', 'RUB', 'ETH/RUB', true
FROM fx_source WHERE code = 'grinex';
```

### Настройка наценки для Grinex

**Глобально для всего Grinex (+1.5%):**
```sql
INSERT INTO fx_markup_rule (level, source_id, percent, fixed, enabled, description)
SELECT 'source', id, 1.5, 0, true, 'Grinex: 1.5% markup'
FROM fx_source WHERE code = 'grinex';
```

**Для конкретной пары (+2% + 10 RUB):**
```sql
INSERT INTO fx_markup_rule (level, source_id, source_pair_id, percent, fixed, enabled, description)
SELECT 'pair', sp.source_id, sp.id, 2.0, 10.0, true, 'USDT/RUB special markup'
FROM fx_source_pair sp
JOIN fx_source s ON s.id = sp.source_id
WHERE s.code = 'grinex' AND sp.internal_symbol = 'USDT/RUB';
```

## 📊 Мониторинг

### Проверка здоровья
```bash
# Через API
curl http://localhost:8000/api/fx/scheduler/status

# Через бот
/grinex_status → 🧪 Тест API
```

### Логи
```bash
# Docker логи
docker-compose logs bot | grep -i grinex

# Логи синхронизации
docker-compose logs bot | grep "FX sync.*grinex"

# Ошибки
docker-compose logs bot | grep -i "grinex.*error"
```

### Метрики
В `/grinex_status` отображаются:
- Latency (задержка API)
- Error count (количество ошибок)
- Last update (время последнего обновления)
- HTTP code (код последнего ответа)

## 🔍 Troubleshooting

### Курсы не обновляются
1. Проверить `/grinex_status` - смотрим статус API
2. Нажать "🧪 Тест API" - проверяем доступность
3. Нажать "🔄 Синхронизировать" - принудительно обновить
4. Проверить логи: `docker-compose logs bot | grep grinex`

### API недоступен (🔴)
1. Проверить GRINEX_API_BASE в .env
2. Проверить сетевую доступность
3. Увеличить GRINEX_TIMEOUT
4. Проверить логи на детали ошибок

### Устаревшие данные (🟡 stale)
- Данные старше FX_STALE_THRESHOLD_SECONDS
- Проверить работу планировщика: `/grinex_status` → ⚙️ Настройки → 🔄 Планировщик
- Принудительно синхронизировать

### Неправильная наценка
1. Проверить Web Admin: http://localhost:8000/admin/fx/markup-rules
2. Убедиться что правило enabled = true
3. Проверить приоритет: Pair > Source > Global
4. Формула: `price1 = raw * (1 + percent/100); final = price1 + fixed`

## 🌐 Web Admin vs Bot

| Функция | Bot | Web Admin |
|---------|-----|-----------|
| Статус API | ✅ `/grinex_status` | ✅ /admin/fx/sources |
| Синхронизация | ✅ Кнопка "🔄" | ✅ Кнопка "Sync Now" |
| Просмотр курсов | ✅ Кнопка "📊" | ✅ /admin/fx/rates |
| Просмотр тикеров | ✅ Кнопка "📈" | ❌ |
| Тест API | ✅ Кнопка "🧪" | ❌ |
| Настройка пар | ❌ | ✅ /admin/fx/sources/{id}/pairs |
| Правила наценки | ❌ | ✅ /admin/fx/markup-rules |
| Логи синхронизации | ❌ | ✅ /admin/fx/logs |

## 📚 Связанные команды

- `/rapira_status` - Аналогичная панель для Rapira
- `/admin` → "🌐 Интеграции" → "📊 FX Rates System" - Общий статус FX
- Web Admin: http://localhost:8000/admin/fx/sources

## 🔐 Доступ

Все команды доступны только администраторам (ADMIN_IDS в .env).

---

**Документация:**
- Полное руководство: `FX_RATES_README.md`
- Детали реализации: `FX_IMPLEMENTATION_SUMMARY.md`
- Быстрый старт: `QUICK_START_FX.md`

