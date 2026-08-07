import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(".env")
ENV_FILE_ENCODING = "utf-8"


def _env_file_for_settings() -> Path | None:
    """Load .env only when readable (avoids crash for users without file ACL)."""
    if ENV_FILE.is_file() and os.access(ENV_FILE, os.R_OK):
        return ENV_FILE
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file_for_settings(),
        env_file_encoding=ENV_FILE_ENCODING,
    )

    database_url: str
    api_keys: str = ""
    host: str = "0.0.0.0"
    port: int = 8080
    rate_limit: str = "100/minute"

    alphavantage_api_key: str = ""
    alphavantage_base_url: str = "https://www.alphavantage.co/query"
    alphavantage_request_timeout: float = 30.0

    @property
    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}


@lru_cache(maxsize=None)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
