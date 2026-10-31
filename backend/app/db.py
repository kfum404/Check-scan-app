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
    _migrate_add_column("users", "push_token", "VARCHAR(255)")


def _migrate_add_column(table: str, column: str, ddl: str) -> None:
    """Добавляет колонку, если её ещё нет (упрощённая миграция без Alembic)."""
    from sqlalchemy import text

    with engine.connect() as conn:
        if engine.dialect.name == "sqlite":
            cols = [r[1] for r in conn.execute(text(f"PRAGMA table_info({table})"))]
            missing = column not in cols
        else:  # postgresql и др. — information_schema
            missing = conn.execute(
                text("SELECT 1 FROM information_schema.columns "
                     "WHERE table_name = :t AND column_name = :c"),
                {"t": table, "c": column},
            ).first() is None
        if missing:
            conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN {column} {ddl}'))
            conn.commit()
