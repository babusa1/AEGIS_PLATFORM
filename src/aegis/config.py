"""
AEGIS Configuration Module

Centralized configuration management using Pydantic Settings.
Supports environment variables and .env files.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AegisSettings(BaseSettings):
    """Main application settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="AEGIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Application
    env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    log_level: str = "INFO"
    secret_key: SecretStr = Field(default=SecretStr("dev-secret-key-change-me"))
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    api_reload: bool = True


class GraphDBSettings(BaseSettings):
    """Graph database (Neptune/JanusGraph) settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="GRAPH_DB_",
        env_file=".env",
        extra="ignore",
    )
    
    host: str = "localhost"
    port: int = 8182
    use_ssl: bool = False
    
    @property
    def connection_url(self) -> str:
        """Get the Gremlin connection URL."""
        protocol = "wss" if self.use_ssl else "ws"
        return f"{protocol}://{self.host}:{self.port}/gremlin"


class OpenSearchSettings(BaseSettings):
    """OpenSearch (vector database) settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="OPENSEARCH_",
        env_file=".env",
        extra="ignore",
    )
    
    host: str = "localhost"
    port: int = 9200
    use_ssl: bool = False
    user: str = "admin"
    password: SecretStr = Field(default=SecretStr("admin"))
    
    # Index names
    vector_index: str = "aegis-vectors"
    documents_index: str = "aegis-documents"
    
    @property
    def connection_url(self) -> str:
        """Get the OpenSearch connection URL."""
        protocol = "https" if self.use_ssl else "http"
        return f"{protocol}://{self.host}:{self.port}"


class PostgresSettings(BaseSettings):
    """PostgreSQL/TimescaleDB settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_",
        env_file=".env",
        extra="ignore",
    )
    
    host: str = "localhost"
    port: int = 5432
    user: str = "aegis"
    password: SecretStr = Field(default=SecretStr("aegis_dev_password"))
    database: str = "aegis"
    min_pool_size: int = 2
    max_pool_size: int = 10
    
    @property
    def connection_url(self) -> str:
        """Get the PostgreSQL connection URL."""
        pwd = self.password.get_secret_value()
        return f"postgresql://{self.user}:{pwd}@{self.host}:{self.port}/{self.database}"


class RedisSettings(BaseSettings):
    """Redis cache settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=".env",
        extra="ignore",
    )
    
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: SecretStr | None = None
    
    @property
    def connection_url(self) -> str:
        """Get the Redis connection URL."""
        if self.password:
            pwd = self.password.get_secret_value()
            return f"redis://:{pwd}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class KafkaSettings(BaseSettings):
    """Kafka event streaming settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="KAFKA_",
        env_file=".env",
        extra="ignore",
    )
    
    bootstrap_servers: str = "localhost:9092"
    consumer_group: str = "aegis-consumers"
    
    # Topic names
    fhir_ingest_topic: str = "aegis.ingest.fhir"
    hl7_ingest_topic: str = "aegis.ingest.hl7"
    events_topic: str = "aegis.events"
    agent_actions_topic: str = "aegis.agent.actions"


class LLMSettings(BaseSettings):
    """LLM (Bedrock/Ollama/Mock) settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        extra="ignore",
    )
    
    # Provider selection: mock, bedrock, ollama
    llm_provider: Literal["mock", "bedrock", "ollama"] = "mock"
    
    # AWS Bedrock settings
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: SecretStr | None = None
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    
    # Ollama settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    
    # Common settings
    max_tokens: int = 4096
    temperature: float = 0.7


class AuthSettings(BaseSettings):
    """Authentication settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        extra="ignore",
    )
    
    # Provider: local, cognito
    auth_provider: Literal["local", "cognito"] = "local"
    
    # Local JWT settings
    jwt_secret_key: SecretStr = Field(default=SecretStr("jwt-secret-change-me"))
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    
    # Cognito settings (when auth_provider=cognito)
    cognito_user_pool_id: str | None = None
    cognito_client_id: str | None = None
    cognito_region: str = "us-east-1"


class TenantSettings(BaseSettings):
    """Multi-tenant settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        extra="ignore",
    )
    
    default_tenant_id: str = "default"
    enable_multi_tenant: bool = False


class Settings:
    """
    Aggregated settings container.
    
    Usage:
        from aegis.config import get_settings
        settings = get_settings()
        print(settings.app.api_port)
        print(settings.graph_db.connection_url)
    """
    
    def __init__(self):
        self.app = AegisSettings()
        self.graph_db = GraphDBSettings()
        self.postgres = PostgresSettings()
        self.redis = RedisSettings()
        self.opensearch = OpenSearchSettings()
        self.kafka = KafkaSettings()
        self.llm = LLMSettings()
        self.auth = AuthSettings()
        self.tenant = TenantSettings()
    
    @property
    def is_development(self) -> bool:
        return self.app.env == "development"
    
    @property
    def is_production(self) -> bool:
        return self.app.env == "production"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings: The application settings
    """
    return Settings()
