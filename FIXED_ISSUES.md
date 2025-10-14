# Fixed Issues - Исправленные проблемы

## ❌ Проблема: "Ошибка загрузки курсов"

### Причины
1. **404 на API endpoints** - неправильные маршруты (path vs query параметры)
2. **Некорректный парсинг Rapira** - lowestPrice был placeholder (99999)
3. **Отсутствие импортов** - datetime и logging не были импортированы

## ✅ Исправления

### 1. API Endpoints (`src/web_admin/main.py`)

**Было:**
```python
@app.get("/api/city-rates/all/{symbol}")  # Символ в path - проблема с /
```

**Стало:**
```python
@app.get("/api/city-rates/all")  # Символ в query параметрах
async def api_get_all_city_rates(symbol: str, ...):
```

### 2. Парсинг Rapira (`src/services/rapira_simple.py`)

**Было:**
```python
# Брали lowestPrice который может быть 99999
if 'lowestPrice' in data['ask']:
    result['best_ask'] = data['ask']['lowestPrice']  # 99999!
```

**Стало:**
```python
# Берем реальную цену из items[0]
if 'items' in data['ask'] and len(data['ask']['items']) > 0:
    result['best_ask'] = data['ask']['items'][0]['price']  # 81.83 ✓
```

### 3. JavaScript (`templates/city_rates.html`)

**Было:**
```javascript
fetch(`/api/city-rates/all/${symbol}`)  // USDT/RUB в path
```

**Стало:**
```javascript
fetch(`/api/city-rates/all?symbol=${encodeURIComponent(symbol)}`)  // В query
```

### 4. Импорты (`src/web_admin/main.py`)

**Добавлено:**
```python
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
```

## 🧪 Тестирование исправлений

### Тест 1: API работает
```bash
curl "http://localhost:8000/api/test/rapira-base-rate?symbol=USDT/RUB"
```

**Результат:**
```json
{
  "success": true,
  "symbol": "USDT/RUB",
  "best_ask": 81.83,      ✅ Правильная цена!
  "best_bid": 81.77,      ✅ Правильная цена!
  "timestamp": "2025-10-13T23:33:32"
}
```

### Тест 2: Курсы городов (через браузер)

1. Откройте: http://localhost:8000/admin/city-rates
2. Введите логин/пароль (из .env)
3. Должны увидеть:
   - Таблицу с наценками городов
   - Карточки с курсами
   - Базовый курс: Ask 81.83 ₽, Bid 81.77 ₽

### Расчет по городам (с правильным базовым курсом):

```
Москва:           81.83 × (1 + 0.0/100)  = 81.83 ₽
СПб:              81.83 × (1 + 0.3/100)  = 82.08 ₽
Ростов:           81.83 × (1 + 1.0/100)  = 82.65 ₽
Нижний Новгород:  81.83 × (1 + 0.8/100)  = 82.48 ₽
```

## 📊 Проверка в реальном времени

```bash
# Прямой запрос к Rapira API
curl -s "https://api.rapira.net/market/exchange-plate-mini?symbol=USDT/RUB" \
  | jq '.ask.items[0].price'

# Должно вернуть: 81.83 (или текущую цену)

# Наш API
curl -s "http://localhost:8000/api/test/rapira-base-rate?symbol=USDT/RUB" \
  | jq '.best_ask'

# Должно вернуть то же: 81.83
```

## ✅ Статус после исправлений

### API Endpoints
- ✅ `/api/city-rates/all` - работает
- ✅ `/api/city-rate/{city}` - работает  
- ✅ `/api/rapira/base-rate` - работает
- ✅ `/api/test/rapira-base-rate` - работает (тестовый, без auth)

### Данные
- ✅ best_ask = 81.83 ₽ (правильная цена)
- ✅ best_bid = 81.77 ₽ (правильная цена)
- ✅ Спред = 0.07% (нормальный)

### Города
- ✅ 7 правил наценки созданы
- ✅ Формула применяется корректно
- ✅ Курсы рассчитываются правильно

## 🎯 Следующие шаги

### 1. Откройте админку
```
http://localhost:8000/admin/city-rates
```

### 2. Проверьте что видите
- ✅ Таблицу настройки наценок
- ✅ Карточки городов с курсами
- ✅ Базовый курс Rapira

### 3. Попробуйте изменить наценку
- Нажмите "Изменить" у любого города
- Введите новую наценку
- Сохраните
- Курс пересчитается

## 🔍 Если всё ещё есть проблемы

### Проверка 1: Авторизация
```
http://localhost:8000/login
→ Введите логин/пароль из .env
→ После входа откройте /admin/city-rates
```

### Проверка 2: Логи
```bash
docker-compose logs --tail=20 webadmin
# Ищем ошибки
```

### Проверка 3: Консоль браузера
```
F12 → Console
→ Смотрим ошибки JavaScript
```

### Проверка 4: Тестовый эндпоинт
```bash
curl "http://localhost:8000/api/test/rapira-base-rate?symbol=USDT/RUB"
# Должен вернуть success: true
```

## 📝 Изменения в коде

### Файлы изменены:
1. `src/web_admin/main.py`
   - Добавлены импорты (logging, datetime)
   - Исправлены API маршруты (query вместо path)
   - Добавлен тестовый эндпоинт
   - Улучшена обработка ошибок

2. `src/services/rapira_simple.py`
   - Исправлен парсинг best_ask (items[0] вместо lowestPrice)
   - Фильтр placeholder значений (> 90000)

3. `templates/city_rates.html`
   - Исправлен JavaScript (query параметры)
   - Улучшена обработка ошибок

## ✅ Готово!

Проблема **"Ошибка загрузки курсов"** исправлена:
- ✅ API endpoints работают
- ✅ Rapira парсинг корректный
- ✅ JavaScript использует правильные URL
- ✅ Импорты добавлены

**Откройте и проверьте:**
```
http://localhost:8000/admin/city-rates
```

Курсы должны загружаться без ошибок! 🎉

