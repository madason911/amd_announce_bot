from aiogram.fsm.state import State, StatesGroup


class EventCreation(StatesGroup):
    waiting_for_chat_selection = State()
    waiting_for_title = State()
    waiting_for_datetime = State()
