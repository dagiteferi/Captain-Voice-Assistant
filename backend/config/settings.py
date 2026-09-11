"""Application settings — all configurable via .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "captain-voice-assistant"

    # ── Database ──────────────────────────────────────
    sqlite_url: str = "sqlite+aiosqlite:///./data/captain.db"

    # ── Directories ───────────────────────────────────
    audio_dir: str = "./data/audio"
    chroma_dir: str = "./chroma"

    # ── LLM (Gemini API — free tier) ──────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # ── Translation (MyMemory — free, no key) ─────────
    mymemory_email: str = ""  # Optional: raises daily limit from 1000 to 10000

    # ── TTS (Google Cloud TTS — free tier) ────────────
    google_tts_api_key: str = ""
    google_tts_voice_en: str = "en-US-Neural2-D"
    google_tts_voice_am: str = "am-ET-Standard-A"

    # ── Logging ───────────────────────────────────────
    log_level: str = "INFO"

    # ── CORS ──────────────────────────────────────────
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
