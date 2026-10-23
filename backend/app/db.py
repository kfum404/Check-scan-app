from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import settings


class Base(DeclarativeBase):
    pass


_engine_kwargs: dict = {}
if settings.DATABASE_URL.startswith("sqlite"):
    # in-memory SQLite иначе теряет таблицы между сессиями (тесты)
    _engine_kwargs = {"connect_args": {"check_same_thread": False},
                      "poolclass": StaticPool}

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Создаёт таблицы при старте (для MVP без Alembic; миграции — след. этап)."""
    from . import models  # noqa: F401 — регистрация моделей

    Base.metadata.create_all(bind=engine)
