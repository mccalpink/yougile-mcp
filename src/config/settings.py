"""
Configuration settings for YouGile MCP server.
Manages environment variables and default values.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """YouGile MCP server configuration.

    Multi-tenant env vars (YOUGILE_KEY_<SLUG>, YOUGILE_LABEL_<SLUG>,
    YOUGILE_COMPANY_<SLUG>) и HTTP transport vars (YOUGILE_TRANSPORT,
    YOUGILE_HOST, YOUGILE_PORT, YOUGILE_HTTP_PATH) читает напрямую
    AuthRegistry / run_server.py из os.environ, минуя Settings.
    extra="ignore" чтобы Pydantic не валидировал их здесь.
    """

    model_config = SettingsConfigDict(
        env_prefix="YOUGILE_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # YouGile API settings (legacy single-tenant)
    yougile_base_url: str = "https://yougile.com"
    yougile_email: Optional[str] = None
    yougile_password: Optional[str] = None
    yougile_company_id: Optional[str] = None
    yougile_api_key: Optional[str] = None

    # HTTP client settings
    yougile_timeout: int = 30
    yougile_max_retries: int = 3
    yougile_rate_limit_per_minute: int = 50

    # MCP server settings
    server_name: str = "YouGile MCP Server"
    server_version: str = "1.0.0"

    # User-configurable context instructions (set via MCP client config)
    user_context: Optional[str] = None

    # Development settings
    debug: bool = False
    log_level: str = "INFO"


# Find .env file relative to this settings.py file
def find_env_file():
    """Find .env file in project root."""
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent  # Go up to project root
    env_file = project_root / ".env"
    return str(env_file) if env_file.exists() else None

# Global settings instance with explicit env file path
env_file_path = find_env_file()
if env_file_path:
    settings = Settings(_env_file=env_file_path)
else:
    settings = Settings()