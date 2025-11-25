from pydantic import EmailStr, ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
        model_config = ConfigDict(
                env_file='./.env',
                extra='ignore'
        )

        DATABASE_URL: str
        MONGO_INITDB_DATABASE: str
        OPENAI_API_KEY: str
        CLIENT_ORIGIN: str
        EMAIL_FROM: EmailStr

        # JWT Configuration
        JWT_SECRET_KEY: str
        JWT_ALGORITHM: str = "HS256"

        # Gmail API Configuration
        GMAIL_CREDENTIALS_FILE: str = "credentials.json"
        GMAIL_TOKEN_FILE: str = "token.pickle"

        # Application Configuration
        APP_NAME: Optional[str] = "Minor Assistant API"
        ENVIRONMENT: Optional[str] = "development"
        ALLOWED_ORIGINS: Optional[str] = "http://localhost:3000,http://localhost:5173"

 
settings = Settings()
