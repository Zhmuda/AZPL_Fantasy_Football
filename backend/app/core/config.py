from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    ADMIN_PASSWORD: str

    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:5173"

    SOFASCORE_TOURNAMENT_ID: int = 709
    SOFASCORE_REQUEST_DELAY: float = 2.0

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()
