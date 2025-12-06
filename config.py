import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")

    # Чаты сообществ в формате "Название:ID,Название:ID"
    COMMUNITY_CHATS = {}
    _chats_env = os.getenv("COMMUNITY_CHATS", "")
    if _chats_env:
        for chat_pair in _chats_env.split(","):
            if ":" in chat_pair:
                name, chat_id = chat_pair.strip().split(":", 1)
                COMMUNITY_CHATS[name.strip()] = int(chat_id.strip())

    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is not set")
        if not cls.ADMIN_IDS:
            raise ValueError("ADMIN_IDS is not set")
        if not cls.COMMUNITY_CHATS:
            raise ValueError("COMMUNITY_CHATS is not set")


config = Config()
