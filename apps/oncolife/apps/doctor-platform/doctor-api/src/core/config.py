"""
Centralized Configuration - Doctor API
=======================================

This module provides a single source of truth for all application settings.
Uses Pydantic Settings for type validation and environment variable loading.

Configuration is loaded from:
1. Environment variables (highest priority)
2. .env file (if present)
3. Default values (lowest priority)

Usage:
    from core.config import settings
    
    # Access settings
    database_url = settings.doctor_database_url
    debug_mode = settings.debug
"""

import os
from functools import lru_cache
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, computed_field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden by environment variables.
    Variable names are case-insensitive.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
    )
    
    # ==========================================================================
    # Application Settings
    # ==========================================================================
    app_name: str = Field(
        default="OncoLife Doctor API",
        description="Application name for logging and identification"
    )
    app_version: str = Field(
        default="1.0.0",
        description="Application version"
    )
    environment: str = Field(
        default="development",
        description="Deployment environment (development, staging, production)"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode with verbose logging"
    )
    local_dev_mode: bool = Field(
        default=False,
        description="Enable local development mode (bypasses Cognito auth)"
    )
    
    # ==========================================================================
    # Server Settings
    # ==========================================================================
    host: str = Field(
        default="0.0.0.0",
        description="Server host address"
    )
    port: int = Field(
        default=8001,
        description="Server port (different from patient API)"
    )
    
    # ==========================================================================
    # Doctor Database Settings
    # ==========================================================================
    doctor_db_user: Optional[str] = Field(
        default=None,
        description="Doctor database username"
    )
    doctor_db_password: Optional[str] = Field(
        default=None,
        description="Doctor database password"
    )
    doctor_db_host: Optional[str] = Field(
        default=None,
        description="Doctor database host"
    )
    doctor_db_port: Optional[str] = Field(
        default="5432",
        description="Doctor database port"
    )
    doctor_db_name: Optional[str] = Field(
        default=None,
        description="Doctor database name"
    )
    
    # ==========================================================================
    # Patient Database Settings (Read-only access for viewing patient data)
    # ==========================================================================
    patient_db_user: Optional[str] = Field(
        default=None,
        description="Patient database username"
    )
    patient_db_password: Optional[str] = Field(
        default=None,
        description="Patient database password"
    )
    patient_db_host: Optional[str] = Field(
        default=None,
        description="Patient database host"
    )
    patient_db_port: Optional[str] = Field(
        default="5432",
        description="Patient database port"
    )
    patient_db_name: Optional[str] = Field(
        default=None,
        description="Patient database name"
    )
    
    # ==========================================================================
    # AWS Cognito Settings (Authentication)
    # ==========================================================================
    aws_region: str = Field(
        default="us-east-1",
        description="AWS region for Cognito"
    )
    aws_access_key_id: Optional[str] = Field(
        default=None,
        description="AWS access key ID"
    )
    aws_secret_access_key: Optional[str] = Field(
        default=None,
        description="AWS secret access key"
    )
    cognito_user_pool_id: Optional[str] = Field(
        default=None,
        description="Cognito User Pool ID"
    )
    cognito_client_id: Optional[str] = Field(
        default=None,
        description="Cognito App Client ID"
    )
    cognito_client_secret: Optional[str] = Field(
        default=None,
        description="Cognito App Client Secret"
    )
    
    # ==========================================================================
    # CORS Settings
    # ==========================================================================
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5174",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # ==========================================================================
    # Logging Settings
    # ==========================================================================
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    log_format: str = Field(
        default="json",
        description="Log format (json or text)"
    )
    
    # ==========================================================================
    # Computed Properties
    # ==========================================================================
    @computed_field
    @property
    def doctor_database_url(self) -> Optional[str]:
        """Construct the doctor database URL from components."""
        if all([
            self.doctor_db_user,
            self.doctor_db_password,
            self.doctor_db_host,
            self.doctor_db_port,
            self.doctor_db_name
        ]):
            return (
                f"postgresql://{self.doctor_db_user}:{self.doctor_db_password}@"
                f"{self.doctor_db_host}:{self.doctor_db_port}/{self.doctor_db_name}?sslmode=require"
            )
        return None
    
    @computed_field
    @property
    def patient_database_url(self) -> Optional[str]:
        """Construct the patient database URL from components."""
        if all([
            self.patient_db_user,
            self.patient_db_password,
            self.patient_db_host,
            self.patient_db_port,
            self.patient_db_name
        ]):
            return (
                f"postgresql://{self.patient_db_user}:{self.patient_db_password}@"
                f"{self.patient_db_host}:{self.patient_db_port}/{self.patient_db_name}?sslmode=require"
            )
        return None
    
    @computed_field
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @computed_field
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"
    
    @computed_field
    @property
    def cognito_issuer(self) -> Optional[str]:
        """Construct the Cognito issuer URL."""
        if self.aws_region and self.cognito_user_pool_id:
            return f"https://cognito-idp.{self.aws_region}.amazonaws.com/{self.cognito_user_pool_id}"
        return None
    
    @computed_field
    @property
    def cognito_jwks_url(self) -> Optional[str]:
        """Construct the Cognito JWKS URL."""
        if self.cognito_issuer:
            return f"{self.cognito_issuer}/.well-known/jwks.json"
        return None


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()


# Global settings instance for easy import
settings = get_settings()





