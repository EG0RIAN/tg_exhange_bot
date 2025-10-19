# Анализ логов бота

Дата: 19 октября 2025, 22:17 UTC

## 🔴 Критические проблемы

### 1. Telegram Conflict (Запущено несколько ботов)

**Ошибка:**
```
ERROR:aiogram.dispatcher:Failed to fetch updates - TelegramConflictError: 
Telegram server says - Conflict: terminated by other getUpdates request; 
make sure that only one bot instance is running
WARNING:aiogram.dispatcher:Sleep for 5.124707 seconds and try again... (tryings = 29)
```

**Причина:**
Одновременно запущено несколько экземпляров бота, которые пытаются получать обновления от Telegram.

**Статус контейнеров:**
```
tg_exhange_bot_bot_1        Up 6 minutes
tg_exhange_bot_webadmin_1   Up 19 minutes
tg_exhange_bot_postgres_1   Up 48 minutes
tg_exhange_bot_redis_1      Up 48 minutes
```

**Решение:**
```bash
# Остановить все контейнеры
docker-compose down

# Убедиться что нет зависших процессов
docker ps -a | grep bot

# Запустить заново
docker-compose up -d
```

---

### 2. Database numeric field overflow

**Ошибка:**
```
ERROR:src.services.rates:Failed to import rate for USDT/RUB: numeric field overflow
DETAIL: A field with precision 18, scale 8 must round to an absolute value less than 10^10.
```

**Причина:**
Курс от Rapira API превышает максимально допустимое значение для поля в БД.
Текущий тип: `NUMERIC(18, 8)` - максимум 10^10 (10,000,000,000)

**Текущий курс Rapira:**
```
ask=82.75, bid=82.7  ✅ Нормальный (в пределах)
```

**Проблема:**
Где-то в коде происходит умножение или неправильное вычисление, которое дает огромное число.

**Решение:**
Нужно проверить логику в `src/services/rates.py` и `src/services/rates_calculator.py`

---

### 3. No price available for cash_in/cash_out

**Ошибка:**
```
ERROR:src.services.rates_calculator:Top-of-book rate failed for USDT/RUB: 
No price available for USDT/RUB cash_in

ERROR:src.services.rates_calculator:Failed to calculate rate for USDT/RUB cash_in: 
No price available for USDT/RUB cash_in
```

**Причина:**
`rates_calculator` не может найти курсы типа `cash_in` и `cash_out`.

**Проблема:**
Возможно несоответствие между типами операций:
- Бот использует: `buy` / `sell`
- rates_calculator ищет: `cash_in` / `cash_out`

**Решение:**
Унифицировать типы операций во всем коде.

---

## ⚠️ Некритические проблемы

### 4. FX Grinex sync error

**Ошибка:**
```
WARNING:src.services.fx_rates:No pairs configured for source grinex
ERROR:src.services.fx_scheduler:Failed to sync FX source grinex: 'status'
Traceback:
  File "/app/src/services/fx_scheduler.py", line 101
    if result['status'] == 'success':
       ~~~~~~^^^^^^^^^^
  KeyError: 'status'
```

**Причина:**
1. Для Grinex не настроены торговые пары
2. Функция sync возвращает не тот формат результата

**Решение:**
Исправить обработку результата в `fx_scheduler.py:101`

---

### 5. Legacy rates import

**Предупреждение:**
```
INFO:src.scheduler:[Scheduler] Курсы обновлены из Rapira (legacy)
WARNING:src.services.rates_scheduler:No rates were updated from Rapira
```

**Причина:**
Используется старая (legacy) система импорта курсов, которая не работает корректно.

**Решение:**
Полностью перейти на новую систему FX rates.

---

## 📊 Статистика ошибок

| Ошибка | Частота | Критичность |
|--------|---------|-------------|
| numeric field overflow | Каждую минуту | 🔴 Критично |
| cash_in/cash_out not found | Каждую минуту | 🔴 Критично |
| Telegram Conflict | Постоянно | 🔴 Критично |
| Grinex KeyError | Каждую минуту | ⚠️ Средне |
| No rates updated | Каждую минуту | ⚠️ Средне |

---

## 🔧 План исправлений

### Приоритет 1 (Критично):

#### 1. Остановить дублирующие экземпляры бота
```bash
ssh root@109.172.85.185
cd /home/tg_exhange_bot
docker-compose down
docker ps -a  # Убедиться что нет зависших
docker-compose up -d
```

#### 2. Исправить numeric overflow
Проверить файл `src/services/rates.py`:
- Найти где происходит умножение на большое число
- Добавить валидацию перед сохранением в БД
- Логировать значение перед ошибкой

#### 3. Исправить cash_in/cash_out
В `src/services/rates_calculator.py`:
- Заменить `cash_in` → `buy`
- Заменить `cash_out` → `sell`
- Или добавить mapping между типами

### Приоритет 2 (Важно):

#### 4. Исправить FX Grinex sync
В `src/services/fx_scheduler.py:101`:
```python
# БЫЛО:
if result['status'] == 'success':

# СТАЛО:
if isinstance(result, dict) and result.get('status') == 'success':
```

#### 5. Настроить пары для Grinex
Добавить в БД пары для источника Grinex.

### Приоритет 3 (Можно позже):

#### 6. Удалить legacy rates import
Убрать старую систему, использовать только FX rates.

---

## 🎯 Быстрое решение (прямо сейчас)

### Шаг 1: Перезапустить бота корректно
```bash
docker-compose down && sleep 5 && docker-compose up -d
```

### Шаг 2: Проверить что конфликт исчез
```bash
docker-compose logs -f bot | grep -E "(Conflict|Run polling)"
```

### Шаг 3: Временно отключить проблемные модули
Закомментировать импорт legacy rates в scheduler.

---

## 📝 Лог работающих компонентов

✅ **Работает:**
- Rapira API: HTTP 200, курсы получаются
- FX sync rapira: 1/1 pairs, 68ms
- APScheduler: Jobs выполняются
- Bot polling: Активен (пытается)

❌ **Не работает:**
- Импорт курсов в БД (overflow)
- rates_calculator (неправильные типы)
- Grinex sync (KeyError)
- Telegram updates (conflict)

---

**Автор:** AI Assistant  
**Дата:** 19 октября 2025, 22:17 UTC

