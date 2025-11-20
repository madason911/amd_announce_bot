from datetime import datetime
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.states import EventCreation
from bot.keyboards import get_event_keyboard
from config import config
from database import Database

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


@router.message(Command("event"))
async def cmd_event(message: Message, state: FSMContext):
    if message.chat.type != "private":
        await message.answer(
            "⚠️ Создание мероприятий доступно только в личных сообщениях с ботом.\n"
            "Напишите мне в личку: @amd_announce_bot"
        )
        return

    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав для создания мероприятий.")
        return

    await message.answer(
        "🎯 Создание нового мероприятия\n\n"
        "Введите название мероприятия:"
    )
    await state.set_state(EventCreation.waiting_for_title)


@router.message(EventCreation.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите дату и время (формат DD.MM HH:MM):")
    await state.set_state(EventCreation.waiting_for_datetime)


@router.message(EventCreation.waiting_for_datetime)
async def process_datetime(message: Message, state: FSMContext):
    try:
        current_year = datetime.now().year
        event_datetime = datetime.strptime(f"{message.text} {current_year}", "%d.%m %H:%M %Y")

        if event_datetime < datetime.now():
            event_datetime = event_datetime.replace(year=current_year + 1)

        await state.update_data(date_time=event_datetime)
        await message.answer("Введите адрес:")
        await state.set_state(EventCreation.waiting_for_address)
    except ValueError:
        await message.answer("Неверный формат даты. Используйте формат DD.MM HH:MM (например, 15.12 18:00):")


@router.message(EventCreation.waiting_for_address)
async def process_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("Введите описание:")
    await state.set_state(EventCreation.waiting_for_description)


@router.message(EventCreation.waiting_for_description)
async def process_description(message: Message, state: FSMContext, db: Database, scheduler):
    data = await state.get_data()

    event = await db.create_event(
        title=data["title"],
        date_time=data["date_time"],
        address=data["address"],
        description=message.text
    )

    event_text = (f"{event.description}")

    try:
        sent_message = await message.bot.send_message(
            chat_id=config.COMMUNITY_CHAT_ID,
            text=event_text,
            reply_markup=get_event_keyboard(event.id)
        )

        async with db.session_maker() as session:
            db_event = await session.get(event.__class__, event.id)
            db_event.message_id = sent_message.message_id
            db_event.chat_id = config.COMMUNITY_CHAT_ID
            await session.commit()

        scheduler.schedule_reminders(event.id, event.date_time)

        await message.answer(
            "✅ Мероприятие успешно создано!\n\n"
            "📢 Анонс опубликован в чате сообщества\n"
            "🔔 Напоминания запланированы:\n"
            "   • За 24 часа до начала\n"
            "   • За 3 часа до начала"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при публикации: {str(e)}")

    await state.clear()
