from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from .lib import env_loader

# defining engine url

# creating an async engine
engine = create_async_engine(env_loader.DB_URI, echo=False, future=True)

# creating a async session local class
SessionLocal = async_sessionmaker(
    autoflush=False, autocommit=False, bind=engine, class_=AsyncSession
)


# creating a dependency function for querying
async def get_db() -> AsyncIterator[AsyncSession]:
    """
    Dependency function for creating new database session
    """
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
