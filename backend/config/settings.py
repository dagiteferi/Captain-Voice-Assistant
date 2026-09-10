"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "captain-voice-assistant"
    llm_provider: str = "ollama"
    translator_provider: str = "argos"
    tts_provider: str = "coqui"


settings = Settings()
