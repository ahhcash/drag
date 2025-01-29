from functools import lru_cache
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    openai_api_key: str = "not set"

    supabase_postgres_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/vectors"

    # Prefect (we'll add these later)
    prefect_api_url: str = "http://localhost:4200/api"

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache
def get_settings() -> Settings:
    return Settings()
