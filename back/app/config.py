from pydantic_settings import BaseSettings 
# Pydantic is used for data validation.
# BaseSettings automatically reads values from .env
from pathlib import Path

class Settings(BaseSettings):
    R2_ACCESS_KEY_ID: str
    R2_SECRET_ACCESS_KEY: str
    R2_ACCOUNT_ID: str
    R2_BUCKET: str
    R2_ENDPOINT: str
    R2_PUBLIC_URL: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str 
    POSTGRES_PORT: int
#    If .env or OS env does not provide them, the defaults are used.
    REDIS_HOST: str
    REDIS_PORT: int

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    class Config:  #Read variables from the file named .env and use UTF-8 encoding
        env_file = str(Path(__file__).resolve().parent.parent / ".env")
        env_file_encoding = 'utf-8'


settings = Settings()
