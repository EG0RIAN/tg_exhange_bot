# City Rates - Курсы по городам с наценками

## 🎯 Концепция

Упрощенная логика работы с курсами Rapira:

1. **Базовый курс** - получаем из Rapira API (московский курс)
2. **Наценка по городу** - применяем процентную надбавку в зависимости от города
3. **Финальный курс** - отдаем клиенту

```
Москва:           81.83 ₽ + 0%   = 81.83 ₽  (базовый)
СПб:              81.83 ₽ + 0.3% = 82.08 ₽
Ростов:           81.83 ₽ + 1%   = 82.65 ₽
Нижний Новгород:  81.83 ₽ + 0.8% = 82.48 ₽
Другие города:    81.83 ₽ + 1.5% = 83.06 ₽
```

## 📊 Формула

```python
final_rate = base_rate * (1 + markup_percent/100) + fixed
```

**Где:**
- `base_rate` - курс из Rapira API (best ask или best bid)
- `markup_percent` - процентная наценка города (может быть 0)
- `fixed` - фиксированная надбавка (обычно 0)

## 🌍 Настроенные города

| Город | Код | Наценка | Пример (от 81.83 ₽) |
|-------|-----|---------|----------------------|
| Москва | `moscow` | 0% | 81.83 ₽ |
| Санкт-Петербург | `spb` | +0.3% | 82.08 ₽ |
| Екатеринбург | `ekaterinburg` | +0.7% | 82.40 ₽ |
| Нижний Новгород | `nizhniy_novgorod` | +0.8% | 82.48 ₽ |
| Казань | `kazan` | +0.9% | 82.57 ₽ |
| Ростов-на-Дону | `rostov` | +1.0% | 82.65 ₽ |
| Другие города | `other` | +1.5% | 83.06 ₽ |

## 🚀 Использование

### Web Admin

Откройте: http://localhost:8000/admin/city-rates

**Возможности:**
- ✅ Просмотр курсов для всех городов
- ✅ Сравнение базового и финального курса
- ✅ Изменение наценки любого города
- ✅ Real-time обновление
- ✅ Выбор пары (USDT/RUB, BTC/USDT и т.д.)

### REST API

#### Получить курс для конкретного города

```bash
GET /api/city-rate/{city}/{symbol}?operation=buy

# Пример
curl "http://localhost:8000/api/city-rate/rostov/USDT%2FRUB?operation=buy"
```

**Ответ:**
```json
{
  "symbol": "USDT/RUB",
  "city": "rostov",
  "base_rate": 81.83,
  "markup_percent": 1.0,
  "markup_fixed": 0.0,
  "final_rate": 82.65,
  "operation": "buy",
  "timestamp": "2025-10-13T16:30:00"
}
```

#### Получить курсы для всех городов

```bash
GET /api/city-rates/all/{symbol}?operation=buy

# Пример
curl "http://localhost:8000/api/city-rates/all/USDT%2FRUB?operation=buy"
```

**Ответ:**
```json
{
  "symbol": "USDT/RUB",
  "operation": "buy",
  "cities": {
    "moscow": {
      "city": "moscow",
      "base_rate": 81.83,
      "final_rate": 81.83,
      "markup_percent": 0.0
    },
    "rostov": {
      "city": "rostov",
      "base_rate": 81.83,
      "final_rate": 82.65,
      "markup_percent": 1.0
    },
    ...
  },
  "timestamp": "2025-10-13T16:30:00"
}
```

#### Получить базовый курс из Rapira

```bash
GET /api/rapira/base-rate/{symbol}

# Пример
curl "http://localhost:8000/api/rapira/base-rate/USDT%2FRUB"
```

**Ответ:**
```json
{
  "symbol": "USDT/RUB",
  "best_ask": 81.83,
  "best_bid": 81.50,
  "timestamp": "2025-10-13T16:30:00"
}
```

### Python API

```python
from src.services.rapira_simple import get_city_rate, get_rapira_simple_client

# Получить курс для Ростова
rate = await get_city_rate("USDT/RUB", "rostov", "buy")
print(f"Курс для Ростова: {rate['final_rate']} ₽")
print(f"Базовый курс: {rate['base_rate']} ₽")
print(f"Наценка: {rate['markup_percent']}%")

# Получить базовый курс из Rapira
client = await get_rapira_simple_client()
base_data = await client.get_base_rate("USDT/RUB")
print(f"Москва ask: {base_data['best_ask']}")
print(f"Москва bid: {base_data['best_bid']}")
```

## 🔧 Настройка

### 1. Применить миграцию

```bash
docker-compose exec postgres psql -U exchange -d exchange -f /app/migrations/005_city_markups.sql
```

### 2. Добавить города (если нужны новые)

