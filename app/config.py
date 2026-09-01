from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str = Field(validation_alias="TELEGRAM_BOT_TOKEN")
    owner_telegram_id: int = Field(gt=0, validation_alias="OWNER_TELEGRAM_ID")
    openai_api_key: str = Field(validation_alias="OPENAI_API_KEY")
    database_url: str = Field(validation_alias="DATABASE_URL")

    bot_name: str = Field(default="Personal AI", validation_alias="BOT_NAME")
    owner_name: str = Field(default="", validation_alias="OWNER_NAME")
    personality: str = Field(
        default="You are a helpful, natural and personal AI assistant.",
        validation_alias="PERSONALITY",
    )
    interests: str = Field(default="", validation_alias="INTERESTS")
    timezone: str = Field(default="UTC", validation_alias="TIMEZONE")

    openai_model: str = Field(
        default="gpt-5.6-luna",
        validation_alias="OPENAI_MODEL",
    )
    transcription_model: str = Field(
        default="gpt-4o-mini-transcribe",
        validation_alias="TRANSCRIPTION_MODEL",
    )
    context_messages: int = Field(
        default=20,
        ge=1,
        le=100,
        validation_alias="CONTEXT_MESSAGES",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator(
        "telegram_bot_token",
        "openai_api_key",
        "database_url",
        "openai_model",
        "transcription_model",
        mode="before",
    )
    @classmethod
    def reject_blank_required_strings(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("must not be empty")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
