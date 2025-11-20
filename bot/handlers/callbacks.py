from aiogram import Router, F
from aiogram.types import CallbackQuery

from database import Database
from bot.keyboards import get_event_keyboard

router = Router()


STATUS_MESSAGES = {
    "going": "✅ Вы отметили: Я приду",
    "maybe": "✅ Вы отметили: Возможно приду",
    "not_going": "✅ Вы отметили: Не приду"
}

STATUS_MESSAGES_DETAILED = {
    "going": "✅ Ваш выбор сохранен!\n\n👍 Я приду\n\nВы получите напоминания за 24 часа и за 3 часа до мероприятия.",
    "maybe": "✅ Ваш выбор сохранен!\n\n🤔 Возможно приду\n\nВы получите напоминания за 24 часа и за 3 часа до мероприятия.",
    "not_going": "✅ Ваш выбор сохранен!\n\n👎 Не приду\n\nВы не будете получать напоминания об этом мероприятии."
}


@router.callback_query(F.data.startswith("event:"))
async def handle_event_response(callback: CallbackQuery, db: Database):
    try:
        _, event_id_str, status = callback.data.split(":")
        event_id = int(event_id_str)

        user = callback.from_user
        fullname = user.full_name
        username = user.username

        await db.add_participant(
            event_id=event_id,
            user_id=user.id,
            username=username,
            fullname=fullname,
            status=status
        )

        going = await db.get_participants_by_status(event_id, "going")
        maybe = await db.get_participants_by_status(event_id, "maybe")
        not_going = await db.get_participants_by_status(event_id, "not_going")

        new_keyboard = get_event_keyboard(
            event_id,
            going_count=len(going),
            maybe_count=len(maybe),
            not_going_count=len(not_going)
        )

        await callback.message.edit_reply_markup(reply_markup=new_keyboard)
        await callback.answer(STATUS_MESSAGES.get(status, "Ваш ответ принят"))

        try:
            await callback.bot.send_message(
                chat_id=user.id,
                text=STATUS_MESSAGES_DETAILED.get(status, "Ваш выбор сохранен!")
            )
        except Exception:
            pass

    except Exception as e:
        await callback.answer(f"Произошла ошибка: {str(e)}", show_alert=True)
