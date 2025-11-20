from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import config
from database import Database

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


@router.message(Command("list"))
async def cmd_list(message: Message, db: Database):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав для просмотра участников.")
        return

    events = await db.get_upcoming_events()

    if not events:
        await message.answer("Нет предстоящих мероприятий.")
        return

    for event in events:
        going = await db.get_participants_by_status(event.id, "going")
        maybe = await db.get_participants_by_status(event.id, "maybe")

        going_list = [
            f"@{p.username}" if p.username else p.fullname
            for p in going
        ]
        maybe_list = [
            f"@{p.username}" if p.username else p.fullname
            for p in maybe
        ]

        response = f"📊 Мероприятие: {event.title}\n"
        response += f"📅 {event.date_time.strftime('%d.%m.%Y %H:%M')}\n\n"

        response += f"👍 Я приду ({len(going)}):\n"
        if going_list:
            response += ", ".join(going_list) + "\n\n"
        else:
            response += "Пока никто не записался\n\n"

        response += f"🤔 Возможно ({len(maybe)}):\n"
        if maybe_list:
            response += ", ".join(maybe_list)
        else:
            response += "Пока никто не записался"

        await message.answer(response)


@router.message(Command("clear_events"))
async def cmd_clear_events(message: Message, db: Database):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав для удаления мероприятий.")
        return

    await db.delete_old_events()
    await message.answer("✅ Старые мероприятия удалены.")
