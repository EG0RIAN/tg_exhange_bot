# Интеграция с Rapira API

## Обзор

Модуль интеграции с Rapira API предоставляет автоматическое получение курсов валют, поддержку VWAP расчетов и применение бизнес-правил для расчета финальных курсов обмена.

## Архитектура

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Telegram Bot  │    │  RatesScheduler  │    │  RapiraProvider │
│                 │    │                  │    │                 │
│  /rapira_status │◄──►│  Auto-update     │◄──►│  HTTP Client    │
│  /rapira_vwap   │    │  every 5 sec     │    │  Retry Logic    │
│  /rapira_help   │    │                  │    │  Fallback       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ RatesCalculator  │    │   Redis Cache   │
                       │                  │    │                 │
                       │ Business Rules   │    │ 5 sec TTL       │
                       │ VWAP Support     │    │ Fallback Data   │
                       │ City Spreads     │    │                 │
                       └──────────────────┘    └─────────────────┘
```

## Основные компоненты

### 1. RapiraProvider (`src/services/rapira.py`)

Основной провайдер для работы с Rapira API:

- **get_plate_mini(symbol)** - получение мини-стакана по паре
- **get_rates()** - получение сводных курсов (fallback источник)
- **calculate_vwap(plate, side, amount)** - расчет VWAP для заданной суммы
- **Health monitoring** - мониторинг состояния API

### 2. RatesCalculator (`src/services/rates_calculator.py`)

Калькулятор курсов с применением бизнес-правил:

- **calculate_rate()** - основной метод расчета курса
- **VWAP поддержка** - расчет курса для больших сумм
- **City spreads** - применение спредов по локациям
- **Business rules** - процентные правила и фиксированные корректировки

### 3. RatesScheduler (`src/services/rates_scheduler.py`)

Планировщик автоматического обновления курсов:

- **Автообновление** каждые 5 секунд
- **Force update** - принудительное обновление
- **Status monitoring** - мониторинг состояния

### 4. Admin Handlers (`src/handlers/admin_rapira.py`)

Админские команды для управления интеграцией:

- `/rapira_status` - статус интеграции
- `/rapira_vwap` - расчет VWAP курса
- `/rapira_help` - справка по командам

## Конфигурация

### Переменные окружения

```bash
# API endpoints
RAPIRA_API_BASE=https://api.rapira.net

# Настройки запросов
RAPIRA_TIMEOUT=10
RAPIRA_MAX_RETRIES=3
RAPIRA_RETRY_DELAY=0.5

# Кэширование
RAPIRA_CACHE_TTL=5
RAPIRA_STALE_TTL=30

# Планировщик
RAPIRA_UPDATE_INTERVAL=5

# VWAP
RAPIRA_VWAP_AMOUNT=50000

# Спреды по городам (%)
RAPIRA_MOSCOW_CASH_IN_SPREAD=0.5
RAPIRA_MOSCOW_CASH_OUT_SPREAD=0.5
RAPIRA_SPB_CASH_IN_SPREAD=0.6
RAPIRA_SPB_CASH_OUT_SPREAD=0.6
RAPIRA_OTHER_CASH_IN_SPREAD=1.0
RAPIRA_OTHER_CASH_OUT_SPREAD=1.0
```

### Конфигурационный файл

Основные настройки находятся в `src/config/rapira_config.py`:

```python
from src.config.rapira_config import config

# Получение настроек
cache_ttl = config.CACHE_TTL
city_spread = config.get_city_spread("moscow", "cash_in")
```

## Использование

### Базовый расчет курса

```python
from src.services.rates import get_current_rate
from src.services.rates_calculator import OperationType

# Получение курса для CASH_IN (клиент отдает USDT)
rate = await get_current_rate(
    pair="USDT/RUB",
    operation=OperationType.CASH_IN,
    location="moscow"
)

print(f"Курс: {rate.final_rate}")
print(f"Спред: {rate.spread:.2f}%")
```

### Расчет VWAP курса

```python
from src.services.rates import calculate_vwap_rate

# Расчет VWAP для суммы $50,000
rate = await calculate_vwap_rate(
    pair="USDT/RUB",
    operation=OperationType.CASH_IN,
    amount_usd=50000.0,
    location="moscow"
)

print(f"VWAP курс: {rate.final_rate}")
print(f"VWAP сумма: ${rate.vwap_amount:,.0f}")
```

### Получение статуса интеграции

```python
from src.services.rates_scheduler import get_scheduler_status

