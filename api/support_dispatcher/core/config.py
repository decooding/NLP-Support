"""Core configuration and exceptions for Smart Support Dispatcher."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration loaded via environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General / Application
    APP_NAME: str = "Smart Support Dispatcher"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # System 1 (Laya Fast-Path / Hugging Face Spaces Docker Server)
    LAYA_MODEL_NAME: str = "multilingual"
    LAYA_REVISION: str = "main"
    LAYA_MIN_CONFIDENCE: float = Field(default=0.85, ge=0.0, le=1.0)
    LAYA_MAX_CONCURRENCY: int = Field(default=4, ge=1)
    LAYA_DEVICE: str = "cpu"
    LAYA_REMOTE_URL: str | None = None
    LAYA_REMOTE_TIMEOUT_SECONDS: float = Field(default=3.0, gt=0.0)

    # System 2 (Gemini Fallback)
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_MIN_CONFIDENCE: float = Field(default=0.70, ge=0.0, le=1.0)
    GEMINI_TIMEOUT_SECONDS: float = Field(default=3.5, gt=0.0)
    GEMINI_MAX_RETRIES: int = Field(default=2, ge=0)
    SYSTEM2_TOTAL_BUDGET_SECONDS: float = Field(default=10.0, gt=0.0)

    # Circuit Breaker & Resilience
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(default=5, ge=1)
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0.0)

    # Human in the Loop (HITL) & Storage
    HITL_QUEUE_ENABLED: bool = True
    DEDUPLICATION_CACHE_TTL_SECONDS: int = Field(default=3600, ge=1)


class DispatcherError(Exception):
    """Base exception for support dispatcher."""


class ValidationError(DispatcherError):
    """Raised when ticket validation fails."""


class ModelInferenceError(DispatcherError):
    """Raised when System 1 inference fails."""


class FallbackError(DispatcherError):
    """Raised when System 2 external API fails."""


class CircuitBreakerOpenError(DispatcherError):
    """Raised when circuit breaker is tripped open."""
