from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📖 FAQ"), KeyboardButton(text="💱 Курсы")],
        [KeyboardButton(text="✉️ Оставить заявку")],
        [KeyboardButton(text="👨‍💼 Перейти к менеджеру")],
        [KeyboardButton(text="⚙️ Настройки")],
    ],
    resize_keyboard=True
)

def add_back_button(keyboard: InlineKeyboardMarkup) -> InlineKeyboardMarkup:
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back")])
    return keyboard

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