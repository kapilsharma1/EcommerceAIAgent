"""Configuration management using Pydantic Settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import ssl


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
        """Get database URL, constructing it if not provided.
        
        Automatically strips sslmode parameter from URL as asyncpg doesn't support it.
        SSL is configured separately via get_ssl_config().
        """
        if self.database_url:
            # Parse URL and remove sslmode parameter (asyncpg doesn't support it)
            parsed = urlparse(self.database_url)
            query_params = parse_qs(parsed.query)
            
            # Remove sslmode from query parameters
            query_params.pop('sslmode', None)
            
            # Rebuild query string without sslmode
            new_query = urlencode(query_params, doseq=True)
            
            # Reconstruct URL
            new_parsed = parsed._replace(query=new_query)
            url = urlunparse(new_parsed)
            
            return url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    def get_ssl_config(self) -> dict:
        """Get SSL configuration and connection args for asyncpg based on database_url.
        
        Checks for sslmode parameter in the original database_url and converts it
        to asyncpg-compatible SSL configuration. For Supabase and cloud databases,
        creates an SSL context that doesn't verify certificates to handle
        self-signed certificates in the chain.
        
        Also disables prepared statement cache for pgbouncer connections (Supabase pooler)
        as pgbouncer doesn't support prepared statements properly.
        
        Returns:
            dict with connection arguments for asyncpg (ssl, statement_cache_size, etc.)
        """
        if self.database_url:
            parsed = urlparse(self.database_url)
            query_params = parse_qs(parsed.query)
            sslmode = query_params.get('sslmode', [''])[0]
            
            # Check if this is a cloud database (Supabase, AWS, etc.)
            is_cloud_db = (
                'supabase' in parsed.netloc or 
                'amazonaws' in parsed.netloc or 
                'pooler' in parsed.netloc
            )
            
            # Check if using pgbouncer (Supabase connection pooler)
            is_pgbouncer = 'pooler' in parsed.netloc
            
            connect_args = {}
            
            # Configure SSL
            if sslmode == 'disable':
                connect_args['ssl'] = False
            elif sslmode == 'require' or sslmode == 'prefer' or is_cloud_db:
                # For cloud databases, create SSL context without certificate verification
                # to handle self-signed certificates in the chain
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                connect_args['ssl'] = ssl_context
            else:
                connect_args['ssl'] = False
            
            # Disable prepared statement cache for pgbouncer connections
            # PgBouncer doesn't support prepared statements properly
            if is_pgbouncer:
                connect_args['statement_cache_size'] = 0
                connect_args['prepared_statement_cache_size'] = 0
            
            return connect_args
        return {'ssl': False}


# Global settings instance
settings = Settings()

