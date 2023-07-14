from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    S3_ACCESS_KEY: str
    S3_ENDPOINT: str
    S3_SECRET_KEY: str
    S3_BUCKET_NAME: str

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str

    SRC_PREFIX: str = "/fm2/a/"

    PER_PAGE: int = 50
    DEBUG: bool = False

    @property
    def POSTGRES_CONN_STRING(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


@lru_cache
def get_settings():
    return Settings()
