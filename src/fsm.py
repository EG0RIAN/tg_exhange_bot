"""
Машины состояний (FSM) для Telegram бота
"""

from aiogram.fsm.state import State, StatesGroup


# ============================================================================
# FSM для ПОКУПКИ USDT (клиент покупает крипту за наличные)
# ============================================================================
class BuyUSDTStates(StatesGroup):
    """Состояния для покупки USDT клиентом"""
    enter_amount = State()         # Ввод суммы
    choose_city = State()          # Выбор города
    confirm_rate = State()         # Подтверждение курса
    choose_currency = State()      # Выбор валюты (USD/RUB и т.п.)
    enter_username = State()       # Ввод username
    confirm = State()              # Подтверждение заявки


# ============================================================================
# FSM для ПРОДАЖИ USDT (клиент продает крипту за наличные)
# ============================================================================
class SellUSDTStates(StatesGroup):
    """Состояния для продажи USDT клиентом"""
    enter_amount = State()         # Ввод суммы
    choose_city = State()          # Выбор города
    confirm_rate = State()         # Подтверждение курса
    choose_currency = State()      # Выбор валюты для выдачи наличных
    enter_username = State()       # Ввод username
    confirm = State()              # Подтверждение заявки


# ============================================================================
# FSM для ОПЛАТЫ ИНВОЙСА
# ============================================================================
class PayInvoiceStates(StatesGroup):
    """Состояния для оплаты инвойса"""
    choose_purpose = State()       # Выбор цели инвойса
    choose_payment_method = State() # Выбор способа оплаты (наличные/USDT)
    enter_amount = State()         # Ввод суммы
    choose_currency = State()      # Выбор валюты (если наличные)
    choose_city = State()          # Выбор города (если наличные)
    attach_invoice = State()       # Прикрепление файла инвойса
    enter_username = State()       # Ввод username
    confirm = State()              # Подтверждение заявки


# ============================================================================
# LEGACY FSM (для совместимости со старым кодом)
# ============================================================================
class RequestFSM(StatesGroup):
    """Устаревший FSM - оставлен для совместимости"""
    ChooseCity = State()
    ChoosePair = State()
    ChooseAction = State()
    EnterAmount = State()
    SelectPayout = State()  # Добавлено для совместимости
    EnterContact = State()
    ContactInfo = State()  # Добавлено для совместимости
    Confirm = State()
