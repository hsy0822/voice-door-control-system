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
    voice_enroll_url: str = ""          # 声纹注册服务地址
    emotion_analyze_url: str = ""
    ai_http_timeout_sec: float = 120.0

    # 仅联调：未配置 VOICE_VERIFY_URL 时若三段 wav 齐全也视为通过（不做真实声纹比对，勿用于生产）
    voice_verify_allow_segments_stub: bool = False

    mock_voiceprint_match: bool = False
    mock_emotion_duress: bool = False

    @property
    def db_path(self) -> Path:
        return self.data_dir / "app.db"


settings = Settings()
