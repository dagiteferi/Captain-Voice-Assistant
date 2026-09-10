from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "captain-voice-assistant"
    sqlite_url: str = "sqlite+aiosqlite:///./data/captain.db"
    llm_provider: str = "ollama"
    translator_provider: str = "argos"
    tts_provider: str = "coqui"


settings = Settings()
