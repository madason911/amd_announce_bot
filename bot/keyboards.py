from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def get_event_keyboard(event_id: int, reminder_count: int = 0) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"🔔 Напомнить ({reminder_count})",
                callback_data=f"event:{event_id}:remind"
            )
        ]
    ])
    return keyboard


def get_chat_selection_keyboard(chats: dict) -> ReplyKeyboardMarkup:
    buttons = []
    for chat_name in chats.keys():
        buttons.append([KeyboardButton(text=chat_name)])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
