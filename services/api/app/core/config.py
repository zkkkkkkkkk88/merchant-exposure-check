from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/exposure"
    ark_api_key: SecretStr = SecretStr("")
    ark_model: str = "doubao-seed-2-0-lite-260215"
    amap_key: SecretStr = SecretStr("")
    tencent_map_key: SecretStr = SecretStr("")
    api_base_url: str = "http://localhost:8000"
    runtime_dir: Path = Path(".runtime")
    worker_stale_after_seconds: int = 15

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
