from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_APP_ENV = os.environ.get("APP_ENV", "development")
_ENV_SPECIFIC = PROJECT_ROOT / f".env.{_APP_ENV}"
ENV_FILE_PATH = _ENV_SPECIFIC if _ENV_SPECIFIC.exists() else PROJECT_ROOT / ".env"
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "project_remake.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE_PATH), env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="One-Tap Closer Remake", alias="APP_NAME")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8001, alias="APP_PORT")

    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    
    mysql_host: str = Field(default="localhost", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_user: str = Field(default="vscode", alias="MYSQL_USER")
    mysql_password: str = Field(default="", alias="MYSQL_PASSWORD")
    mysql_database: str = Field(default="one_tap_closer", alias="MYSQL_DATABASE")

    @property
    def database_url(self) -> str:
        # Check if an explicit DATABASE_URL is set in the environment (like in docker modes)
        # Otherwise, dynamically formulate it using the provided MYSQL variables.
        # But wait, Pydantic fields can't read `os.environ` easily here if we want dynamic property.
        if os.environ.get("DATABASE_URL"):
            return os.environ.get("DATABASE_URL")
        return f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"

    whatsapp_verify_token: str = Field(default="", alias="WHATSAPP_VERIFY_TOKEN")
    whatsapp_app_secret: str = Field(default="", alias="WHATSAPP_APP_SECRET")
    whatsapp_api_version: str = Field(default="v22.0", alias="WHATSAPP_API_VERSION")

    jwt_secret: str = Field(default="change_me", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_ttl_hours: int = Field(default=168, alias="JWT_TTL_HOURS")
    jwt_min_secret_length: int = Field(default=32, alias="JWT_MIN_SECRET_LENGTH")

    auth_rate_limit_max: int = Field(default=30, alias="AUTH_RATE_LIMIT_MAX")
    auth_rate_limit_window_seconds: int = Field(default=60, alias="AUTH_RATE_LIMIT_WINDOW_SECONDS")
    webhook_rate_limit_max: int = Field(default=120, alias="WEBHOOK_RATE_LIMIT_MAX")
    webhook_rate_limit_window_seconds: int = Field(default=60, alias="WEBHOOK_RATE_LIMIT_WINDOW_SECONDS")

    nvidia_api_key: str = Field(default="", alias="NVIDIA_API_KEY")
    nvidia_base_url: str = Field(default="https://integrate.api.nvidia.com/v1", alias="NVIDIA_BASE_URL")
    nvidia_model: str = Field(default="meta/llama-3.1-70b-instruct", alias="NVIDIA_MODEL")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    
    active_llm_provider: str = Field(default="gemini", alias="ACTIVE_LLM_PROVIDER")

    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(default="http://localhost:8001/auth/google/callback", alias="GOOGLE_REDIRECT_URI")
    google_customer_group_resource: str = Field(default="", alias="GOOGLE_CUSTOMER_GROUP_RESOURCE")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
