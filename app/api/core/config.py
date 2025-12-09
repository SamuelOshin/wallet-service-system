"""
Application configuration management.

This module centralizes all environment-based configuration for the wallet service,
including database, Google OAuth, Paystack, JWT, and API key settings.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Attributes:
        APP_NAME (str): Name of the application.
        DEBUG (bool): Debug mode flag.
        API_V1_PREFIX (str): API version prefix for routes.
        APP_PORT (int): Port for the application to run on.
        DATABASE_URL (str): Database connection URL.
        SECRET_KEY (str): Secret key for JWT encoding/decoding.
        ALGORITHM (str): Algorithm used for JWT.
        ACCESS_TOKEN_EXPIRE_MINUTES (int): JWT token expiration time in minutes.
        GOOGLE_CLIENT_ID (str): Google OAuth client ID.
        GOOGLE_CLIENT_SECRET (str): Google OAuth client secret.
        GOOGLE_REDIRECT_URI (str): Google OAuth redirect URI.
        PAYSTACK_SECRET_KEY (str): Paystack secret key.
        PAYSTACK_PUBLIC_KEY (str): Paystack public key.
        PAYSTACK_WEBHOOK_SECRET (str): Paystack webhook secret.
        PAYSTACK_BASE_URL (str): Base URL for Paystack API.
        API_KEY_PREFIX (str): Prefix for generated API keys.
        MAX_API_KEYS_PER_USER (int): Maximum number of API keys allowed per user.
        FRONTEND_URL (str): URL of the frontend application.
    Examples:
        >>> settings = get_settings()
        >>> print(settings.APP_NAME)
        'Wallet Service'
    """

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    # App
    APP_NAME: str = "Wallet Service"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    APP_PORT: int = 8000
    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    # Paystack
    PAYSTACK_SECRET_KEY: str
    PAYSTACK_PUBLIC_KEY: str
    PAYSTACK_WEBHOOK_SECRET: str
    PAYSTACK_BASE_URL: str = "https://api.paystack.co"

    # API Keys
    API_KEY_PREFIX: str = "sk_live_"
    MAX_API_KEYS_PER_USER: int = 5

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings: Singleton settings object loaded from environment.

    Examples:
        >>> settings = get_settings()
        >>> database_url = settings.DATABASE_URL
    """
    return Settings()