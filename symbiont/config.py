"""Configuration management for the Symbiont SDK."""

import json
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class ConfigSource(str, Enum):
    """Configuration source enumeration."""
    ENVIRONMENT = "environment"
    FILE = "file"
    VAULT = "vault"
    DEFAULT = "default"


class DatabaseConfig(BaseModel):
    """Database connection configuration."""
    host: str = "localhost"
    port: int = 5432
    database: str = "symbiont"
    username: Optional[str] = None
    password: Optional[str] = None
    ssl_mode: str = "prefer"
    connection_timeout: int = 30
    max_connections: int = 20


class AuthConfig(BaseModel):
    """Authentication configuration."""
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_seconds: int = 3600
    jwt_refresh_expiration_seconds: int = 86400
    api_key_header: str = "Authorization"
    enable_refresh_tokens: bool = True
    token_issuer: str = "symbiont"
    token_audience: str = "symbiont-api"


class VectorConfig(BaseModel):
    """Vector database configuration."""
    provider: str = "qdrant"
    host: str = "localhost"
    port: int = 6333
    collection_name: str = "symbiont_vectors"
    vector_size: int = 1536
    distance_metric: str = "cosine"
    enable_indexing: bool = True
    batch_size: int = 100


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    enable_console: bool = True
    enable_structured: bool = False
    max_file_size: str = "10MB"
    backup_count: int = 5


class ClientConfig(BaseSettings):
    """Main client configuration class."""

    # API Configuration
    api_key: Optional[str] = Field(None, env="SYMBIONT_API_KEY")
    base_url: str = Field("http://localhost:8080/api/v1", env="SYMBIONT_BASE_URL")
    timeout: int = Field(30, env="SYMBIONT_TIMEOUT")
    max_retries: int = Field(3, env="SYMBIONT_MAX_RETRIES")

    # Component configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    vector: VectorConfig = Field(default_factory=VectorConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Feature flags
    enable_caching: bool = Field(True, env="SYMBIONT_ENABLE_CACHING")
    enable_metrics: bool = Field(True, env="SYMBIONT_ENABLE_METRICS")
    enable_debug: bool = Field(False, env="SYMBIONT_DEBUG")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator('base_url')
    def validate_base_url(cls, v):
        """Validate and normalize base URL."""
        if v:
            return v.rstrip('/')
        return v


class ConfigManager:
    """Main configuration management class."""

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """Initialize the configuration manager.

        Args:
            config_path: Path to configuration file (YAML or JSON)
        """
        self._config: Optional[ClientConfig] = None
        self._config_path = Path(config_path) if config_path else None
        self._sources: Dict[str, ConfigSource] = {}

    def load(self,
             config_path: Optional[Union[str, Path]] = None,
             force_reload: bool = False) -> ClientConfig:
        """Load configuration from various sources.

        Args:
            config_path: Optional path to configuration file
            force_reload: Force reload even if already loaded

        Returns:
            ClientConfig: Loaded configuration

        Raises:
            FileNotFoundError: If config file specified but not found
            ValueError: If config file format is invalid
        """
        if self._config and not force_reload:
            return self._config

        # Use provided path or stored path
        config_file_path = config_path or self._config_path

        # Start with environment variables and defaults
        config_dict = {}

        # Load from file if specified
        if config_file_path:
            config_file_path = Path(config_file_path)
            if config_file_path.exists():
                config_dict.update(self._load_from_file(config_file_path))
                self._sources.update(dict.fromkeys(config_dict.keys(), ConfigSource.FILE))
            elif config_path:  # Only raise if explicitly provided
                raise FileNotFoundError(f"Configuration file not found: {config_file_path}")

        # Create configuration with file data + environment overrides
        self._config = ClientConfig(**config_dict)

        # Track environment variable sources
        for field_name in self._config.__fields__:
            env_var = f"SYMBIONT_{field_name.upper()}"
            if env_var in os.environ:
                self._sources[field_name] = ConfigSource.ENVIRONMENT
            elif field_name not in self._sources:
                self._sources[field_name] = ConfigSource.DEFAULT

        return self._config

    def _load_from_file(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration from a file.

        Args:
            file_path: Path to configuration file

        Returns:
            Dict containing configuration data

        Raises:
            ValueError: If file format is unsupported or invalid
        """
        try:
            with open(file_path, encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yml', '.yaml']:
                    return yaml.safe_load(f) or {}
                elif file_path.suffix.lower() == '.json':
                    return json.load(f) or {}
                else:
                    raise ValueError(f"Unsupported config file format: {file_path.suffix}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file: {e}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}") from e

    def get_config(self) -> ClientConfig:
        """Get current configuration.

        Returns:
            ClientConfig: Current configuration

        Raises:
            RuntimeError: If configuration not loaded
        """
        if not self._config:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        return self._config

    def reload(self) -> ClientConfig:
        """Reload configuration from sources.

        Returns:
            ClientConfig: Reloaded configuration
        """
        return self.load(force_reload=True)

    def get_source(self, field_name: str) -> ConfigSource:
        """Get the source of a configuration field.

        Args:
            field_name: Name of the configuration field

        Returns:
            ConfigSource: Source of the field value
        """
        return self._sources.get(field_name, ConfigSource.DEFAULT)

    def validate_required_settings(self) -> Dict[str, str]:
        """Validate that required settings are present.

        Returns:
            Dict mapping missing fields to error messages
        """
        errors = {}
        config = self.get_config()

        # Check for critical missing values (only when actually needed for requests)
        # API key will be validated when making actual requests
        # if not config.api_key:
        #     errors['api_key'] = "API key is required for authentication"

        if config.auth.jwt_secret_key is None and config.auth.enable_refresh_tokens:
            errors['auth.jwt_secret_key'] = "JWT secret key required when refresh tokens enabled"  # nosec B105 - This is an error message, not a password

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dict representation of configuration
        """
        if not self._config:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        return self._config.dict()

    def save_to_file(self, file_path: Union[str, Path],
                     format: str = "yaml",
                     exclude_secrets: bool = True) -> None:
        """Save current configuration to file.

        Args:
            file_path: Path to save configuration
            format: File format ('yaml' or 'json')
            exclude_secrets: Whether to exclude sensitive values
        """
        if not self._config:
            raise RuntimeError("Configuration not loaded. Call load() first.")

        config_dict = self._config.dict()

        if exclude_secrets:
            # Remove sensitive fields
            sensitive_paths = [
                ['api_key'],
                ['auth', 'jwt_secret_key'],
                ['database', 'password']
            ]

            for path in sensitive_paths:
                current = config_dict
                for key in path[:-1]:
                    if key in current:
                        current = current[key]
                    else:
                        break
                else:
                    if path[-1] in current:
                        current[path[-1]] = None

        file_path = Path(file_path)

        with open(file_path, 'w', encoding='utf-8') as f:
            if format.lower() == 'yaml':
                yaml.safe_dump(config_dict, f, default_flow_style=False, indent=2)
            elif format.lower() == 'json':
                json.dump(config_dict, f, indent=2, default=str)
            else:
                raise ValueError(f"Unsupported format: {format}")


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance.

    Returns:
        ConfigManager: Global configuration manager
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> ClientConfig:
    """Get the current configuration.

    Returns:
        ClientConfig: Current configuration
    """
    return get_config_manager().get_config()


def load_config(config_path: Optional[Union[str, Path]] = None) -> ClientConfig:
    """Load configuration from file and environment.

    Args:
        config_path: Optional path to configuration file

    Returns:
        ClientConfig: Loaded configuration
    """
    return get_config_manager().load(config_path)
