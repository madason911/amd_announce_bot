import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []
    COMMUNITY_CHAT_ID = int(os.getenv("COMMUNITY_CHAT_ID", "0"))
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")

    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is not set")
        if not cls.ADMIN_IDS:
            raise ValueError("ADMIN_IDS is not set")
        if not cls.COMMUNITY_CHAT_ID:
            raise ValueError("COMMUNITY_CHAT_ID is not set")


config = Config()
