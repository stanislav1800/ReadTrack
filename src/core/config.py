from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_token: str
    log_level: str = "INFO"
    parse_mode: Optional[Literal["HTML", "Markdown", "MarkdownV2"]] = None
    protect_content: Optional[bool] = None
    drop_pending_updates: bool = False
    admin_ids: list[int]
    show_alert: bool = False
    show_auth_users: bool = False

    # Database
    db_user: str
    db_password: str
    db_host: str
    db_port: int = 5432
    db_name: str
    db_schema: Optional[str] = None

    # Proxy
    proxy_url: Optional[str] = None
    proxy_user: Optional[str] = None
    proxy_password: Optional[str] = None
    proxy_ip: Optional[str] = None
    proxy_port: Optional[int] = None

    # Redis
    redis_url: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def get_db_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    def get_db_url_for_alembic(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    def get_proxy(self) -> Optional[str]:
        if self.proxy_ip:
            return f"http://{self.proxy_user}:{self.proxy_password}@{self.proxy_ip}:{self.proxy_port}"
        return None


settings = Settings()
