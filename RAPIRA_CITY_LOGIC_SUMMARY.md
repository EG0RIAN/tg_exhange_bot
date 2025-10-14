# Rapira City Logic - Итоговое резюме

## 🎯 Реализованная логика

### Концепция
```
Один парсер Rapira → Базовый курс (Москва) → Наценки по городам → Готово!
```

### Формула
```
final_rate = base_rate * (1 + markup_percent/100)
```

**Пример:**
- Базовый курс (Москва): 81.83 ₽
- Ростов (+1%): 81.83 × 1.01 = **82.65 ₽**
- Нижний Новгород (+0.8%): 81.83 × 1.008 = **82.48 ₽**

## ✅ Что реализовано

### 1. Backend (`src/services/rapira_simple.py`)
- ✅ Упрощенный клиент Rapira
- ✅ Функция `get_base_rate(symbol)` - получение базового курса
- ✅ Функция `get_city_rate(symbol, city, operation)` - курс с наценкой
- ✅ Поддержка buy/sell операций
- ✅ Автоматическое применение наценок из БД

### 2. Database (`migrations/005_city_markups.sql`)
- ✅ 7 правил наценки для городов:
  - Москва: 0% (базовый)
  - СПб: +0.3%
  - Екатеринбург: +0.7%
  - Нижний Новгород: +0.8%
  - Казань: +0.9%
  - Ростов: +1%
  - Другие: +1.5%

### 3. Web Admin API (`src/web_admin/main.py`)
- ✅ `GET /admin/city-rates` - страница управления
- ✅ `GET /api/city-rate/{city}/{symbol}` - курс для города
- ✅ `GET /api/city-rates/all/{symbol}` - курсы всех городов
- ✅ `POST /api/city-rates/update-markup` - изменить наценку
- ✅ `GET /api/rapira/base-rate/{symbol}` - базовый курс Rapira

### 4. Web UI (`templates/city_rates.html`)
- ✅ Таблица настройки наценок по городам
- ✅ Карточки с курсами для каждого города
- ✅ Базовый курс из Rapira (Ask/Bid/Spread)
- ✅ Редактирование наценок в модальном окне
- ✅ Real-time обновление
- ✅ Выбор пары (USDT/RUB, BTC/USDT и т.д.)

### 5. Dashboard Integration
- ✅ Новая карточка "📍 Курсы по городам" (зеленый градиент)
- ✅ 4 карточки интеграций вместо 3

### 6. Documentation
- ✅ `CITY_RATES_README.md` - полное руководство
- ✅ `CITY_RATES_QUICKSTART.md` - быстрый старт
- ✅ `RAPIRA_CITY_LOGIC_SUMMARY.md` - это резюме

## 📊 Визуальная схема

```
┌─────────────────────────────────────────────────────────┐
│                    Rapira API                            │
│        https://api.rapira.net/market/exchange-plate-mini │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
           ┌─────────────────────┐
           │  Базовый курс       │
           │  (Москва)           │
           │  81.83 ₽            │
           └──────────┬──────────┘
                      │
      ┌───────────────┼───────────────┐
      │               │               │
      ▼               ▼               ▼
┌──────────┐   ┌──────────┐   ┌──────────┐
│ Москва   │   │ Ростов   │   │ Н.Новг.  │
│  0%      │   │  +1%     │   │  +0.8%   │
│ 81.83 ₽  │   │ 82.65 ₽  │   │ 82.48 ₽  │
└──────────┘   └──────────┘   └──────────┘
```

## 🔧 Настройка городов

### Через Web Admin
1. http://localhost:8000/admin/city-rates
2. Кнопка "Изменить" напротив города
3. Ввести новую наценку (например: 1.2)
4. Сохранить

### Через SQL
```sql
-- Ростов теперь +1.2%
UPDATE fx_markup_rule
SET percent = 1.2
WHERE description ILIKE '%город: rostov%';

-- Екатеринбург теперь +0.5%
UPDATE fx_markup_rule
SET percent = 0.5
WHERE description ILIKE '%город: ekaterinburg%';
```

### Через API
```bash
curl -X POST http://localhost:8000/api/city-rates/update-markup \
  -d "city=rostov&percent=1.2"
```

