from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "captain-voice-assistant"
    sqlite_url: str = "sqlite+aiosqlite:///./data/captain.db"
    audio_dir: str = "./data/audio"
    chroma_dir: str = "./chroma"
    llm_provider: str = "ollama"
    translator_provider: str = "argos"
    tts_provider: str = "coqui"


    cors_origins: list[str] | str = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ]

    @property
    def cors_origins_list(self) -> list[str]:
        if isinstance(self.cors_origins, list):
            return self.cors_origins
        if isinstance(self.cors_origins, str):
            if self.cors_origins.startswith("["):
                import json

                try:
                    return json.loads(self.cors_origins)
                except Exception:
                    pass
            return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return []


settings = Settings()
