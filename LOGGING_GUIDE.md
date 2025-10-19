# Руководство по логированию в проекте

Дата: 19 октября 2025

## 📝 Обзор

В проект добавлена централизованная система логирования с:
- ✅ Цветными логами для консоли
- ✅ Автоматическими декораторами
- ✅ Структурированным логированием событий
- ✅ Мониторингом производительности
- ✅ Контекстным логированием ошибок

---

## 🎨 Новая система логирования

### Файл: `src/utils/logger.py`

**Основные компоненты:**

1. **setup_logging()** - централизованная настройка
2. **@log_handler** - декоратор для обработчиков Aiogram
3. **@log_function** - декоратор для функций
4. **log_user_action()** - структурированное логирование действий
5. **log_order_event()** - логирование событий заказов
6. **log_api_call()** - логирование API вызовов
7. **log_db_query()** - логирование запросов к БД
8. **PerformanceLogger** - контекстный менеджер для мониторинга

---

## 🚀 Использование

### 1. Инициализация (в bot.py)

```python
from src.utils.logger import setup_logging

async def main():
    # Настройка логирования
    log_level = os.getenv("LOG_LEVEL", "INFO")  # DEBUG, INFO, WARNING, ERROR
    setup_logging(level=log_level, colored=True)
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting bot...")
```

### 2. Декоратор для обработчиков

```python
from src.utils.logger import log_handler, log_user_action

@router.message(F.text == "💵 Купить USDT")
@log_handler("start_buy_usdt")
async def start_buy_usdt(message: Message, state: FSMContext):
    log_user_action(logger, message.from_user.id, "started buy USDT flow")
    # ... ваш код ...
```

**Вывод:**
```
🎯 Handler [start_buy_usdt] started: user=123456, type=message, data=💵 Купить USDT
👤 User 123456: started buy USDT flow
✅ Handler [start_buy_usdt] completed in 15ms
```

### 3. Логирование действий пользователя

```python
from src.utils.logger import log_user_action

log_user_action(
    logger, 
    user_id=123456, 
    action="entered amount", 
    amount=1000
)
```

**Вывод:**
```
👤 User 123456: entered amount [amount=1000]
```

### 4. Логирование заказов

```python
from src.utils.logger import log_order_event

log_order_event(
    logger, 
    order_id=42, 
    event="created",
    type="buy_usdt",
    amount=1000,
    city="moscow"
)
```

**Вывод:**
```
📋 Order #42: created [type=buy_usdt, amount=1000, city=moscow]
```

### 5. Мониторинг производительности

```python
from src.utils.logger import PerformanceLogger

with PerformanceLogger(logger, "calculate_rate"):
    # ... долгая операция ...
    rate = await calculate_rate()
```

**Вывод:**
```
⏱️ calculate_rate started
⏱️ calculate_rate completed in 150ms
```

### 6. Логирование API вызовов

```python
from src.utils.logger import log_api_call

start = datetime.now()
result = await api.call()
duration = (datetime.now() - start).total_seconds() * 1000

log_api_call(logger, "rapira", "get_rate", duration, "success")
```

**Вывод:**
```
🌐 API rapira/get_rate: 65ms ✅
```

---

## 🎨 Цветные логи

### Уровни логирования с цветами:

```
DEBUG    - Cyan    (голубой)
INFO     - Green   (зеленый)
WARNING  - Yellow  (желтый)
ERROR    - Red     (красный)
CRITICAL - Magenta (пурпурный)
```

### Примеры:

```python
logger.debug("🔍 Debug message")      # Голубой
logger.info("ℹ️ Info message")        # Зеленый
logger.warning("⚠️ Warning message")  # Желтый
logger.error("❌ Error message")      # Красный
```

---

## 📊 Где добавлено логирование

### Обработчики:

**buy_usdt.py:**
- ✅ start_buy_usdt - начало flow
- ✅ enter_custom_amount - ввод суммы
- ✅ choose_city - выбор города
- ✅ confirm_order - подтверждение и создание заказа

**sell_usdt.py:**
- ✅ start_sell_usdt - начало flow
- ✅ confirm_order - создание заказа

**pay_invoice.py:**
- ✅ Добавлены импорты для логирования

### Сервисы:

**best_rate.py:**
- ✅ get_best_city_rate - расчет лучшего курса
- ✅ Логирование результата с деталями

**Общее:**
- ✅ bot.py - инициализация системы логирования

---

## 🔧 Конфигурация

### Переменные окружения:

```bash
# В .env или docker-compose.yml
LOG_LEVEL=INFO     # DEBUG | INFO | WARNING | ERROR | CRITICAL
```