## 📍 Добавить новый город

### 1. SQL миграция
```sql
INSERT INTO fx_markup_rule (level, percent, fixed, enabled, description, rounding_mode, round_to)
VALUES ('global', 1.1, 0, true, 'Наценка для города: sochi (Сочи)', 'ROUND_HALF_UP', 2);
```

### 2. Обновить код (опционально)
В `src/services/rapira_simple.py`:
```python
CITIES = {
    'moscow': 'Москва',
    'rostov': 'Ростов-на-Дону',
    'nizhniy_novgorod': 'Нижний Новгород',
    'spb': 'Санкт-Петербург',
    'ekaterinburg': 'Екатеринбург',
    'kazan': 'Казань',
    'sochi': 'Сочи',  # <-- Новый город
    'other': 'Другие города'
}
```

## 🌐 API Endpoints

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/admin/city-rates` | GET | Web страница управления |
| `/api/city-rate/{city}/{symbol}` | GET | Курс для города |
| `/api/city-rates/all/{symbol}` | GET | Курсы всех городов |
| `/api/city-rates/update-markup` | POST | Изменить наценку |
| `/api/rapira/base-rate/{symbol}` | GET | Базовый курс Rapira |

## 💡 Примеры использования

### В боте (получить курс для пользователя)

```python
from src.services.rapira_simple import get_city_rate

# Из профиля пользователя
user_city = user_profile['city']  # 'rostov'

# Получаем курс
rate = await get_city_rate("USDT/RUB", user_city, "buy")

await message.answer(
    f"💰 Ваш курс в городе {rate['city']}:\n"
    f"**{rate['final_rate']:.2f} ₽** за 1 USDT\n\n"
    f"_Базовый курс: {rate['base_rate']:.2f} ₽_\n"
    f"_Наценка города: +{rate['markup_percent']}%_"
)
```

### В админке (показать все курсы)

```python
from src.services.rapira_simple import CITIES

cities_data = {}
for city_code in CITIES.keys():
    rate = await get_city_rate("USDT/RUB", city_code, "buy")
    cities_data[city_code] = rate

# Отобразить в таблице/карточках
```

## 🔄 Интеграция с существующими системами

### Совместимость с FX Rates
- ✅ Использует существующую таблицу `fx_markup_rule`
- ✅ Работает параллельно с Grinex/другими источниками
- ✅ Те же принципы приоритета правил
- ✅ Та же формула наценки

### Не конфликтует с:
- ✅ FX Sources (Grinex, Rapira как источник)
- ✅ FX Markup Rules (общие правила)
- ✅ Старой логикой Rapira (можно использовать обе)

## 📈 Преимущества новой логики

| Аспект | Старая логика | Новая логика |
|--------|---------------|--------------|
| Сложность | Высокая (VWAP, спреды, корректировки) | Низкая (базовый + наценка) |
| Настройка | Много параметров | Один процент на город |
| Прозрачность | Сложно объяснить клиенту | Понятно: Москва + наценка |
| Гибкость | Ограниченная | Любая наценка любому городу |
| Управление | Через код/ENV | Через админку в 1 клик |

## ✅ Чеклист запуска

- [x] Миграция создана (`005_city_markups.sql`)
- [x] Клиент Rapira упрощен (`rapira_simple.py`)
- [x] API endpoints добавлены (`main.py`)
- [x] Web UI создан (`city_rates.html`)
- [x] Dashboard обновлен (новая карточка)
- [x] Документация написана
- [ ] Миграция применена
- [ ] Webadmin перезапущен
- [ ] Протестировано в браузере

## 🚀 Следующие шаги

```bash
# 1. Применить миграцию
docker-compose exec postgres psql -U exchange -d exchange -f /app/migrations/005_city_markups.sql

# 2. Перезапустить
docker-compose restart webadmin

# 3. Открыть
http://localhost:8000/admin/city-rates

# 4. Проверить API
curl "http://localhost:8000/api/rapira/base-rate/USDT%2FRUB"
curl "http://localhost:8000/api/city-rates/all/USDT%2FRUB?operation=buy"
```

---

**Готово к использованию!** 🎉

Простая, понятная логика: **Rapira базовый курс + наценка города = финальный курс для клиента**

