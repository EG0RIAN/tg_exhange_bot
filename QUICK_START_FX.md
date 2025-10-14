# Quick Start - FX Rates System

## 🚀 Запуск за 5 минут

### Шаг 1: Применить миграцию БД

```bash
cd /Users/arkhiptsev/dev/tg_exchange_bot

# Применить миграцию
docker-compose exec postgres psql -U exchange -d exchange -f /app/migrations/004_fx_rates_system.sql
```

### Шаг 2: Добавить переменные в .env

Добавьте в файл `.env` (или создайте если нет):

```bash
# FX Module Settings
FX_UPDATE_INTERVAL_SECONDS=60
FX_STALE_CHECK_INTERVAL=300
FX_STALE_THRESHOLD_SECONDS=180

# Grinex API
GRINEX_API_BASE=https://api.grinex.io
GRINEX_TIMEOUT=5
GRINEX_MAX_RETRIES=3
```

### Шаг 3: Перезапустить контейнеры

```bash
docker-compose restart bot webadmin
```

### Шаг 4: Проверить работу

Откройте в браузере:

```
http://localhost:8000/admin/fx/sources
```

Логин/пароль - как обычно для админки.

## 📍 Основные URL

| Раздел | URL |
|--------|-----|
| Источники | http://localhost:8000/admin/fx/sources |
| Правила наценки | http://localhost:8000/admin/fx/markup-rules |
| Текущие курсы | http://localhost:8000/admin/fx/rates |
| Логи синхронизации | http://localhost:8000/admin/fx/logs |

## 🔧 Первая настройка

### 1. Проверить источники

Перейдите в `/admin/fx/sources` и нажмите **"Sync Now"** для каждого источника.

### 2. Создать правило наценки

Перейдите в `/admin/fx/markup-rules` → **"Create New Rule"**

**Пример глобального правила (1% на всё):**
- Level: Global
- Percent: 1.0
- Fixed: 0
- Enabled: ✓

**Пример правила для конкретной пары (+2% + 10 RUB на USDT/RUB):**
- Level: Pair
- Source: Grinex
- Pair: USDT/RUB
- Percent: 2.0
- Fixed: 10.0
- Enabled: ✓

### 3. Проверить результат

Перейдите в `/admin/fx/rates` - должны появиться курсы с примененными наценками.

## 🧪 Тестирование API

```bash
# Получить все курсы
curl http://localhost:8000/api/fx/rates

# Получить конкретную пару
curl "http://localhost:8000/api/fx/rates?base=USDT&quote=RUB&source=grinex"

# Принудительная синхронизация
curl -X POST http://localhost:8000/api/fx/sync

# Статус планировщика
curl http://localhost:8000/api/fx/scheduler/status
```

## 📊 Проверка логов

```bash
# Все логи FX модуля
docker-compose logs bot | grep -i fx

# Только ошибки
docker-compose logs bot | grep -i "fx.*error"

# Логи последней синхронизации
docker-compose logs --tail=50 bot | grep "FX sync"
```

## ❓ Troubleshooting

### Курсы не появляются

1. Проверьте логи: `docker-compose logs bot | grep FX`
2. Триггерните синхронизацию вручную: кнопка "Sync Now" в админке
3. Проверьте `/admin/fx/logs` на наличие ошибок

### Неправильная наценка

1. Проверьте приоритет правил: Pair > Source > Global
2. Формула: `price1 = raw * (1 + percent/100); final = price1 + fixed`
3. Проверьте что правило `enabled = true`

### Planировщик не работает

```bash
# Проверить статус
curl http://localhost:8000/api/fx/scheduler/status

# Перезапустить бота
docker-compose restart bot
```

## 📚 Дополнительно

- Полная документация: `FX_RATES_README.md`
- Детали реализации: `FX_IMPLEMENTATION_SUMMARY.md`
- Тесты: `tests/test_fx_rates.py`

---

Если что-то не работает - проверьте логи: `docker-compose logs bot webadmin`

