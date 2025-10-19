from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ============================================================================
# НОВОЕ ГЛАВНОЕ МЕНЮ (3 основных действия)
# ============================================================================
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💵 Купить USDT")],
        [KeyboardButton(text="💸 Продать USDT")],
        [KeyboardButton(text="📄 Оплатить инвойс")],
        [KeyboardButton(text="📖 FAQ")],
        [KeyboardButton(text="👨‍💼 Связаться с менеджером")],
    ],
    resize_keyboard=True
)

def add_back_button(keyboard: InlineKeyboardMarkup) -> InlineKeyboardMarkup:
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back")])
    return keyboard

def add_manager_button(keyboard: InlineKeyboardMarkup) -> InlineKeyboardMarkup:
    """Добавляет кнопку 'Связаться с менеджером' на каждом этапе"""
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="👨‍💼 Связаться с менеджером", callback_data="contact_manager")
    ])
    return keyboard

# ============================================================================
# КЛАВИАТУРЫ ДЛЯ НОВОГО FLOW
# ============================================================================

def get_countries_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора страны"""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Россия", callback_data="country:russia")],
            [InlineKeyboardButton(text="🇰🇿 Казахстан", callback_data="country:kazakhstan")],
            [InlineKeyboardButton(text="🇺🇿 Узбекистан", callback_data="country:uzbekistan")],
            [InlineKeyboardButton(text="🇦🇿 Азербайджан", callback_data="country:azerbaijan")],
            [InlineKeyboardButton(text="🇬🇪 Грузия", callback_data="country:georgia")],
            [InlineKeyboardButton(text="🇹🇷 Турция", callback_data="country:turkey")],
            [InlineKeyboardButton(text="🇦🇪 ОАЭ", callback_data="country:uae")],
        ]
    )
    return add_manager_button(kb)

async def get_priority_cities_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора города с приоритетными городами + кнопка 'Остальные города'"""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏛 Москва", callback_data="city:moscow")],
            [InlineKeyboardButton(text="🌉 Санкт-Петербург", callback_data="city:spb")],
            [InlineKeyboardButton(text="🌴 Краснодар", callback_data="city:krasnodar")],
            [InlineKeyboardButton(text="🏭 Ростов-на-Дону", callback_data="city:rostov")],
            [InlineKeyboardButton(text="🌍 Остальные города", callback_data="city:other")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")],
        ]
    )
    return add_manager_button(kb)

async def get_all_cities_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура со всеми остальными городами (кроме приоритетных)"""
    from src.db import get_pg_pool
    
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        cities = await conn.fetch("""
            SELECT code, name FROM cities 
            WHERE enabled = true 
            AND code NOT IN ('moscow', 'spb', 'krasnodar', 'rostov')
            ORDER BY name
        """)
    
    buttons = []
    for city in cities:
        buttons.append([InlineKeyboardButton(
            text=city['name'], 
            callback_data=f"city:{city['code']}"
        )])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_priority_cities")])
    return add_manager_button(kb)

def get_currencies_keyboard(city_code=None) -> InlineKeyboardMarkup:
    """Клавиатура выбора валюты (только рубль)"""
    currencies = [
        ("₽ RUB (Рубль)", "RUB"),
    ]
    
    buttons = [[InlineKeyboardButton(text=name, callback_data=f"currency:{code}")] 
               for name, code in currencies]
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back")])
    return add_manager_button(kb)

def get_amount_keyboard_v2():
    """Клавиатура для ввода суммы (только кнопка назад)"""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
        ]
    )
    return add_manager_button(kb)

def get_payment_methods_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора способа оплаты (для инвойса)"""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💵 Наличные", callback_data="payment:cash")],
            [InlineKeyboardButton(text="💎 USDT", callback_data="payment:usdt")],
        ]
    )
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back")])
    return add_manager_button(kb)

def get_invoice_purposes_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора цели инвойса"""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏢 Оплата услуг", callback_data="purpose:services")],
            [InlineKeyboardButton(text="🏬 Покупка товаров", callback_data="purpose:goods")],
            [InlineKeyboardButton(text="📦 Доставка/логистика", callback_data="purpose:delivery")],
            [InlineKeyboardButton(text="💼 Прочее", callback_data="purpose:other")],
        ]
    )
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back")])
    return add_manager_button(kb)

def get_confirm_keyboard_v2():
    """Клавиатура подтверждения заявки"""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm:yes")],
            [InlineKeyboardButton(text="✏️ Изменить", callback_data="confirm:edit")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="confirm:cancel")],
        ]
    )
    return add_manager_button(kb)

def get_rate_confirm_keyboard():
    """Клавиатура подтверждения курса"""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить курс", callback_data="rate:confirm")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="rate:cancel")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")],
        ]
    )
    return add_manager_button(kb)

def get_pairs_keyboard(pairs: list[str]) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(text=pair, callback_data=f"pair:{pair}") for pair in pairs]
    rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    return add_back_button(kb)

def get_amount_keyboard():
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="100", callback_data="amount:100"),
             InlineKeyboardButton(text="250", callback_data="amount:250")],
            [InlineKeyboardButton(text="1000", callback_data="amount:1000")],
            [InlineKeyboardButton(text="📝 Своя", callback_data="amount:custom")],
        ]
    )
    return add_back_button(kb)

def get_payout_keyboard(methods: list[str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=method, callback_data=f"payout:{method}")] for method in methods]
    )
    return add_back_button(kb)

async def get_cities_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора города с приоритетными городами + кнопка 'Остальные города'"""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏛 Москва", callback_data="city:moscow")],
            [InlineKeyboardButton(text="🌉 Санкт-Петербург", callback_data="city:spb")],
            [InlineKeyboardButton(text="🌴 Краснодар", callback_data="city:krasnodar")],
            [InlineKeyboardButton(text="🏭 Ростов-на-Дону", callback_data="city:rostov")],
            [InlineKeyboardButton(text="🌍 Остальные города", callback_data="city:other")],
        ]
    )
    return kb