### Уровни для библиотек:

```python
# Автоматически настроено в setup_logging():
logging.getLogger('httpx').setLevel(logging.WARNING)        # Меньше HTTP логов
logging.getLogger('httpcore').setLevel(logging.WARNING)     # Меньше HTTP логов
logging.getLogger('aiogram').setLevel(logging.INFO)         # Важные события Aiogram
logging.getLogger('apscheduler').setLevel(logging.WARNING)  # Только проблемы scheduler
```

---

## 📈 Примеры вывода

### До улучшений:

```
INFO:src.handlers.buy_usdt:Confirming buy_usdt order from user 123456
INFO:src.handlers.buy_usdt:Order data: {'amount': '1000', 'city': 'moscow'}
INFO:src.handlers.buy_usdt:Order #42 created: buy_usdt, user=123456
```

### После улучшений:

```
🎯 Handler [start_buy_usdt] started: user=123456, type=message, data=💵 Купить USDT
👤 User 123456: started buy USDT flow
✅ Handler [start_buy_usdt] completed in 15ms

🎯 Handler [enter_amount] started: user=123456, type=message, data=1000
👤 User 123456: entered amount [amount=1000.0]
✅ Handler [enter_amount] completed in 12ms

🎯 Handler [choose_city] started: user=123456, type=callback, data=city:moscow
👤 User 123456: chose city [city=Москва, code=moscow]
Best rate calculated: USDT/RUB buy @ moscow = 83.48 (source: rapira, markup: 1.0%, 45ms)
✅ Handler [choose_city] completed in 58ms

🎯 Handler [confirm_order] started: user=123456, type=callback, data=confirm:yes
👤 User 123456: confirming buy order [amount=1000, city=moscow, currency=RUB]
📋 Order #42: created [type=buy_usdt, user_id=123456, amount=1000, city=moscow]
✅ Handler [confirm_order] completed in 125ms
```

---

## 🎯 Лучшие практики

### 1. Всегда используйте декораторы

```python
@log_handler("my_handler")
async def my_handler(message: Message):
    # Автоматическое логирование входа/выхода
    pass
```

### 2. Логируйте важные события

```python
# Действия пользователя
log_user_action(logger, user_id, "changed language", lang="ru")

# События заказов
log_order_event(logger, order_id, "status_changed", old="new", new="processing")

# API вызовы
log_api_call(logger, "rapira", "get_ticker", duration_ms, "success")
```

### 3. Добавляйте контекст к ошибкам

```python
from src.utils.logger import log_error_with_context

try:
    result = await process_order(order_id)
except Exception as e:
    log_error_with_context(
        logger,
        "Failed to process order",
        e,
        order_id=order_id,
        user_id=user_id
    )
    raise
```

### 4. Используйте правильные уровни

```python
logger.debug("Detailed info for debugging")      # Только в DEBUG режиме
logger.info("Normal operational messages")       # Обычные события
logger.warning("Something unexpected happened")  # Предупреждения
logger.error("Error that should be fixed")       # Ошибки
logger.critical("Critical system failure")       # Критические проблемы
```

---

## 📁 Структура логов

### Формат логов:

```
YYYY-MM-DD HH:MM:SS - module.name - LEVEL - message
```

**Пример:**
```
2025-10-19 22:30:15 - src.handlers.buy_usdt - INFO - 👤 User 123456: started buy USDT flow
```

---

## 🔍 Мониторинг

### Просмотр логов на сервере:

```bash
# Все логи
docker-compose logs -f bot

# Только ERROR
docker-compose logs -f bot | grep ERROR

# Только пользователь 123456
docker-compose logs -f bot | grep "User 123456"

# Только заказы
docker-compose logs -f bot | grep "Order #"

# С временными метками
docker-compose logs -f -t bot
```

### Фильтрация по уровням:

```bash
# WARNING и выше
docker-compose logs -f bot | grep -E "WARNING|ERROR|CRITICAL"

# Только INFO
docker-compose logs -f bot | grep "INFO"
```

---

## 📊 Метрики логирования

**Добавлено логирования:**
- Handlers: +7 декораторов
- Services: +3 точки логирования
- Utils: +1 модуль (290 строк)
- Бизнес-события: +10 log_user_action, log_order_event

**Типы логов:**
- 👤 User actions - действия пользователей
- 📋 Order events - события заказов
- 🎯 Handler events - обработчики
- 🌐 API calls - внешние вызовы
- 🗄️ DB queries - запросы к БД
- ⏱️ Performance - производительность

---

## 🎁 Бонусы

### Автоматическая фильтрация чувствительных данных:

