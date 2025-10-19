# Аудит логики клавиатур

Дата: 19 октября 2025

## 🔍 Обнаруженные проблемы

### ❌ Критические проблемы:

#### 1. **Дублирование функций клавиатур**

**Проблема:** Две почти идентичные функции для городов:
- `get_priority_cities_keyboard()` (строка 28) - с кнопкой менеджера
- `get_cities_keyboard()` (строка 134) - без кнопки менеджера

```python
# Строка 28
async def get_priority_cities_keyboard() -> InlineKeyboardMarkup:
    # ... cities ...
    return add_manager_button(kb)

# Строка 134 - ДУБЛИКАТ!
async def get_cities_keyboard() -> InlineKeyboardMarkup:
    # ... те же города ...
    return kb  # БЕЗ кнопки менеджера
```

**Использование:**
- `get_priority_cities_keyboard()` - используется в 5 местах
- `get_cities_keyboard()` - используется в 3 местах

**Решение:** Удалить `get_cities_keyboard()`, использовать везде `get_priority_cities_keyboard()`

---

#### 2. **Кнопка "Настройки" не в главном меню**

**Проблема:** В `src/handlers/settings.py` есть обработчик:
```python
@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message, state: FSMContext):
    await message.answer("Выберите язык:", ...)
```

Но в главном меню (`main_menu`) нет кнопки "⚙️ Настройки"!

**Текущее главное меню:**
```python
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💵 Купить USDT")],
        [KeyboardButton(text="💸 Продать USDT")],
        [KeyboardButton(text="📄 Оплатить инвойс")],
        [KeyboardButton(text="📖 FAQ")],
        [KeyboardButton(text="👨‍💼 Связаться с менеджером")],
        # ❌ Нет кнопки "⚙️ Настройки"
    ],
    resize_keyboard=True
)
```

**Решение:** Добавить кнопку "⚙️ Настройки" в главное меню

---

#### 3. **Несогласованность callback_data**

**Проблема:** Разные префиксы для кнопок "Назад":
- В обычных flow: `callback_data="back"`
- В FAQ flow: `callback_data="faq_back"`
- В городах: `callback_data="back_to_priority_cities"`

**Пример:**
```python
# В get_priority_cities_keyboard()
[InlineKeyboardButton(text="🔙 Назад", callback_data="back")]

# В get_faq_categories_keyboard()
[InlineKeyboardButton(text="🔙 Назад", callback_data="faq_back")]

# В get_all_cities_keyboard()
[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_priority_cities")]
```

**Проблема:** Усложняет логику обработчиков, каждый flow должен обрабатывать свои callback

**Решение:** Унифицировать или четко документировать

---

### ⚠️ Средние проблемы:

#### 4. **Кнопка менеджера добавляется везде**

**Проблема:** Функция `add_manager_button()` добавляет кнопку "Связаться с менеджером" во все inline клавиатуры

**Плюсы:**
- ✅ Удобно для пользователя
- ✅ Всегда есть способ связаться

**Минусы:**
- ❌ Клавиатуры становятся длиннее
- ❌ Занимает место на экране
- ❌ В админских клавиатурах не нужна

**Текущее поведение:**
```python
def add_manager_button(keyboard: InlineKeyboardMarkup) -> InlineKeyboardMarkup:
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="👨‍💼 Связаться с менеджером", 
                           callback_data="contact_manager")
    ])
    return keyboard
```

Добавляется в:
- `get_priority_cities_keyboard()`
- `get_all_cities_keyboard()`
- `get_currencies_keyboard()`
- `get_amount_keyboard_v2()`
- `get_payment_methods_keyboard()`
- `get_invoice_purposes_keyboard()`
- `get_confirm_keyboard_v2()`
- `get_rate_confirm_keyboard()`

НЕ добавляется в:
- Админские клавиатуры
- FAQ клавиатуры
- `get_cities_keyboard()` (дубликат)

---

#### 5. **Обработчик `back_to_priority_cities` не найден в основных handlers**

**Проблема:** В `keyboards.py`:
```python
kb.inline_keyboard.append([
    InlineKeyboardButton(text="🔙 Назад", 
                       callback_data="back_to_priority_cities")
])
```

**Обработчик найден только в:**
- `src/handlers/menu.py:106` (для просмотра курсов)

**Но не найден в:**
- `src/handlers/buy_usdt.py`
- `src/handlers/sell_usdt.py`
- `src/handlers/pay_invoice.py`

**Есть отдельный обработчик:**
```python
@router.callback_query(BuyUSDTStates.choose_city, F.data == "back_to_priority_cities")
async def back_to_priority_cities(callback: CallbackQuery):
    # Обработка внутри FSM
```

**Решение:** Убедиться что все flow обрабатывают `back_to_priority_cities`

---

### 💡 Рекомендации по улучшению:

#### 6. **Отсутствие универсального callback роутера**

**Проблема:** Каждый handler дублирует обработку одинаковых callback:
- `contact_manager` обрабатывается в 3 местах
- `back` обрабатывается в каждом FSM отдельно

