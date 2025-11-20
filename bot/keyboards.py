from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_event_keyboard(event_id: int, going_count: int = 0, maybe_count: int = 0, not_going_count: int = 0) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"👍 Я приду ({going_count})",
                callback_data=f"event:{event_id}:going"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"🤔 Возможно приду ({maybe_count})",
                callback_data=f"event:{event_id}:maybe"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"👎 Не приду ({not_going_count})",
                callback_data=f"event:{event_id}:not_going"
            )
        ]
    ])
    return keyboard
