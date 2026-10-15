from typing import AsyncGenerator, Any
from backend.app.core.config import settings

Base: Any = None
engine = None
AsyncSessionLocal = None

try:
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from sqlalchemy.orm import declarative_base

    Base = declarative_base()
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        future=True,
        pool_pre_ping=True
    )
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
except Exception as e:
    # Graceful warning if SQLAlchemy / asyncpg is not yet installed in local dev
    print(f"[Database Notice] Database ORM initialized in decoupled mode: {e}")

async def get_db() -> AsyncGenerator[Any, None]:
    """
    Dependency generator for injecting SQLAlchemy AsyncSession into API route handlers.
    """
    if AsyncSessionLocal is None:
        yield None
        return

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