status = await get_scheduler_status()
print(f"Планировщик работает: {status['is_running']}")
print(f"Последнее обновление: {status['last_update']}")
```

## API Endpoints

### Rapira API

1. **Plate Mini** - `GET /market/exchange-plate-mini?symbol=USDT/RUB`
   - Возвращает лучшие bid/ask и глубину стакана
   - Используется для VWAP расчетов

2. **Rates** - `GET /open/market/rates`
   - Сводные курсы по всем парам
   - Fallback источник при недоступности plate mini

### Локальные эндпоинты

- `/rapira_status` - статус интеграции
- `/rapira_vwap` - интерактивный расчет VWAP
- `/rapira_help` - справка по командам

## Бизнес-логика

### Расчет курса

1. **Получение базового курса**
   - Top-of-book: best bid/ask
   - VWAP: расчет по глубине стакана

2. **Применение спредов по локации**
   - Москва: 0.5%
   - СПб: 0.6%
   - Другие города: 1.0%

3. **Применение процентных правил**
   - Default: 0.0%
   - Premium: -0.1%

4. **Фиксированные корректировки**
   - Настраиваются по парам

5. **Округление по валюте**
   - RUB: 2 знака после запятой
   - USDT: 4 знака после запятой

### VWAP алгоритм

```python
def calculate_vwap(levels, side, target_amount):
    sorted_levels = sort_by_price(levels, side)
    total_qty = 0
    weighted_sum = 0
    
    for level in sorted_levels:
        if total_qty >= target_amount:
            break
        qty_to_use = min(level.qty, target_amount - total_qty)
        weighted_sum += level.price * qty_to_use
        total_qty += qty_to_use
    
    return weighted_sum / total_qty
```

## Мониторинг и логирование

### Health метрики

- **Latency** - время ответа API
- **HTTP код** - статус ответа
- **Freshness** - свежесть данных
- **Error count** - количество ошибок

### Логирование

```python
import logging
logger = logging.getLogger(__name__)

# Уровни логирования
logger.debug("Debug информация")
logger.info("Информационные сообщения")
logger.warning("Предупреждения")
logger.error("Ошибки")
```

## Fallback стратегия

1. **Primary**: Rapira Plate Mini API
2. **Secondary**: Rapira Rates API
3. **Cache**: Redis кэш (TTL: 5 сек)
4. **Database**: Последние известные курсы
5. **Default**: Фиксированные курсы

## Тестирование

### Запуск тестов

```bash
# Все тесты
pytest tests/test_rapira_integration.py -v

# Конкретный класс тестов
pytest tests/test_rapira_integration.py::TestRapiraProvider -v

# Конкретный тест
pytest tests/test_rapira_integration.py::TestRapiraProvider::test_get_plate_mini_success -v
```

### Тестовые сценарии

- ✅ Успешное получение курсов
- ✅ VWAP расчеты
- ✅ Fallback на кэш
- ✅ Применение бизнес-правил
- ✅ Обработка ошибок API

## Развертывание

### Docker

```dockerfile
# Добавить в Dockerfile
COPY src/config/rapira_config.py /app/src/config/
COPY src/services/rapira.py /app/src/services/
COPY src/services/rates_calculator.py /app/src/services/
COPY src/services/rates_scheduler.py /app/src/services/
COPY src/handlers/admin_rapira.py /app/src/handlers/
```

### Переменные окружения

```bash
# .env файл
RAPIRA_API_BASE=https://api.rapira.net
RAPIRA_CACHE_TTL=5
RAPIRA_UPDATE_INTERVAL=5
RAPIRA_VWAP_AMOUNT=50000
```

## Troubleshooting

### Частые проблемы

1. **API недоступен**
   - Проверить `RAPIRA_API_BASE`
   - Проверить сетевую доступность
   - Использовать `/rapira_status` для диагностики

2. **Курсы не обновляются**
   - Проверить статус планировщика
   - Проверить Redis подключение
   - Запустить force update

3. **VWAP не работает**
   - Проверить наличие данных в стакане
   - Проверить формат пары (BASE/QUOTE)
   - Проверить сумму (должна быть > 0)

### Команды диагностики

```bash
# Статус интеграции
/rapira_status

# Тест API
/rapira_test_api

# Принудительное обновление
/rapira_force_update

# Расчет VWAP
/rapira_vwap
```

## Развитие

### Планируемые улучшения

1. **Дополнительные источники**
   - Binance API
   - CoinGecko API
   - Локальные биржи

2. **Расширенные правила**
   - Динамические спреды
   - Временные корректировки
   - Пользовательские настройки

3. **Мониторинг**
   - Grafana дашборды
   - Prometheus метрики
   - Алерты в Telegram

### API версионирование

Текущая версия: v1.0

- **v1.1**: Поддержка WebSocket для real-time обновлений
- **v1.2**: Расширенная аналитика и отчеты
- **v2.0**: Микросервисная архитектура

## Лицензия

Интеграция с Rapira API является частью основного проекта и подчиняется его лицензии.

## Поддержка

Для получения поддержки:
1. Проверить `/rapira_help`
2. Изучить логи приложения
3. Использовать команды диагностики
4. Обратиться к команде разработки