def get_confirm_keyboard():
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm")],
            [InlineKeyboardButton(text="🔄 Изменить", callback_data="edit")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
        ]
    )
    return add_back_button(kb)

def get_faq_categories_keyboard(categories: list[tuple]) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора категории FAQ
    categories: список кортежей (id, name)
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=f"faq_cat:{cat_id}")] for cat_id, name in categories
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="faq_back")]]
    )

def get_faq_questions_keyboard(questions: list[tuple]) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора вопроса FAQ
    questions: список кортежей (id, question)
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=question, callback_data=f"faq_q:{qid}")] for qid, question in questions
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="faq_back")]]
    )

def get_faq_answer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="faq_back")]]
    )

def get_livechat_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Отключить чат", callback_data="livechat_off")]]
    )

def get_admin_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Курсы", callback_data="admin_rates")],
            [InlineKeyboardButton(text="FAQ", callback_data="admin_faq")],
            [InlineKeyboardButton(text="Заявки", callback_data="admin_orders")],
            [InlineKeyboardButton(text="Рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="Логи", callback_data="admin_logs")],
            [InlineKeyboardButton(text="Контент", callback_data="admin_content")],
            [InlineKeyboardButton(text="🌐 Интеграции", callback_data="admin_integrations")],
        ]
    )

def get_admin_content_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Торговые пары", callback_data="admin_trading_pairs")],
            [InlineKeyboardButton(text="Способы выплаты", callback_data="admin_payout_methods")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
        ]
    )

def get_admin_integrations_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Grinex Exchange", callback_data="admin_grinex")],
            [InlineKeyboardButton(text="📊 FX Rates System", callback_data="admin_fx_system")],
            [InlineKeyboardButton(text="🌍 Курсы по городам", callback_data="admin_city_rates")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
        ]
    )

def get_trading_pairs_keyboard(pairs: list[dict]) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора торговых пар
    pairs: список словарей с данными пар
    """
    buttons = []
    for pair in pairs:
        buttons.append([InlineKeyboardButton(
            text=f"{pair['base_name']} ➡️ {pair['quote_name']}", 
            callback_data=f"rates_pair:{pair['id']}"
        )])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="rates_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_rates_back_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для возврата к главному меню"""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="rates_back")]]
    )

def get_rate_tiers_keyboard(pair_id, tiers):
    rows = []
    for tier in tiers:
        rows.append([InlineKeyboardButton(text=f"От ${tier['min_amount']:,} ➡️ {tier['rate']}", callback_data=f"admin_edit_rate:{tier['id']}")])
    rows.append([InlineKeyboardButton(text="➕ Добавить курс", callback_data=f"admin_add_rate:{pair_id}")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_trading_pairs")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_rates_list_keyboard(rates, page, total):
    rows = []
    for rate in rates:
        rows.append([InlineKeyboardButton(text=f"{rate['pair']} {rate['bid']}/{rate['ask']}", callback_data=f"admin_rate:{rate['id']}")])
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_rates_page:{page-1}"))
    if page * 10 < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_rates_page:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="➕ Добавить", callback_data="admin_rate_add"), InlineKeyboardButton(text="⏰ Импорт Rapira", callback_data="admin_rate_import")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_admin_order_status_keyboard(order_id, current_status):
    statuses = ["new", "processing", "done"]
    rows = [[InlineKeyboardButton(text=s if s != current_status else f"✅ {s}", callback_data=f"admin_order_status:{order_id}:{s}")] for s in statuses if s != current_status]
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_orders")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_admin_orders_keyboard(orders, page, total):
    rows = [[InlineKeyboardButton(text=f"#{o['id']} {o['pair']} {o['amount']} {o['status']}", callback_data=f"admin_order:{o['id']}")] for o in orders]
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_orders_page:{page-1}"))
    if page * 10 < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_orders_page:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_broadcast_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👁️ Предпросмотр", callback_data="admin_broadcast_preview")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_back")],
        ]
    )

def get_broadcast_confirm_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Разослать", callback_data="admin_broadcast_send")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_back")],
        ]
    )

def get_logs_filter_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❗ error", callback_data="admin_logs_error"),
             InlineKeyboardButton(text="⚠️ warning", callback_data="admin_logs_warning"),
             InlineKeyboardButton(text="ℹ️ info", callback_data="admin_logs_info")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
        ]
    )

def get_admin_faq_categories_keyboard(categories):
    """Создает админскую клавиатуру для управления категориями FAQ
    categories: список кортежей (id, name)
    """
    rows = [[InlineKeyboardButton(text=name, callback_data=f"admin_faq_cat:{cat_id}")] for cat_id, name in categories]
    rows.append([InlineKeyboardButton(text="➕ Добавить категорию", callback_data="admin_faq_cat_add")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_admin_faq_questions_keyboard(questions, category):
    """Создает админскую клавиатуру для управления вопросами FAQ
    questions: список кортежей (id, question)
    category: id категории
    """
    rows = [[InlineKeyboardButton(text=question, callback_data=f"admin_faq_q:{qid}")] for qid, question in questions]
    rows.append([InlineKeyboardButton(text="➕ Добавить вопрос", callback_data=f"admin_faq_q_add:{category}")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_faq"),])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_admin_faq_edit_keyboard(faq_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💾 Сохранить", callback_data=f"admin_faq_save:{faq_id}")],
            [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"admin_faq_del:{faq_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_faq")],
        ]
    ) 