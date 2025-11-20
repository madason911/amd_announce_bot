import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import config
from database import Database
from scheduler import ReminderScheduler
from bot.handlers import event, callbacks, admin

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot, db: Database, scheduler: ReminderScheduler):
    logger.info("Инициализация базы данных...")
    await db.init_db()

    logger.info("Запуск планировщика напоминаний...")
    scheduler.start()

    logger.info("Перепланирование существующих напоминаний...")
    await scheduler.reschedule_all_reminders()

    logger.info("Бот запущен!")


async def on_shutdown(scheduler: ReminderScheduler):
    logger.info("Остановка планировщика...")
    scheduler.stop()
    logger.info("Бот остановлен!")


async def main():
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        logger.error("Создайте файл .env и заполните необходимые переменные")
        return

    db = Database(config.DATABASE_URL)

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    scheduler = ReminderScheduler(bot, db)

    dp.include_router(event.router)
    dp.include_router(callbacks.router)
    dp.include_router(admin.router)

    await on_startup(bot, db, scheduler)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(), db=db, scheduler=scheduler)
    finally:
        await on_shutdown(scheduler)
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
