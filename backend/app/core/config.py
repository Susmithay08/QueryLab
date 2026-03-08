from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./querylab.db"
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    FRONTEND_URL: str = "http://localhost:5173"
    MAX_QUERY_ROWS: int = 500
    QUERY_TIMEOUT_SEC: int = 10

    class Config:
        env_file = ".env"

settings = Settings()
