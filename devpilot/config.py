"""
DevPilot Configuration and Settings
"""
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """DevPilot application settings loaded from environment or defaults."""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "DevPilot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API and Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Gemini AI configuration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # Security & Guardrails
    DEFAULT_REPO_ROOT: Path = Path(__file__).resolve().parent.parent / "sample_repo"
    ALLOWED_COMMANDS: List[str] = [
        "pytest",
        "python -m pytest",
        "pytest -v",
        "pytest -v --tb=short",
        "python -m pytest -v",
        "python -m pytest -v --tb=short",
    ]
    COMMAND_TIMEOUT_SECONDS: int = 20
    MAX_FILE_READ_BYTES: int = 500_000  # 500 KB limit to prevent context exhaustion
    
    # Persistence
    DATABASE_PATH: Path = Path(__file__).resolve().parent.parent / "devpilot.sqlite3"
    
    # Secret redaction patterns
    REDACTED_STRINGS: List[str] = [
        "api_key",
        "token",
        "secret",
        "password",
        "credential",
    ]


settings = Settings()
