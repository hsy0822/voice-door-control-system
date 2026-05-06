"""后端配置（环境变量覆盖）。"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "*"

    data_dir: Path = Field(default=_BACKEND_ROOT / "data")

    secret_key: str = "change-me-in-production-use-long-random-string"
    access_token_expire_minutes: int = 60 * 24 * 7

    seed_admin_username: str = "admin"
    seed_admin_password: str = "admin123"

    asr_verify_url: str = "http://127.0.0.1:8090/api/v1/verify"
    voice_verify_url: str = ""
    emotion_analyze_url: str = ""
    ai_http_timeout_sec: float = 120.0

    mock_voiceprint_match: bool = False
    mock_emotion_duress: bool = False

    @property
    def db_path(self) -> Path:
        return self.data_dir / "app.db"


settings = Settings()