**Решение:** Создать middleware или универсальный роутер для общих callback

---

#### 7. **Админские клавиатуры смешаны с клиентскими**

**Проблема:** Все клавиатуры в одном файле `keyboards.py` (322 строки)

**Клиентские:**
- main_menu
- get_priority_cities_keyboard
- get_currencies_keyboard
- get_confirm_keyboard_v2
- FAQ клавиатуры

**Админские:**
- get_admin_menu_keyboard
- get_admin_content_keyboard
- get_admin_integrations_keyboard
- get_trading_pairs_keyboard
- get_rates_list_keyboard
- get_admin_orders_keyboard
- и т.д.

**Решение:** Разделить на:
- `src/keyboards/client.py`
- `src/keyboards/admin.py`

---

## 📋 Структура текущих клавиатур

### Клиентские (ReplyKeyboard):
```
main_menu (5 кнопок)
├── 💵 Купить USDT
├── 💸 Продать USDT
├── 📄 Оплатить инвойс
├── 📖 FAQ
└── 👨‍💼 Связаться с менеджером
    ❌ Нет: ⚙️ Настройки
```

### Клиентские flow (InlineKeyboard):

**Покупка/Продажа USDT:**
```
1. get_amount_keyboard_v2() → Ввод суммы
2. get_priority_cities_keyboard() → Выбор города
   ├── city:moscow, city:spb, ...
   ├── city:other → get_all_cities_keyboard()
   └── back
3. get_rate_confirm_keyboard() → Подтверждение курса
   ├── rate:confirm
   ├── rate:cancel
   └── back
4. get_currencies_keyboard() → Выбор валюты
   ├── currency:RUB
   └── back
5. (Ввод username - текст)
6. get_confirm_keyboard_v2() → Финальное подтверждение
   ├── confirm:yes
   ├── confirm:edit
   └── confirm:cancel
```

**Оплата инвойса:**
```
1. get_invoice_purposes_keyboard() → Цель
2. get_payment_methods_keyboard() → Способ оплаты
3. (Ввод суммы/реквизитов - текст)
4. get_confirm_keyboard_v2() → Подтверждение
```

**FAQ:**
```
1. get_faq_categories_keyboard() → Категории
2. get_faq_questions_keyboard() → Вопросы
3. get_faq_answer_keyboard() → Ответ
```

### Админские (InlineKeyboard):
```
get_admin_menu_keyboard()
├── admin_rates → get_rates_list_keyboard()
├── admin_faq → get_admin_faq_categories_keyboard()
├── admin_orders → get_admin_orders_keyboard()
├── admin_broadcast
├── admin_logs → get_logs_filter_keyboard()
├── admin_content → get_admin_content_keyboard()
└── admin_integrations → get_admin_integrations_keyboard()
```

---

## ✅ Хорошие практики (уже реализованы):

1. ✅ **Кнопка "Назад" есть везде**
2. ✅ **Резиновая клавиатура** (`resize_keyboard=True`)
3. ✅ **Emoji для визуализации**
4. ✅ **Понятные callback_data** (`city:moscow`, `currency:RUB`)
5. ✅ **Функция add_manager_button()** для единообразия
6. ✅ **Async функции для динамических клавиатур** (города из БД)

---

## 🔧 Приоритет исправлений:

### Высокий приоритет:
1. ✅ **Добавить кнопку "⚙️ Настройки" в главное меню**
2. ✅ **Удалить дублирующую функцию `get_cities_keyboard()`**

### Средний приоритет:
3. **Убедиться что все flow обрабатывают `back_to_priority_cities`**
4. **Разделить keyboards.py на client.py и admin.py**

### Низкий приоритет:
5. **Создать универсальный роутер для общих callback**
6. **Документировать логику callback_data**

---

## 📝 Предложенные исправления

### Исправление 1: Главное меню с настройками

```python
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💵 Купить USDT")],
        [KeyboardButton(text="💸 Продать USDT")],
        [KeyboardButton(text="📄 Оплатить инвойс")],
        [KeyboardButton(text="📖 FAQ"), KeyboardButton(text="⚙️ Настройки")],
        [KeyboardButton(text="👨‍💼 Связаться с менеджером")],
    ],
    resize_keyboard=True
)
```

### Исправление 2: Удалить дубликат

```python
# УДАЛИТЬ функцию get_cities_keyboard() (строки 134-145)
# Использовать везде get_priority_cities_keyboard()
```

### Исправление 3: Опциональная кнопка менеджера

```python
def add_manager_button(keyboard: InlineKeyboardMarkup, 
                      enabled: bool = True) -> InlineKeyboardMarkup:
    """Добавляет кнопку менеджера, если enabled=True"""
    if enabled:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="👨‍💼 Связаться с менеджером", 
                               callback_data="contact_manager")
        ])
    return keyboard
```

---

**Автор:** AI Assistant  
**Дата:** 19 октября 2025  
**Версия:** 1.0