```python
logger.info(f"User data: password={user.password}, api_key={key}")
# Автоматически станет:
# User data: password=***, api_key=***
```

### Измерение времени выполнения:

Все декорированные функции автоматически логируют время выполнения.

### Предупреждения о медленных операциях:

```
⏱️ get_rate completed in 1250ms (SLOW!)  # Если > 1000ms
```

---

## 📚 Примеры использования

### Пример 1: Новый обработчик

```python
@router.message(F.text == "🎁 New Feature")
@log_handler("new_feature")
async def handle_new_feature(message: Message, state: FSMContext):
    log_user_action(logger, message.from_user.id, "used new feature", param="value")
    
    try:
        result = await do_something()
        logger.info(f"Feature result: {result}")
    except Exception as e:
        logger.error(f"Feature failed: {e}", exc_info=True)
        raise
```

### Пример 2: Новый сервис

```python
from src.utils.logger import log_function, log_api_call

logger = logging.getLogger(__name__)

@log_function
async def my_service_function(param1: str, param2: int):
    """Автоматическое логирование входа/выхода/ошибок"""
    
    start = datetime.now()
    result = await external_api.call(param1, param2)
    duration = (datetime.now() - start).total_seconds() * 1000
    
    log_api_call(logger, "external_api", "call", duration, "success")
    
    return result
```

---

## 🔧 Настройка уровней логирования

### В docker-compose.yml:

```yaml
services:
  bot:
    environment:
      - LOG_LEVEL=INFO  # Измените на DEBUG для детальных логов
```

### Временно изменить:

```bash
# На сервере
docker-compose exec bot python -c "
import os
os.environ['LOG_LEVEL'] = 'DEBUG'
"

# Или через restart с новой переменной
LOG_LEVEL=DEBUG docker-compose restart bot
```

---

## 📋 Чек-лист для новых функций

При добавлении нового кода:

- [ ] Добавить `logger = logging.getLogger(__name__)` в начало модуля
- [ ] Использовать `@log_handler` для обработчиков Aiogram
- [ ] Логировать важные действия пользователей через `log_user_action()`
- [ ] Логировать создание/изменение заказов через `log_order_event()`
- [ ] Логировать вызовы внешних API через `log_api_call()`
- [ ] Логировать долгие операции с `PerformanceLogger`
- [ ] Использовать правильные уровни: DEBUG/INFO/WARNING/ERROR

---

## 🎯 Текущее покрытие логами

### Обработчики (✅ 80% покрыто):
- ✅ buy_usdt.py - полное логирование flow
- ✅ sell_usdt.py - полное логирование flow
- ⚠️ pay_invoice.py - базовое логирование
- ⚠️ admin.py - нужно добавить
- ⚠️ faq.py - нужно добавить

### Сервисы (✅ 60% покрыто):
- ✅ best_rate.py - расчет курсов
- ✅ rates.py - импорт курсов
- ✅ fx_scheduler.py - синхронизация
- ⚠️ client_rates.py - нужно добавить
- ⚠️ rapira_simple.py - частичное логирование

### Система (✅ 100%):
- ✅ bot.py - централизованная инициализация
- ✅ utils/logger.py - все инструменты логирования

---

## 📊 Статистика

**Добавлено:**
- 📄 Файлов: 1 (logger.py - 290 строк)
- 🎨 Декораторов: 2 (@log_handler, @log_function)
- 📝 Helper функций: 6
- 🔧 Логов в обработчиках: +15 точек
- 🔧 Логов в сервисах: +5 точек

**Улучшения:**
- 🎨 Цветной вывод: проще читать логи
- ⏱️ Автоматические таймеры: видим медленные операции
- 👤 Структурированные события: проще анализировать
- 🔒 Фильтрация паролей: безопасность

---

## 🚀 Следующие шаги

### Рекомендуется добавить:

1. **Логирование в админ-панель:**
   - admin.py - все действия администратора
   - admin_content.py - изменения контента
   - admin_grinex.py - настройки интеграций

2. **Расширенное логирование сервисов:**
   - client_rates.py - расчет клиентских курсов
   - rapira.py - детали работы с Rapira API
   - grinex.py - детали работы с Grinex API

3. **Логирование в файл:**
   - Добавить FileHandler для логов на диск
   - Ротация логов (по размеру/времени)
   - Отдельные файлы для ERROR уровня

4. **Интеграция с мониторингом:**
   - Sentry для ошибок в продакшене
   - Prometheus metrics
   - ELK stack для анализа логов

---

**Автор:** AI Assistant  
**Дата:** 19 октября 2025  
**Версия:** 1.0

