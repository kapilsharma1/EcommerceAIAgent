"""Configuration management using Pydantic Settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings with validation."""
    
    # OpenAI Configuration
    openai_api_key: str
    
    # PostgreSQL Configuration
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "ecommerce_support"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: Optional[str] = None
    
    # LangSmith Configuration
    langchain_tracing_v2: bool = True
    langchain_api_key: Optional[str] = None
    langchain_project: str = "ecommerce-support-agent"
    
    # Application Configuration
    app_name: str = "ECommerce Support Agent"
    app_version: str = "1.0.0"
    log_level: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def get_database_url(self) -> str:
        """Get database URL, constructing it if not provided."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


# Global settings instance
settings = Settings()

