"""
Application configuration loaded from environment variables / .env file.
Uses pydantic-settings for type-safe config management.
"""

import os
from pydantic_settings import BaseSettings

# Resolve .env path relative to this file's parent directory (project root)
_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:devank@localhost:5432/recipe_planner"
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    class Config:
        env_file = _ENV_PATH
        env_file_encoding = "utf-8"


# Singleton settings instance
settings = Settings()