```sql
INSERT INTO fx_markup_rule (level, percent, fixed, enabled, description, rounding_mode, round_to)
VALUES ('global', 1.2, 0, true, 'Наценка для города: krasnodar (Краснодар)', 'ROUND_HALF_UP', 2);
```

### 3. Изменить наценку города

**Через Web Admin:**
1. Откройте http://localhost:8000/admin/city-rates
2. Нажмите "Изменить" напротив города
3. Введите новую наценку в процентах
4. Сохраните

**Через SQL:**
```sql
UPDATE fx_markup_rule
SET percent = 1.2
WHERE description ILIKE '%город: rostov%';
```

**Через API:**
```bash
curl -X POST http://localhost:8000/api/city-rates/update-markup \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "city=rostov&percent=1.2"
```

## 📊 Как это работает

### Пример: Клиент покупает USDT в Ростове

1. **Запрос к Rapira API:**
   ```
   GET https://api.rapira.net/market/exchange-plate-mini?symbol=USDT/RUB
   ```

2. **Получаем базовый курс (best ask):**
   ```
   best_ask = 81.83 ₽
   ```

3. **Применяем наценку Ростова (+1%):**
   ```
   final_rate = 81.83 * (1 + 1.0/100)
   final_rate = 81.83 * 1.01
   final_rate = 82.65 ₽
   ```

4. **Отдаем клиенту:**
   ```
   Курс для Ростова: 82.65 ₽
   ```

### Пример: Клиент продает USDT в Нижнем Новгороде

1. **Получаем базовый курс (best bid):**
   ```
   best_bid = 81.50 ₽
   ```

2. **Применяем наценку (+0.8%):**
   ```
   final_rate = 81.50 * 1.008 = 82.15 ₽
   ```

## 🎨 Web Admin Interface

### Главная страница `/admin/city-rates`

**Верхняя секция - Настройка наценок:**
- Таблица всех городов с текущими наценками
- Кнопки "Изменить" для каждого города
- Статус (Активно/Выкл)
- Последнее обновление

**Средняя секция - Текущие курсы:**
- Карточки для каждого города
- Базовый курс (зачеркнутый)
- Финальный курс (большой, зеленый)
- Badge с наценкой (цветной по значению)
- Выбор пары (USDT/RUB, BTC/USDT и т.д.)

**Нижняя секция - Базовый курс Rapira:**
- Best Ask (покупка)
- Best Bid (продажа)
- Спред

## 🔐 Безопасность

- ✅ Все API endpoints требуют аутентификации
- ✅ Только админы могут изменять наценки
- ✅ Валидация всех входных данных

## 📈 Мониторинг

### Проверка базового курса

```bash
# Через API
curl "http://localhost:8000/api/rapira/base-rate/USDT%2FRUB"

# Напрямую из Rapira
curl "https://api.rapira.net/market/exchange-plate-mini?symbol=USDT/RUB" | jq '.ask.lowestPrice'
```

### Логи

```bash
# Логи получения курсов
docker-compose logs webadmin | grep "Rapira base rate"

# Логи наценок
docker-compose logs webadmin | grep "City rate for"
```

## ❓ FAQ

### Как добавить новый город?

```sql
INSERT INTO fx_markup_rule (level, percent, fixed, enabled, description, rounding_mode, round_to)
VALUES ('global', 1.3, 0, true, 'Наценка для города: sochi (Сочи)', 'ROUND_HALF_UP', 2);
```

Затем обновите словарь `CITIES` в `src/services/rapira_simple.py`.

### Как временно отключить наценку города?

```sql
UPDATE fx_markup_rule
SET enabled = false
WHERE description ILIKE '%город: rostov%';
```

Или через Web Admin - кнопка "Изменить" → снять галочку "Активно".

### Разница между operation=buy и operation=sell?

- **buy** - клиент покупает USDT, платит RUB → используем ask (цена выше)
- **sell** - клиент продает USDT, получает RUB → используем bid (цена ниже)

### Можно ли отрицательную наценку (скидку)?

Да! Установите отрицательный процент:

```sql
UPDATE fx_markup_rule
SET percent = -0.5  -- скидка 0.5%
WHERE description ILIKE '%город: moscow%';
```

## 🔗 Связанные модули

- **Rapira Simple Client** (`src/services/rapira_simple.py`) - получение базовых курсов
- **FX Markup Rules** (`migrations/004_fx_rates_system.sql`) - система наценок
- **Web Admin** (`src/web_admin/main.py`) - API endpoints
- **City Rates Page** (`templates/city_rates.html`) - интерфейс

## ✅ Готово к использованию

1. Примените миграцию: `migrations/005_city_markups.sql`
2. Перезапустите: `docker-compose restart webadmin`
3. Откройте: http://localhost:8000/admin/city-rates

---

**Просто. Понятно. Гибко.** 🚀

