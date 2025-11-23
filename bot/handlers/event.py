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


def format_date_russian(dt: datetime) -> str:
    """Форматирует дату в формате '12 ноября(ср)'"""
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    weekdays = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]

    day = dt.day
    month = months[dt.month - 1]
    weekday = weekdays[dt.weekday()]

    return f"{day} {month}({weekday})"


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
        "Введите номер мероприятия (например, 15):"
    )
    await state.set_state(EventCreation.waiting_for_event_number)


@router.message(EventCreation.waiting_for_event_number)
async def process_event_number(message: Message, state: FSMContext):
    try:
        event_number = int(message.text)
        await state.update_data(event_number=event_number)
        await message.answer("Введите название/тему мероприятия:")
        await state.set_state(EventCreation.waiting_for_title)
    except ValueError:
        await message.answer("Пожалуйста, введите число (например, 15):")


@router.message(EventCreation.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите дату и время начала (формат DD.MM HH:MM):")
    await state.set_state(EventCreation.waiting_for_datetime)


@router.message(EventCreation.waiting_for_datetime)
async def process_datetime(message: Message, state: FSMContext):
    try:
        current_year = datetime.now().year
        event_datetime = datetime.strptime(f"{message.text} {current_year}", "%d.%m %H:%M %Y")

        if event_datetime < datetime.now():
            event_datetime = event_datetime.replace(year=current_year + 1)

        await state.update_data(date_time=event_datetime)
        await message.answer("Введите время окончания (формат HH:MM):")
        await state.set_state(EventCreation.waiting_for_end_time)
    except ValueError:
        await message.answer("Неверный формат даты. Используйте формат DD.MM HH:MM (например, 15.12 18:00):")


@router.message(EventCreation.waiting_for_end_time)
async def process_end_time(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        start_datetime = data["date_time"]

        end_time = datetime.strptime(message.text, "%H:%M").time()
        end_datetime = datetime.combine(start_datetime.date(), end_time)

        if end_datetime <= start_datetime:
            await message.answer("Время окончания должно быть позже времени начала. Попробуйте снова:")
            return

        await state.update_data(end_time=end_datetime)
        await message.answer("Введите адрес:")
        await state.set_state(EventCreation.waiting_for_address)
    except ValueError:
        await message.answer("Неверный формат времени. Используйте формат HH:MM (например, 22:00):")


@router.message(EventCreation.waiting_for_address)
async def process_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("Введите описание:")
    await state.set_state(EventCreation.waiting_for_description)


@router.message(EventCreation.waiting_for_description)
async def process_description(message: Message, state: FSMContext, db: Database, scheduler):
    data = await state.get_data()

    event = await db.create_event(
        event_number=data["event_number"],
        title=data["title"],
        date_time=data["date_time"],
        end_time=data["end_time"],
        address=data["address"],
        description=message.text
    )

    date_formatted = format_date_russian(data['date_time'])
    time_range = f"{data['date_time'].strftime('%H:%M')} - {data['end_time'].strftime('%H:%M')}"

    event_text = (
        f"<b>Дискуссии в АМД #{data['event_number']}</b>\n\n"
        f"<b>Тема: «{data['title']}»</b>\n\n"
        f"📝 {message.text}\n\n"
        f"📅 <b>Дата: {date_formatted}</b>\n"
        f"🕒 <b>Время: {time_range}</b>\n"
        f"📍 <b>Адрес: {data['address']}</b>\n\n"
        f"Формат и правила, можно прочитать в закрепеленном сообщении! Ждем вас!"
    )

    try:
        sent_message = await message.bot.send_message(
            chat_id=config.COMMUNITY_CHAT_ID,
            text=event_text,
            parse_mode="HTML",
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
