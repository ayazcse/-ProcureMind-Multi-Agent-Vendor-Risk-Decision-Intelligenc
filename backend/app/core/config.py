"""
Central application configuration.

Loaded once from environment variables / .env file via pydantic-settings.
This is the SINGLE place that decides whether ProcureMind runs in
LLM-augmented mode or pure deterministic (rule-based) mode.
"""
from __future__ import annotations
from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "sqlite:///./procuremind.db"

    # LLM
    llm_provider: Literal["anthropic", "openai", "none"] = "none"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # App
    app_env: str = "development"
    secret_key: str = "dev-secret"
    max_upload_size_mb: int = 10
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_enabled(self) -> bool:
        """
        True only if a provider is explicitly selected AND the matching
        API key is actually present (not the placeholder text).
        """
        if self.llm_provider == "anthropic":
            return bool(self.anthropic_api_key) and "your_" not in self.anthropic_api_key
        if self.llm_provider == "openai":
            return bool(self.openai_api_key) and "your_" not in self.openai_api_key
        return False


@lru_cache
def get_settings() -> Settings:
    return Settings()
