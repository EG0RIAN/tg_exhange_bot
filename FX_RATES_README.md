# FX Rates Module - Валютные курсы с наценками

## Описание

Модуль синхронизации валютных курсов с интеграцией бирж Grinex и Rapira, поддержкой наценок и управлением через админ-панель.

## Возможности

- ✅ **Интеграция с биржами**: Grinex (публичный API), Rapira (публичный API)
- ✅ **Гибкая система наценок**: процентные и фиксированные наценки на трёх уровнях (глобально, по бирже, по паре)
- ✅ **Автоматическая синхронизация**: настраиваемый планировщик обновления курсов
- ✅ **Приоритет правил**: pair > source > global
- ✅ **Различные режимы округления**: ROUND_HALF_UP, ROUND_DOWN, ROUND_UP, BANKERS
- ✅ **Stale detection**: автоматическое определение устаревших данных
- ✅ **Подробное логирование**: история всех синхронизаций с метриками
- ✅ **Web Admin UI**: удобный интерфейс управления
- ✅ **REST API**: программный доступ к курсам

## Архитектура

### База данных

```
fx_source           - Источники (биржи)
fx_source_pair      - Пары источника с маппингом
fx_raw_rate         - Сырые курсы из биржи
fx_markup_rule      - Правила наценки (3 уровня)
fx_final_rate       - Финальные курсы с наценкой
fx_sync_log         - Логи синхронизации
fx_rate_snapshot    - История снимков (опционально)
```

### Компоненты

- **Клиенты**: `grinex.py`, `rapira.py` - HTTP-клиенты для бирж
- **Сервис**: `fx_rates.py` - основная логика (синхронизация, наценки, вычисления)
- **Планировщик**: `fx_scheduler.py` - автоматическое обновление курсов
- **API**: `web_admin/main.py` - REST эндпоинты и админка

## Конфигурация

### Переменные окружения

```bash
# FX Module Settings
FX_UPDATE_INTERVAL_SECONDS=60          # Интервал обновления курсов
FX_STALE_CHECK_INTERVAL=300            # Интервал проверки stale данных  
FX_STALE_THRESHOLD_SECONDS=180         # Порог устаревания данных

# Grinex API
GRINEX_API_BASE=https://api.grinex.io
GRINEX_TIMEOUT=5                        # Таймаут запросов (сек)
GRINEX_MAX_RETRIES=3                    # Количество ретраев

# Rapira API (уже существующие настройки)
RAPIRA_API_BASE=https://api.rapira.net
RAPIRA_TIMEOUT=10
RAPIRA_MAX_RETRIES=3
RAPIRA_CACHE_TTL=5
```

### Применение миграций

```bash
# Применить миграцию БД
docker-compose exec postgres psql -U exchange -d exchange -f /app/migrations/004_fx_rates_system.sql

# Или через Python
python init_db.py
```

## Формула наценки

```python
price1 = raw_price * (1 + percent/100)
final_price = price1 + fixed
```

**Порядок важен**: сначала применяется процент, затем фиксированная сумма.

**Пример**:
- raw_price = 100
- percent = 2.5 (2.5%)
- fixed = 5

```
price1 = 100 * 1.025 = 102.5
final_price = 102.5 + 5 = 107.5
```

## Приоритет правил

1. **Pair** (пара) - самый высокий приоритет
2. **Source** (биржа) - средний приоритет  
3. **Global** (глобально) - самый низкий приоритет

Применяется первое подходящее правило в порядке приоритета.

## Использование

### Web Admin

1. **Источники**: `/admin/fx/sources`
   - Просмотр всех источников (Grinex, Rapira)
   - Статус, количество пар, последняя синхронизация
   - Кнопка "Sync Now" для принудительного обновления

2. **Пары источника**: `/admin/fx/sources/{id}/pairs`
   - Список всех пар конкретного источника
   - Сырые и финальные курсы
   - Статус (OK, STALE, NO DATA)

3. **Правила наценки**: `/admin/fx/markup-rules`
   - CRUD правил наценки
   - Настройка уровня, процента, фикса, округления
   - Приоритет автоматический

4. **Текущие курсы**: `/admin/fx/rates`
   - Все актуальные курсы
   - Сырая и финальная цена
   - Примененная наценка
   - Индикатор stale

5. **Логи**: `/admin/fx/logs`
   - История всех синхронизаций
   - Статус, длительность, ошибки

### REST API

#### Получить курс для пары

```bash
GET /api/fx/rates?base=USDT&quote=RUB&source=grinex

Response:
{
  "base": "USDT",
  "quote": "RUB",
  "source": "grinex",
  "final_price": "98.3200",
  "raw_price": "96.9100",
  "applied_rule_id": 42,
  "markup": {
    "percent": "1.2",
    "fixed": "0.2"
  },
  "calculated_at": "2025-10-13T13:00:15Z",
  "stale": false,
  "bid": "96.9000",
  "ask": "96.9200"
}
```

#### Получить все курсы

