import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "User Profile Microservice"
    API_V1_STR: str = "/api/v1"

    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "goyda_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "goyda_password")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "goyda_db")
    DATABASE_URL: str = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
    class Config:
        case_sensitive = True

settings = Settings()
