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
        participants = await db.get_participants_by_event(event.id)

        participant_list = [
            f"@{p.username}" if p.username else p.fullname
            for p in participants
        ]

        response = f"📊 <b>Мероприятие:</b> {event.title}\n"
        response += f"📅 <b>{event.date_time.strftime('%d.%m.%Y %H:%M')}</b>\n\n"

        response += f"🔔 <b>Включили напоминание ({len(participants)}):</b>\n"
        if participant_list:
            response += ", ".join(participant_list)
        else:
            response += "Пока никто не активировал напоминания"

        await message.answer(response, parse_mode="HTML")


@router.message(Command("clear_events"))
async def cmd_clear_events(message: Message, db: Database):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав для удаления мероприятий.")
        return

    await db.delete_old_events()
    await message.answer("✅ Старые мероприятия удалены.")
