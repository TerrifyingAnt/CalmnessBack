import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Chat Microservice"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "goyda_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "goyda_password")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "goyda_db")
    DATABASE_URL: str = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"

    # MinIO Configuration
    MINIO_ROOT_USER: str = os.getenv("MINIO_ROOT_USER", "gh_user")
    MINIO_ROOT_PASSWORD: str = os.getenv("MINIO_ROOT_PASSWORD", "gh_password")
    MINIO_URL: str = os.getenv("MINIO_URL", "10.147.19.91:9000")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "False").lower() == "true"
    MINIO_BUCKET_NAME: str = os.getenv("MINIO_BUCKET_NAME", "chat-bucket")
    MINIO_PROXY_URL: str = os.getenv("MINIO_PROXY", "http://minio:9000")
    
    # Security
    # SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    # ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    class Config:
        case_sensitive = True

settings = Settings()