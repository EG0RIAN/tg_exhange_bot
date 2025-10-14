# Quick Test - Быстрое тестирование

## ✅ Все системы работают!

```bash
Docker Containers:
✅ postgres  - Up 10 hours (port 5432)
✅ redis     - Up 10 hours (port 6379)
✅ bot       - Up 4 minutes
✅ webadmin  - Up 4 minutes (port 8000)
```

## 🧪 Быстрые тесты

### 1. Проверка базового курса Rapira

```bash
curl -s "https://api.rapira.net/market/exchange-plate-mini?symbol=USDT/RUB" | jq '.ask.lowestPrice'
```

**Ожидаемый результат:**
```
81.83000000
```

### 2. Проверка БД - правила городов

```bash
docker-compose exec postgres psql -U exchange -d exchange \
  -c "SELECT percent, description FROM fx_markup_rule WHERE description ILIKE '%город%' ORDER BY percent;"
```

**Ожидаемый результат:**
```
Москва:            0.0%
СПб:               0.3%
Екатеринбург:      0.7%
Нижний Новгород:   0.8%
Казань:            0.9%
Ростов:            1.0%
Другие города:     1.5%
```

### 3. Проверка Web Admin

```bash
# Главная страница (требует login)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/admin
# Должно быть: 302 (редирект на login)

# Login страница
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/login
# Должно быть: 200 (OK)

# City rates (требует login)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/admin/city-rates
# Должно быть: 302 (редирект на login)
```

### 4. Проверка логов планировщика

```bash
docker-compose logs bot | grep "FX"
```

**Ожидаемый вывод:**
```
INFO:src.services.fx_scheduler:Starting FX rates scheduler...
INFO:src.services.fx_scheduler:FX rates scheduler started successfully
INFO:src.services.fx_rates:Cache refreshed: 2 sources, 4 pairs, 8 rules
```

## 🌐 Откройте в браузере

### Вариант 1: Прямая ссылка
```
http://localhost:8000/admin/city-rates
```

### Вариант 2: Через дашборд
```
1. http://localhost:8000/admin
2. Логин (из .env: ADMIN_LOGIN/ADMIN_PASSWORD)
3. Карточка "📍 Курсы по городам" (зеленая)
```

## 💡 Что вы увидите

### На странице `/admin/city-rates`:

**1. Таблица настройки наценок:**
```
Город             | Наценка | Статус  | Действия
Москва           | 0%      | Активно | [Изменить]
СПб              | +0.3%   | Активно | [Изменить]
Ростов           | +1%     | Активно | [Изменить]
Нижний Новгород  | +0.8%   | Активно | [Изменить]
...
```

**2. Карточки с курсами (после загрузки):**
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ 🗺 Москва        │  │ 🗺 Ростов        │  │ 🗺 Н.Новгород   │
│ ̶8̶1̶.̶8̶3̶ (base)    │  │ ̶8̶1̶.̶8̶3̶ (base)    │  │ ̶8̶1̶.̶8̶3̶ (base)    │
│ 81.83 ₽         │  │ 82.65 ₽         │  │ 82.48 ₽         │
│ [0%]            │  │ [+1%]           │  │ [+0.8%]         │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

**3. Базовый курс Rapira:**
```
Best Ask (покупка): 81.83 ₽
Best Bid (продажа): 81.50 ₽
Спред: 0.40%
```

## 🎯 Попробуйте

### 1. Измените наценку

```
1. Нажмите "Изменить" напротив Ростова
2. Введите: 1.2 (вместо 1.0)
3. Сохраните
4. Курс пересчитается: 81.83 × 1.012 = 82.81 ₽
```

### 2. Посмотрите другую пару

```
1. В селекторе выберите "BTC/USDT"
2. Курсы обновятся для биткоина
3. Наценки те же, но цены другие
```

### 3. Проверьте в боте

```
/admin
→ "🌐 Интеграции"
→ "🟢 Grinex Exchange"
→ Кнопка "📊 Курсы"
```

## 🐛 Если что-то не работает

### Страница не открывается
```bash
# Проверить логи
docker-compose logs webadmin

# Перезапустить
docker-compose restart webadmin
```

### Нет курсов на странице
```bash
# Проверить что правила созданы
docker-compose exec postgres psql -U exchange -d exchange \
  -c "SELECT COUNT(*) FROM fx_markup_rule WHERE description ILIKE '%город%';"
# Должно быть: 7

# Проверить API Rapira напрямую
curl "https://api.rapira.net/market/exchange-plate-mini?symbol=USDT/RUB"
```

### Ошибки в консоли браузера
```
F12 → Console → Смотрим ошибки
Возможно CORS или API недоступен
```

## 📊 Диагностика

```bash
# 1. Проверка контейнеров
docker-compose ps
# Все должны быть Up

# 2. Проверка БД
docker-compose exec postgres psql -U exchange -d exchange -c "\dt fx_*"
# Должно быть 7 таблиц fx_*

# 3. Проверка правил
docker-compose exec postgres psql -U exchange -d exchange \
  -c "SELECT COUNT(*) FROM fx_markup_rule;"
# Должно быть >= 8

# 4. Проверка логов
docker-compose logs --tail=50 bot webadmin
# Не должно быть критических ошибок
```

## 🎉 Готово!

Откройте и попробуйте:
```
http://localhost:8000/admin/city-rates
```

Логин/пароль из .env файла.

---

**Вопросы? Смотрите документацию:**
- `CITY_RATES_README.md` - Полное руководство
- `CITY_RATES_QUICKSTART.md` - Быстрый старт
- `DEPLOYMENT_COMPLETE.md` - Статус развертывания

