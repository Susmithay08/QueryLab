from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, DateTime, Text, Integer, Float, Boolean
from datetime import datetime, timezone
import uuid
from app.core.config import settings


class Base(DeclarativeBase):
    pass


class QueryHistory(Base):
    __tablename__ = "query_history"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    database_name = Column(String, nullable=False)
    sql = Column(Text, nullable=False)
    row_count = Column(Integer, nullable=True)
    exec_ms = Column(Float, nullable=True)
    had_error = Column(Boolean, default=False)
    error_msg = Column(Text, nullable=True)
    ai_explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SharedQuery(Base):
    __tablename__ = "shared_queries"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String, unique=True, nullable=False)   # short 8-char ID for URL
    database_name = Column(String, nullable=False)
    sql = Column(Text, nullable=False)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
