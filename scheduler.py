import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from aiogram import Bot

from database import Database

logger = logging.getLogger(__name__)


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
        try:
            event = await self.db.get_event(event_id)
            if not event:
                logger.warning(f"Мероприятие {event_id} не найдено")
                return

            statuses = ["going", "maybe"]
            participants = []

            for status in statuses:
                parts = await self.db.get_participants_by_status(event_id, status)
                participants.extend(parts)

            if reminder_type == "24h":
                message_text = (
                    f"🔔 Напоминание: завтра состоится мероприятие в дискуссионном клубе АМД на тему:"
                    f'<b>{event.title}</b> в <b>{event.date_time.strftime("%H:%M")}</b>. Ждём вас!'
                )
            elif reminder_type == "3h":
                message_text = (
                    f'🔔 Напоминаем: через 3 часа начнётся встреча на тему:<b>{event.title}</b> '
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
        reminder_24h = event_datetime - timedelta(hours=24)
        reminder_3h = event_datetime - timedelta(hours=3)

        now = datetime.now()

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
