from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Все настройки через переменные окружения (см. .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://checkscan:checkscan@localhost:5432/checkscan"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_MINUTES: int = 60 * 24 * 7  # неделя

    UPLOAD_DIR: str = "uploads"          # куда складываем фото чеков
    TESSERACT_CMD: str | None = None     # путь к tesseract.exe (Windows-разработка)
    TESSERACT_LANG: str = "rus+eng"
    TESSERACT_PSM: int = 6

    CORS_ORIGINS: str = "*"              # на проде: "https://...,exp://..."


settings = Settings()
