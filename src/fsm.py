from aiogram.fsm.state import StatesGroup, State

class RequestFSM(StatesGroup):
    ChoosePair = State()
    EnterAmount = State()
    SelectPayout = State()
    ContactInfo = State()
    Confirm = State() 