"""
ExamGuard Pro - Database Configuration
SQLAlchemy async database setup with Supabase PostgreSQL
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import DATABASE_URL

# Detect backend
_is_sqlite = DATABASE_URL.startswith("sqlite")

# Create async engine with appropriate settings
if _is_sqlite:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
    )
else:
    # PostgreSQL (Supabase) - use connection pool settings
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,  # Recycle connections every 30 min
        pool_pre_ping=True,  # Verify connections before using
        connect_args={"statement_cache_size": 0} # Required for Supabase pgbouncer
    )

# Create async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Base class for models
class Base(DeclarativeBase):
    pass


async def init_db():
    """Initialize database tables"""
    # Import models to register them with Base
    from models import session, event, analysis, research, student
    
    # Import auth models for User and RefreshToken tables
    from auth import models as auth_models
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("Database initialized (including auth tables)")


async def get_db():
    """Dependency to get database session"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