```bash
GET /api/fx/rates

Response:
{
  "rates": [
    {
      "base": "USDT",
      "quote": "RUB",
      "source": "grinex",
      "internal_symbol": "USDT/RUB",
      "final_price": "98.3200",
      "raw_price": "96.9100",
      "calculated_at": "2025-10-13T13:00:15Z",
      "stale": false
    },
    ...
  ]
}
```

#### Принудительная синхронизация

```bash
POST /api/fx/sync
POST /api/fx/sync?source=grinex

Response:
{
  "success": true,
  "message": "Sync triggered for grinex",
  "result": {
    "pairs_processed": 10,
    "pairs_succeeded": 10,
    "pairs_failed": 0,
    "duration_ms": 523,
    "status": "success"
  }
}
```

#### Статус планировщика

```bash
GET /api/fx/scheduler/status

Response:
{
  "running": true,
  "jobs": [
    {
      "id": "fx_sync_all",
      "name": "Sync all FX sources",
      "next_run": "2025-10-13T13:01:00Z"
    }
  ],
  "last_sync": {
    "grinex": "2025-10-13T13:00:15Z",
    "rapira": "2025-10-13T13:00:16Z"
  },
  "config": {
    "update_interval_seconds": 60,
    "stale_check_interval": 300,
    "stale_threshold_seconds": 180
  }
}
```

### Python API

```python
from src.services.fx_rates import get_fx_service

# Получить сервис
fx_service = await get_fx_service()

# Синхронизировать источник
result = await fx_service.sync_source_rates('grinex')

# Получить финальный курс
rate = await fx_service.get_final_rate(
    base='USDT',
    quote='RUB',
    source_code='grinex',
    allow_stale=False
)

print(f"Final price: {rate.final_price}")
print(f"Markup: {rate.markup_percent}% + {rate.markup_fixed}")

# Получить все курсы
rates = await fx_service.get_all_final_rates(source_code='grinex')
```

## Добавление нового источника

### 1. Создать клиент

```python
# src/services/new_exchange.py
class NewExchangeClient:
    async def get_ticker(self, symbol: str):
        # Реализация получения тикера
        pass
    
    async def get_all_tickers(self):
        # Реализация получения всех тикеров
        pass
```

### 2. Интегрировать в FX сервис

```python
# В fx_rates.py, метод sync_source_rates
elif source_code == 'new_exchange':
    rates_data = await self._fetch_new_exchange_rates(pairs)
```

### 3. Добавить в БД

```sql
INSERT INTO fx_source (code, name, enabled, auth_type, api_base_url)
VALUES ('new_exchange', 'New Exchange', true, 'public', 'https://api.new.exchange');

-- Добавить пары
INSERT INTO fx_source_pair (source_id, source_symbol, base_currency, quote_currency, internal_symbol)
SELECT id, 'USDTRUB', 'USDT', 'RUB', 'USDT/RUB'
FROM fx_source WHERE code = 'new_exchange';
```

## Мониторинг

### Проверка здоровья

```python
from src.services.grinex import get_grinex_client
from src.services.rapira import get_rapira_provider

# Проверка Grinex
client = await get_grinex_client()
health = client.get_health()
print(f"Grinex: latency={health.latency_ms}ms, available={health.is_available}")

# Проверка Rapira
provider = await get_rapira_provider()
health = provider.get_health()
print(f"Rapira: latency={health.latency}ms, errors={health.error_count}")
```

### Метрики

- Latency каждого источника (в миллисекундах)
- Количество ошибок
- Количество stale курсов
- Длительность синхронизации
- Процент успешных обновлений

## Troubleshooting

### Курсы не обновляются

1. Проверить статус планировщика: `GET /api/fx/scheduler/status`
2. Проверить логи: `/admin/fx/logs`
3. Триггерить синхронизацию вручную: `POST /api/fx/sync`

### Stale данные

- Данные помечаются как stale если старше `FX_STALE_THRESHOLD_SECONDS`
- Проверить доступность источника
- Увеличить таймауты или ретраи

### Неправильная наценка

1. Проверить приоритет правил: pair > source > global
2. Проверить формулу: `price1 = raw * (1 + percent/100); final = price1 + fixed`
3. Проверить режим округления и decimals

### Ошибки API

- Проверить логи синхронизации
- Проверить health статус источников
- Увеличить таймауты: `GRINEX_TIMEOUT`, `RAPIRA_TIMEOUT`

## Тестирование

```bash
# Запустить все тесты
pytest tests/test_fx_rates.py -v

# Запустить конкретный тест
pytest tests/test_fx_rates.py::TestMarkupCalculations::test_combined_markup -v
```

## Безопасность

- ✅ Все API эндпоинты требуют аутентификации
- ✅ Секреты (если будут) хранятся в ENV, не в БД
- ✅ Логирование без чувствительных данных
- ✅ Валидация всех входных данных

## Roadmap

- [ ] Поддержка HMAC авторизации для приватных API
- [ ] WebSocket подписки на тикеры
- [ ] Снапшоты курсов для аналитики
- [ ] Алерты при критических ошибках
- [ ] Grafana дашборды
- [ ] Circuit breaker для источников
- [ ] Кэширование в Redis
- [ ] A/B тестирование наценок

