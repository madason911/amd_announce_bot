import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from aiogram import Bot

from database import Database

logger = logging.getLogger(__name__)

# Московский часовой пояс
MOSCOW_TZ = ZoneInfo("Europe/Moscow")


class ReminderScheduler:
    def __init__(self, bot: Bot, db: Database):
        self.bot = bot
        self.db = db
        self.scheduler = AsyncIOScheduler()

    def start(self):
        self.scheduler.start()
        logger.info("Планировщик напоминаний запущен")

    def stop(self):
        self.scheduler.shutdown()
        logger.info("Планировщик напоминаний остановлен")

    async def send_reminder(self, event_id: int, reminder_type: str):
        logger.info(f"Запуск отправки напоминания типа {reminder_type} для мероприятия {event_id}")
        try:
            event = await self.db.get_event(event_id)
            if not event:
                logger.warning(f"Мероприятие {event_id} не найдено")
                return

            participants = await self.db.get_participants_by_event(event_id)
            logger.info(f"Найдено {len(participants)} участников для мероприятия {event_id}")

            if not participants:
                logger.info(f"Нет участников для отправки напоминаний по мероприятию {event_id}")
                return

            if reminder_type == "24h":
                message_text = (
                    f"🔔 Напоминание: завтра состоится встреча на тему: "
                    f'<b>{event.title}</b> в <b>{event.date_time.strftime("%H:%M")}</b>. Ждём вас!'
                )
            elif reminder_type == "3h":
                message_text = (
                    f'🔔 Напоминаем: через 3 часа начнётся встреча на тему: <b>{event.title}</b> '
                    f"по адресу <b>{event.address}</b>. До встречи!"
                )
            else:
                logger.warning(f"Неизвестный тип напоминания: {reminder_type}")
                return

            sent_count = 0
            failed_count = 0

            for participant in participants:
                try:
                    await self.bot.send_message(
                        chat_id=participant.user_id,
                        text=message_text,
                        parse_mode="HTML"
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(
                        f"Не удалось отправить напоминание пользователю {participant.user_id}: {e}"
                    )
                    failed_count += 1

            logger.info(
                f"Отправлено напоминаний: {sent_count}, не удалось отправить: {failed_count}"
            )

        except Exception as e:
            logger.error(f"Ошибка при отправке напоминаний: {e}")

    def schedule_reminders(self, event_id: int, event_datetime: datetime):
        # Убеждаемся, что event_datetime имеет часовой пояс
        if event_datetime.tzinfo is None:
            event_datetime = event_datetime.replace(tzinfo=MOSCOW_TZ)

        reminder_24h = event_datetime - timedelta(hours=24)
        reminder_3h = event_datetime - timedelta(hours=3)

        # Получаем текущее московское время
        now = datetime.now(MOSCOW_TZ)

        if reminder_24h > now:
            self.scheduler.add_job(
                self.send_reminder,
                trigger=DateTrigger(run_date=reminder_24h),
                args=[event_id, "24h"],
                id=f"reminder_24h_{event_id}",
                replace_existing=True
            )
            logger.info(f"Запланировано напоминание за 24 часа для мероприятия {event_id}")

        if reminder_3h > now:
            self.scheduler.add_job(
                self.send_reminder,
                trigger=DateTrigger(run_date=reminder_3h),
                args=[event_id, "3h"],
                id=f"reminder_3h_{event_id}",
                replace_existing=True
            )
            logger.info(f"Запланировано напоминание за 3 часа для мероприятия {event_id}")

    async def reschedule_all_reminders(self):
        try:
            events = await self.db.get_upcoming_events()
            logger.info(f"Перепланирование напоминаний для {len(events)} мероприятий")

            for event in events:
                self.schedule_reminders(event.id, event.date_time)

        except Exception as e:
            logger.error(f"Ошибка при перепланировании напоминаний: {e}")
