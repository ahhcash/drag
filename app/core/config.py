from functools import lru_cache
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()


class Settings(BaseSettings):
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    db_user: str = os.getenv("DB_USER", "")
    db_host: str = os.getenv("DB_HOST", "")
    db_password: str = os.getenv("DB_PASSWORD", "")
    db_port: str = os.getenv("DB_PORT", "")
    db_name: str = os.getenv("DB_NAME", "")

    # Prefect (we'll add these later)
    prefect_api_url: str = "http://localhost:4200/api"

    @property
    def supabase_postgres_url(self) -> str:
        escaped_password = quote_plus(self.db_password)

        return (
            f"postgresql+psycopg://{self.db_user}:{escaped_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def async_postgres_url(self) -> str:
        escaped_password = quote_plus(self.db_password)

        return (
            f"postgresql+asyncpg://{self.db_user}:{escaped_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
