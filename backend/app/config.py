import os
from dataclasses import dataclass


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str
    secret_key: str
    admin_password: str
    postgres_password: str
    cors_origins: str
    backend_url: str
    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    log_level: str
    environment: str
    db_pool_size: int
    db_max_overflow: int
    rate_limit_per_minute: int
    rate_limit_per_hour: int


settings = Settings(
    database_url=_required_env("DATABASE_URL"),
    secret_key=_required_env("SECRET_KEY"),
    admin_password=_required_env("ADMIN_PASSWORD"),
    postgres_password=_required_env("POSTGRES_PASSWORD"),
    cors_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000"),
    backend_url=os.getenv("BACKEND_URL", "http://localhost:8000"),
    algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
    access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
    refresh_token_expire_days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")),
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    environment=os.getenv("ENVIRONMENT", "development"),
    db_pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    db_max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
    rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "30")),
    rate_limit_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "500")),
)
