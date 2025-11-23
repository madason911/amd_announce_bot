from datetime import datetime
from typing import Optional, List
from sqlalchemy import BigInteger, String, DateTime, ForeignKey, select, delete
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine, AsyncSession


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_number: Mapped[int] = mapped_column()
    title: Mapped[str] = mapped_column(String(255))
    date_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    address: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(String(2000))
    message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    participants: Mapped[List["Participant"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan"
    )


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fullname: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20))  # going, maybe, not_going
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    event: Mapped["Event"] = relationship(back_populates="participants")


class Database:
    def __init__(self, db_url: str = "sqlite+aiosqlite:///./bot.db"):
        self.engine = create_async_engine(db_url, echo=False)
        self.session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def init_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def get_session(self) -> AsyncSession:
        async with self.session_maker() as session:
            return session

    async def create_event(
        self,
        event_number: int,
        title: str,
        date_time: datetime,
        end_time: Optional[datetime],
        address: str,
        description: str,
        message_id: Optional[int] = None,
        chat_id: Optional[int] = None
    ) -> Event:
        async with self.session_maker() as session:
            event = Event(
                event_number=event_number,
                title=title,
                date_time=date_time,
                end_time=end_time,
                address=address,
                description=description,
                message_id=message_id,
                chat_id=chat_id
            )
            session.add(event)
            await session.commit()
            await session.refresh(event)
            return event

    async def get_event(self, event_id: int) -> Optional[Event]:
        async with self.session_maker() as session:
            result = await session.execute(
                select(Event).where(Event.id == event_id)
            )
            return result.scalar_one_or_none()

    async def get_all_events(self) -> List[Event]:
        async with self.session_maker() as session:
            result = await session.execute(select(Event))
            return list(result.scalars().all())

    async def get_upcoming_events(self) -> List[Event]:
        async with self.session_maker() as session:
            result = await session.execute(
                select(Event).where(Event.date_time > datetime.now())
            )
            return list(result.scalars().all())

    async def delete_old_events(self):
        async with self.session_maker() as session:
            await session.execute(
                delete(Event).where(Event.date_time < datetime.now())
            )
            await session.commit()

    async def add_participant(
        self,
        event_id: int,
        user_id: int,
        username: Optional[str],
        fullname: str,
        status: str
    ) -> Participant:
        async with self.session_maker() as session:
            result = await session.execute(
                select(Participant).where(
                    Participant.event_id == event_id,
                    Participant.user_id == user_id
                )
            )
            participant = result.scalar_one_or_none()

            if participant:
                participant.status = status
                participant.timestamp = datetime.now()
            else:
                participant = Participant(
                    event_id=event_id,
                    user_id=user_id,
                    username=username,
                    fullname=fullname,
                    status=status
                )
                session.add(participant)

            await session.commit()
            await session.refresh(participant)
            return participant

    async def get_participants_by_event(self, event_id: int) -> List[Participant]:
        async with self.session_maker() as session:
            result = await session.execute(
                select(Participant).where(Participant.event_id == event_id)
            )
            return list(result.scalars().all())

    async def get_participants_by_status(
        self,
        event_id: int,
        status: str
    ) -> List[Participant]:
        async with self.session_maker() as session:
            result = await session.execute(
                select(Participant).where(
                    Participant.event_id == event_id,
                    Participant.status == status
                )
            )
            return list(result.scalars().all())
