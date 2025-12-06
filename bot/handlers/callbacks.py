from aiogram import Router, F
from aiogram.types import CallbackQuery

from database import Database
from bot.keyboards import get_event_keyboard

router = Router()


@router.callback_query(F.data.startswith("event:"))
async def handle_event_response(callback: CallbackQuery, db: Database):
    try:
        _, event_id_str, action = callback.data.split(":")
        event_id = int(event_id_str)

        if action != "remind":
            await callback.answer("Неизвестное действие", show_alert=True)
            return

        user = callback.from_user
        fullname = user.full_name
        username = user.username

        await db.add_participant(
            event_id=event_id,
            user_id=user.id,
            username=username,
            fullname=fullname
        )

        participants = await db.get_participants_by_event(event_id)

        new_keyboard = get_event_keyboard(
            event_id,
            reminder_count=len(participants)
        )

        await callback.message.edit_reply_markup(reply_markup=new_keyboard)
        await callback.answer("✅ Напоминание активировано!")

        try:
            await callback.bot.send_message(
                chat_id=user.id,
                text="✅ Отлично! Бот напомнит вам о мероприятии за 24 часа и за 3 часа до начала встречи."
            )
        except Exception:
            pass

    except Exception as e:
        await callback.answer(f"Произошла ошибка: {str(e)}", show_alert=True)
