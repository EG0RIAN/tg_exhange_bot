"""
Машины состояний (FSM) для Telegram бота
"""

from aiogram.fsm.state import State, StatesGroup


# ============================================================================
# FSM для ПОКУПКИ USDT (клиент покупает крипту за наличные)
# ============================================================================
class BuyUSDTStates(StatesGroup):
    """Состояния для покупки USDT клиентом"""
    choose_city = State()          # Выбор города
    choose_currency = State()      # Выбор валюты (USD/RUB и т.п.)
    enter_amount = State()         # Ввод суммы
    enter_username = State()       # Ввод username
    confirm = State()              # Подтверждение заявки


# ============================================================================
# FSM для ПРОДАЖИ USDT (клиент продает крипту за наличные)
# ============================================================================
class SellUSDTStates(StatesGroup):
    """Состояния для продажи USDT клиентом"""
    choose_city = State()          # Выбор города
    choose_currency = State()      # Выбор валюты для выдачи наличных
    enter_amount = State()         # Ввод суммы
    enter_username = State()       # Ввод username
    confirm = State()              # Подтверждение заявки


# ============================================================================
# FSM для ОПЛАТЫ ИНВОЙСА
# ============================================================================
class PayInvoiceStates(StatesGroup):
    """Состояния для оплаты инвойса"""
    choose_purpose = State()       # Выбор цели инвойса
    choose_payment_method = State() # Выбор способа оплаты (наличные/USDT)
    choose_city = State()          # Выбор города (если наличные)
    enter_amount = State()         # Ввод суммы
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
