from aiogram.fsm.state import StatesGroup, State

class RequestFSM(StatesGroup):
    ChooseCity = State()     # Новый шаг - выбор города
    ChoosePair = State()
    EnterAmount = State()
    SelectPayout = State()
    ContactInfo = State()
    Confirm = State() 