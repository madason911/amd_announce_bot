from datetime import datetime
from zoneinfo import ZoneInfo
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.states import EventCreation
from bot.keyboards import get_event_keyboard, get_chat_selection_keyboard
from config import config
from database import Database

# Московский часовой пояс
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

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
        "Выберите чат для публикации:",
        reply_markup=get_chat_selection_keyboard(config.COMMUNITY_CHATS)
    )
    await state.set_state(EventCreation.waiting_for_chat_selection)


@router.message(EventCreation.waiting_for_chat_selection)
async def process_chat_selection(message: Message, state: FSMContext):
    chat_name = message.text

    if chat_name not in config.COMMUNITY_CHATS:
        await message.answer(
            "❌ Неверный выбор чата. Пожалуйста, выберите из списка:",
            reply_markup=get_chat_selection_keyboard(config.COMMUNITY_CHATS)
        )
        return

    chat_id = config.COMMUNITY_CHATS[chat_name]
    await state.update_data(chat_name=chat_name, chat_id=chat_id)

    from aiogram.types import ReplyKeyboardRemove
    await message.answer(
        "Введите название/тему мероприятия:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(EventCreation.waiting_for_title)


@router.message(EventCreation.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите дату и время начала (формат DD.MM HH:MM):")
    await state.set_state(EventCreation.waiting_for_datetime)


@router.message(EventCreation.waiting_for_datetime)
async def process_datetime(message: Message, state: FSMContext, db: Database, scheduler):
    try:
        # Получаем текущее московское время
        moscow_now = datetime.now(MOSCOW_TZ)
        current_year = moscow_now.year

        # Парсим дату без часового пояса
        event_datetime_naive = datetime.strptime(f"{message.text} {current_year}", "%d.%m %H:%M %Y")

        # Добавляем московский часовой пояс
        event_datetime = event_datetime_naive.replace(tzinfo=MOSCOW_TZ)

        # Если дата в прошлом, берем следующий год
        if event_datetime < moscow_now:
            event_datetime = event_datetime.replace(year=current_year + 1)

        data = await state.get_data()

        # Автоматически генерируем номер мероприятия на основе количества существующих
        events = await db.get_all_events()
        event_number = len(events) + 1

        event = await db.create_event(
            event_number=event_number,
            title=data["title"],
            date_time=event_datetime,
            end_time=None,
            address="",
            description=""
        )

        event_text = (
            f"Если вы хотите чтобы вам напомнили про мероприятие, то нажмите на кнопку ниже и активируйте бот"
        )

        try:
            sent_message = await message.bot.send_message(
                chat_id=data["chat_id"],
                text=event_text,
                parse_mode="HTML",
                reply_markup=get_event_keyboard(event.id)
            )

            async with db.session_maker() as session:
                db_event = await session.get(event.__class__, event.id)
                db_event.message_id = sent_message.message_id
                db_event.chat_id = data["chat_id"]
                await session.commit()

            scheduler.schedule_reminders(event.id, event.date_time)

            await message.answer(
                f"✅ Мероприятие успешно создано!\n\n"
                f"📢 Анонс опубликован в чате: {data['chat_name']}\n"
                f"🔔 Напоминания запланированы:\n"
                f"   • За 24 часа до начала\n"
                f"   • За 3 часа до начала"
            )
        except Exception as e:
            await message.answer(f"❌ Ошибка при публикации: {str(e)}")

        await state.clear()
    except ValueError:
        await message.answer("Неверный формат даты. Используйте формат DD.MM HH:MM (например, 15.12 18:00):")
