from asyncio import current_task

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_scoped_session,
)
# from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base, sessionmaker

from app.settings import get_settings

settings = get_settings()

Base = declarative_base()
print(settings.POSTGRES_CONN_STRING)
engine = create_async_engine(url=settings.POSTGRES_CONN_STRING)


session_factory = async_scoped_session(
    sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=AsyncSession),
    scopefunc=current_task,
)
