"""
Centralized Configuration Management for OncoLife Patient API.

This module uses Pydantic Settings to provide:
- Type-safe configuration with validation
- Environment variable loading with .env file support
- Default values with override capability
- Computed properties for derived settings

Environment Variables:
    - Load from .env file in development
    - Override via actual environment variables in production

Usage:
    from core import settings
    
    # Access settings
    db_url = settings.patient_database_url
    debug = settings.debug
"""

from functools import lru_cache
from typing import List, Optional
from pydantic import Field, field_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
import urllib.parse


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings are validated on startup. Missing required settings
    will raise a clear error message.
    
    Attributes:
        app_name: Application name for logging and identification
        app_version: Semantic version of the application
        debug: Enable debug mode (detailed errors, hot reload)
        environment: Current environment (development, staging, production)
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars not defined here
    )
    
    # ==========================================================================
    # APPLICATION SETTINGS
    # ==========================================================================
    
    app_name: str = Field(
        default="OncoLife Patient API",
        description="Application name for logging and identification"
    )
    app_version: str = Field(
        default="1.0.0",
        description="Semantic version of the application"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode for development"
    )
    environment: str = Field(
        default="development",
        description="Current environment: development, staging, production"
    )
    local_dev_mode: bool = Field(
        default=False,
        description="Enable local development mode (bypasses Cognito auth)"
    )
    
    # ==========================================================================
    # API SETTINGS
    # ==========================================================================
    
    api_v1_prefix: str = Field(
        default="/api/v1",
        description="API version 1 prefix for all endpoints"
    )
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # ==========================================================================
    # PATIENT DATABASE SETTINGS
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
    patient_db_port: str = Field(
        default="5432",
        description="Patient database port"
    )
    patient_db_name: Optional[str] = Field(
        default=None,
        description="Patient database name"
    )
    
    # Database connection pool settings
    db_pool_size: int = Field(
        default=5,
        description="Database connection pool size"
    )
    db_max_overflow: int = Field(
        default=10,
        description="Maximum overflow connections beyond pool size"
    )
    db_pool_recycle: int = Field(
        default=1800,
        description="Seconds before recycling a connection (30 minutes)"
    )
    
    # ==========================================================================
    # DOCTOR DATABASE SETTINGS
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
    doctor_db_port: str = Field(
        default="5432",
        description="Doctor database port"
    )
    doctor_db_name: Optional[str] = Field(
        default=None,
        description="Doctor database name"
    )
    
    # ==========================================================================
    # AUTHENTICATION SETTINGS
    # ==========================================================================
    
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT token signing"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="Algorithm for JWT token signing"
    )
    jwt_access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh token expiration time in days"
    )
    
    # ==========================================================================
    # LOGGING SETTINGS
    # ==========================================================================
    
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )
    log_format: str = Field(
        default="json",
        description="Log format: json (production) or text (development)"
    )
    
    # ==========================================================================
    # AWS SETTINGS
    # ==========================================================================
    
    aws_region: str = Field(
        default="us-west-2",
        description="AWS region for all services"
    )
    aws_access_key_id: Optional[str] = Field(
        default=None,
        description="AWS access key ID"
    )
    aws_secret_access_key: Optional[str] = Field(
        default=None,
        description="AWS secret access key"
    )
    
    # Cognito Settings
    cognito_user_pool_id: Optional[str] = Field(
        default=None,
        description="AWS Cognito User Pool ID"
    )
    cognito_client_id: Optional[str] = Field(
        default=None,
        description="AWS Cognito App Client ID"
    )
    cognito_client_secret: Optional[str] = Field(
        default=None,
        description="AWS Cognito App Client Secret"
    )
    
    # S3 Settings (for document storage)
    s3_referral_bucket: str = Field(
        default="oncolife-referrals",
        description="S3 bucket for storing referral documents"
    )
    s3_education_bucket: str = Field(
        default="oncolife-education",
        description="S3 bucket for storing education documents"
    )
    
    # Textract Settings (for OCR)
    textract_enabled: bool = Field(
        default=True,
        description="Enable AWS Textract for OCR processing"
    )
    
    # SES Settings (for email)
    ses_sender_email: str = Field(
        default="noreply@oncolife.com",
        description="Email address for sending notifications"
    )
    ses_sender_name: str = Field(
        default="OncoLife Care",
        description="Display name for email sender"
    )
    
    # SNS Settings (for SMS)
    sns_enabled: bool = Field(
        default=True,
        description="Enable AWS SNS for SMS notifications"
    )
    
    # ==========================================================================
    # MONITORING & NOTIFICATIONS
    # ==========================================================================
    
    # Slack Notifications
    slack_webhook_url: Optional[str] = Field(
        default=None,
        description="Slack webhook URL for sending alerts"
    )
    
    # SNS Alert Topic (for email/SMS alerts)
    sns_alert_topic_arn: Optional[str] = Field(
        default=None,
        description="SNS Topic ARN for alert notifications"
    )
    
    # CloudWatch Metrics
    cloudwatch_namespace: str = Field(
        default="OncoLife/PatientAPI",
        description="CloudWatch namespace for custom metrics"
    )
    
    # ==========================================================================
    # ONBOARDING SETTINGS
    # ==========================================================================
    
    onboarding_welcome_email_template: str = Field(
        default="oncolife-welcome",
        description="SES template name for welcome emails"
    )
    onboarding_temp_password_length: int = Field(
        default=12,
        description="Length of temporary passwords"
    )
    onboarding_reminder_max_count: int = Field(
        default=3,
        description="Max reminder emails to send for incomplete onboarding"
    )
    onboarding_reminder_interval_days: int = Field(
        default=2,
        description="Days between onboarding reminder emails"
    )
    
    # Terms & Privacy versions
    terms_version: str = Field(
        default="1.0",
        description="Current version of Terms & Conditions"
    )
    privacy_version: str = Field(
        default="1.0",
        description="Current version of Privacy Policy"
    )
    hipaa_version: str = Field(
        default="1.0",
        description="Current version of HIPAA Notice"
    )
    
    # ==========================================================================
    # FAX SERVICE SETTINGS
    # ==========================================================================
    
    fax_inbound_number: str = Field(
        default="+18001234567",
        description="Inbound fax number for receiving referrals"
    )
    fax_webhook_secret: Optional[str] = Field(
        default=None,
        description="Secret for validating fax webhook requests"
    )
    
    # ==========================================================================
    # EXTERNAL SERVICES
    # ==========================================================================
    
    # OpenAI / LLM Settings (for future use if needed)
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key for LLM features"
    )
    
    # Pinecone Settings (for vector search if needed)
    pinecone_api_key: Optional[str] = Field(
        default=None,
        description="Pinecone API key for vector database"
    )
    pinecone_environment: Optional[str] = Field(
        default=None,
        description="Pinecone environment"
    )
    
    # ==========================================================================
    # COMPUTED PROPERTIES
    # ==========================================================================
    
    @computed_field
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @computed_field
    @property
    def patient_database_url(self) -> Optional[str]:
        """
        Construct the full PostgreSQL connection URL for patient database.
        
        Returns:
            PostgreSQL connection URL or None if not configured
        """
        if not all([
            self.patient_db_user,
            self.patient_db_password,
            self.patient_db_host,
            self.patient_db_name
        ]):
            return None
        
        # URL encode password to handle special characters
        encoded_password = urllib.parse.quote_plus(self.patient_db_password)
        
        return (
            f"postgresql://{self.patient_db_user}:{encoded_password}@"
            f"{self.patient_db_host}:{self.patient_db_port}/{self.patient_db_name}?sslmode=require"
        )
    
    @computed_field
    @property
    def doctor_database_url(self) -> Optional[str]:
        """
        Construct the full PostgreSQL connection URL for doctor database.
        
        Returns:
            PostgreSQL connection URL or None if not configured
        """
        if not all([
            self.doctor_db_user,
            self.doctor_db_password,
            self.doctor_db_host,
            self.doctor_db_name
        ]):
            return None
        
        encoded_password = urllib.parse.quote_plus(self.doctor_db_password)
        
        return (
            f"postgresql://{self.doctor_db_user}:{encoded_password}@"
            f"{self.doctor_db_host}:{self.doctor_db_port}/{self.doctor_db_name}?sslmode=require"
        )
    
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
    
    # ==========================================================================
    # VALIDATORS
    # ==========================================================================
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(f"log_level must be one of: {valid_levels}")
        return upper_v
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Ensure environment is valid."""
        valid_envs = {"development", "staging", "production", "testing"}
        lower_v = v.lower()
        if lower_v not in valid_envs:
            raise ValueError(f"environment must be one of: {valid_envs}")
        return lower_v


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are only loaded once,
    improving performance and ensuring consistency.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()


# Global settings instance for easy import
settings = get_settings()

