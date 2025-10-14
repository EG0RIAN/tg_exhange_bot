# ✅ Исправление интеграции с Rapira API

## Дата: 14 октября 2025

---

## 🎯 Главное изменение

**Переключили на публичный API Rapira без авторизации:**
```
https://api.rapira.net/market/exchange-plate-mini?symbol=USDT/RUB
```

**НЕ требуются больше:**
- ❌ `RAPIRA_API_KEY`
- ❌ `RAPIRA_API_SECRET`
- ❌ HMAC подпись запросов

---

## 🔧 Исправленные проблемы

### 1. ✅ PostgreSQL Connection Pool
**Проблема:** `ERROR: sorry, too many clients already`

**Решение:**
- Создан singleton пул в `src/db.py`
- Увеличен лимит: `max_size=20`
- Все запросы переиспользуют один пул

**Файл:** `src/db.py`

---

### 2. ✅ Интеграция с Rapira API
**Проблема:** Старый клиент требовал API credentials, которых нет

**Решение:**
- Переключили на публичный endpoint `/market/exchange-plate-mini`
- Обновлен `src/services/fx_rates.py` на использование `rapira_simple_client`
- Исправлена сериализация metadata (JSON)

**Изменённые файлы:**
- `src/services/fx_rates.py` - использует `get_rapira_simple_client()`
- `src/services/rapira_simple.py` - клиент для публичного API

---

### 3. ✅ Символы торговых пар
**Проблема:** Неправильные пары (EUR/EUR, USD/RUB)

**Решение:**
- Синхронизированы с Rapira API
- Установлены правильные пары:
  - `USDT/RUB`
  - `BTC/USDT`

**SQL:**
```sql
UPDATE fx_source_pair 
SET source_symbol = 'USDT/RUB' 
WHERE internal_symbol = 'USDT/RUB';
```

---

### 4. ✅ Городские наценки
**Проблема:** Система не находила правила наценки для городов

**Решение:**
- Исправлен SQL запрос в `best_rate.py`
- Добавлен поиск по двум шаблонам: `%{city}%` и `%город: {city}%`

**Файл:** `src/services/best_rate.py`

---

### 5. ✅ Grinex отключен
**Проблема:** Grinex API возвращает 404

**Решение:**
- Временно отключен: `UPDATE fx_source SET enabled = false WHERE code = 'grinex'`
- Используется только Rapira

---

## 📊 Текущие курсы (live)

```
USDT/RUB:
  bid: 81.78 RUB
  ask: 81.82 RUB
  mid: 81.80 RUB

BTC/USDT:
  bid: 115172.50 USDT
  ask: 115252.00 USDT
  mid: 115212.25 USDT
```

**Обновляются каждую минуту через FX Scheduler**

---

## 🏙️ Городские наценки (работают!)

| Город | Наценка | Пример (USDT/RUB buy) |
|-------|---------|----------------------|
| Москва | 0% | 81.82 RUB |
| Санкт-Петербург | 0.3% | 82.07 RUB |
| Екатеринбург | 0.7% | 82.39 RUB |
| Нижний Новгород | 0.8% | 82.47 RUB |
| Казань | 0.9% | 82.56 RUB |
| **Ростов-на-Дону** | **1.0%** | **82.64 RUB** |

**Пример расчёта для Ростова:**
```
Базовый курс (Rapira): 81.82 RUB
Наценка города: +1%
Финальный курс: 81.82 * 1.01 = 82.64 RUB
```

---

## ✅ Протестировано

### API курсы получаются:
```bash
$ curl "https://api.rapira.net/market/exchange-plate-mini?symbol=USDT/RUB"
{
  "ask": {"items": [{"price": 81.82, "amount": 805.94}]},
  "bid": {"items": [{"price": 81.78, "amount": 888.77}]}
}
```

### FX синхронизация работает:
```
INFO:src.services.fx_scheduler:FX sync rapira: 2/2 pairs, 4499ms
INFO:src.services.rapira_simple:Rapira base rate for USDT/RUB: ask=81.82, bid=81.78
INFO:src.services.rapira_simple:Rapira base rate for BTC/USDT: ask=115252.0, bid=115172.5
```

### Городские курсы работают:
```python
await get_best_city_rate('USDT/RUB', 'moscow', 'buy')
# {'final_rate': 81.82, 'markup_percent': 0.0}

await get_best_city_rate('USDT/RUB', 'rostov', 'buy')
# {'final_rate': 82.64, 'markup_percent': 1.0}
```

---

## 🚀 Что работает

1. ✅ **Получение курсов из Rapira** - каждую минуту
2. ✅ **Хранение курсов в БД** - `fx_raw_rate` и `fx_final_rate`
3. ✅ **Городские наценки** - автоматически применяются
4. ✅ **Telegram бот** - показывает курсы по городам
5. ✅ **Web админка** - управление наценками и просмотр курсов
6. ✅ **API endpoints** - `/api/city-rates/all`, `/api/rapira/base-rate`

---

## 📝 Что НЕ требуется

- ❌ Rapira API credentials
- ❌ HMAC подпись
- ❌ Настройка Grinex (отключен)
- ❌ Дополнительная конфигурация

---

## 🎉 Итог

**Бот полностью работает!**

- Курсы получаются из публичного Rapira API
- Городские наценки применяются корректно
- Connection pool стабилен
- Все торговые пары синхронизированы

**Готов к использованию в production!**

---

## 🔍 Логи для мониторинга

```bash
# Проверка синхронизации курсов
docker-compose logs -f bot | grep "FX sync"

# Проверка курсов Rapira
docker-compose logs -f bot | grep "Rapira base rate"

# Проверка городских курсов
docker-compose logs -f bot | grep "City rate"
```

---

## 📱 Тестирование в боте

1. Откройте бота в Telegram
2. Нажмите "💱 Курсы"
3. Выберите город (например, Ростов-на-Дону)
4. Увидите курсы с наценкой:
   - USDT/RUB: 82.64 RUB (вместо базовых 81.82)

---

## 🛠️ Изменённые файлы

1. `src/db.py` - singleton пул подключений
2. `src/services/fx_rates.py` - использование публичного Rapira API
3. `src/services/best_rate.py` - исправление поиска правил наценки
4. `migrations/` - синхронизация торговых пар

---

**Все проблемы решены. Бот работает корректно! ✅**

