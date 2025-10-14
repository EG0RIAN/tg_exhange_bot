# Quick Start - Курсы по городам

## 🚀 Запуск за 3 шага

### Шаг 1: Применить миграцию

```bash
docker-compose exec postgres psql -U exchange -d exchange -f /app/migrations/005_city_markups.sql
```

**Что делает миграция:**
- Создает 7 правил наценки для городов
- Москва (0%), СПб (+0.3%), Ростов (+1%), НН (+0.8%), Екб (+0.7%), Казань (+0.9%), Другие (+1.5%)

### Шаг 2: Перезапустить webadmin

```bash
docker-compose restart webadmin
```

### Шаг 3: Открыть админку

```
http://localhost:8000/admin/city-rates
```

## 📊 Что вы увидите

### 1. Таблица наценок
```
Город              | Наценка | Статус  | Действия
Москва            | 0%      | Активно | [Изменить]
СПб               | +0.3%   | Активно | [Изменить]
Ростов            | +1%     | Активно | [Изменить]
Нижний Новгород   | +0.8%   | Активно | [Изменить]
...
```

### 2. Карточки с курсами
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ 🗺 Москва        │  │ 🗺 Ростов        │  │ 🗺 Н.Новгород   │
│ ̶8̶1̶.̶8̶3̶            │  │ ̶8̶1̶.̶8̶3̶            │  │ ̶8̶1̶.̶8̶3̶            │
│ 81.83 ₽         │  │ 82.65 ₽         │  │ 82.48 ₽         │
│ [0%]   Покупка  │  │ [+1%]  Покупка  │  │ [+0.8%] Покупка │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### 3. Базовый курс Rapira
```
Best Ask (покупка): 81.83 ₽
Best Bid (продажа): 81.50 ₽
Спред: 0.40%
```

## ✏️ Изменить наценку

### Через интерфейс:
1. Нажмите "Изменить" напротив города
2. Введите новую наценку (например: `1.2` для +1.2%)
3. Нажмите "Сохранить"

### Через SQL:
```sql
-- Изменить наценку Ростова на 1.2%
UPDATE fx_markup_rule
SET percent = 1.2
WHERE description ILIKE '%город: rostov%';
```

## 🧪 Тест API

```bash
# Получить курс для Ростова
curl "http://localhost:8000/api/city-rate/rostov/USDT%2FRUB?operation=buy"

# Получить курсы для всех городов
curl "http://localhost:8000/api/city-rates/all/USDT%2FRUB?operation=buy"

# Базовый курс из Rapira
curl "http://localhost:8000/api/rapira/base-rate/USDT%2FRUB"

# Обновить наценку (нужна аутентификация)
curl -X POST "http://localhost:8000/api/city-rates/update-markup" \
  -d "city=rostov&percent=1.2"
```

## 📍 Интеграция в бота

### Пример использования в хендлере:

```python
from src.services.rapira_simple import get_city_rate

@router.message(Command("rate"))
async def cmd_rate(message: types.Message):
    # Получаем город пользователя (из БД или FSM)
    user_city = "rostov"  # Например, из профиля
    
    # Получаем курс
    rate = await get_city_rate("USDT/RUB", user_city, "buy")
    
    if rate:
        await message.answer(
            f"💰 Курс USDT/RUB для {user_city}:\n"
            f"Базовый: {rate['base_rate']:.2f} ₽\n"
            f"Наценка: +{rate['markup_percent']}%\n"
            f"**Итого: {rate['final_rate']:.2f} ₽**"
        )
```

## 🎯 Добавить город в бот

### 1. Создать FSM для выбора города

```python
class OrderFSM(StatesGroup):
    choosing_city = State()
    choosing_amount = State()

@router.message(Command("order"))
async def start_order(message: types.Message, state: FSMContext):
    # Показываем клавиатуру с городами
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏛 Москва", callback_data="city:moscow")],
        [InlineKeyboardButton(text="🌉 СПб", callback_data="city:spb")],
        [InlineKeyboardButton(text="🏭 Ростов", callback_data="city:rostov")],
        [InlineKeyboardButton(text="🏰 Н.Новгород", callback_data="city:nizhniy_novgorod")],
    ])
    
    await message.answer("Выберите ваш город:", reply_markup=keyboard)
    await state.set_state(OrderFSM.choosing_city)

@router.callback_query(lambda c: c.data.startswith("city:"))
async def process_city(callback: types.CallbackQuery, state: FSMContext):
    city = callback.data.split(":")[1]
    await state.update_data(city=city)
    
    # Получаем и показываем курс
    rate = await get_city_rate("USDT/RUB", city, "buy")
    
    await callback.message.edit_text(
        f"✅ Город: {CITIES[city]}\n"
        f"💰 Курс: {rate['final_rate']:.2f} ₽\n\n"
        f"Введите сумму:"
    )
    await state.set_state(OrderFSM.choosing_amount)
```

## 📋 Сравнение логик

### Старая логика (сложная):
```python
# Rapira API → VWAP расчеты → Спреды → Корректировки → Бизнес-правила
# Много шагов, сложная конфигурация
```

### Новая логика (простая):
```python
# Rapira API → Наценка по городу → Готово!
# Один источник (Rapira) → Настройка наценок в админке → Все города получают свои курсы
```

## ✅ Преимущества

- ✅ **Просто**: Один источник (Rapira), одна формула
- ✅ **Гибко**: Настройка наценки каждого города в 1 клик
- ✅ **Прозрачно**: Видно базовый и финальный курс
- ✅ **Быстро**: Нет сложных вычислений, прямое применение наценки
- ✅ **Удобно**: Web интерфейс для управления

## 🎬 Демо

1. Откройте http://localhost:8000/admin
2. Нажмите карточку "📍 Курсы по городам"
3. Увидите все курсы с наценками
4. Попробуйте изменить наценку для любого города
5. Курс пересчитается автоматически

---

**Вот и всё!** 🎉

Один парсер Rapira → Настройка наценок в админке → Курсы для всех городов готовы!

