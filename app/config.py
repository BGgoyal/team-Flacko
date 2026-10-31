from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT / ".env", Path(__file__).resolve().parents[1] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    session_secret: str = "dev-only-change-me"
    frontend_origin: str = "http://127.0.0.1:5173"
    database_url: str = f"sqlite:///{(Path(__file__).resolve().parents[1] / 'fincoach.db').as_posix()}"

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_verify_service_sid: str = ""

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    angel_one_api_key: str = ""
    angel_one_client_code: str = ""
    angel_one_jwt_token: str = ""
    angel_one_refresh_token: str = ""
    angel_one_feed_token: str = ""

    coingecko_api_key: str = ""
    metals_api_base: str = "https://api.gold-api.com"

    @property
    def twilio_configured(self) -> bool:
        return bool(
            self.twilio_account_sid
            and self.twilio_auth_token
            and self.twilio_verify_service_sid
        )

    @property
    def openai_configured(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def angel_configured(self) -> bool:
        return bool(self.angel_one_api_key and self.angel_one_jwt_token)


@lru_cache
def get_settings() -> Settings:
    return Settings()
