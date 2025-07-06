"""Centralized Configuration Management for WhisperSync Agents.

This module provides centralized configuration management with environment-based
overrides, type safety, and validation. It replaces hardcoded values throughout
the codebase with a flexible, testable configuration system.

WHY CENTRALIZED CONFIG:
- Eliminates hardcoded constants scattered across files
- Enables environment-specific configurations (dev/staging/prod)
- Provides type safety and validation for configuration values
- Simplifies testing with configuration overrides
- Supports secure secret management and rotation

DESIGN PATTERNS:
- Dataclass pattern for type safety and IDE support
- Factory pattern for environment-specific configurations
- Singleton pattern for global configuration access
- Environment variable pattern for deployment flexibility
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Deployment environment types.
    
    WHY ENUM: Type safety for environment names and prevents typos
    that could cause production issues.
    """
    
    DEVELOPMENT = "development"
    TESTING = "testing" 
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(Enum):
    """Logging level configuration.
    
    WHY ENUM: Ensures valid logging levels and provides IDE autocompletion.
    """
    
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class AWSConfig:
    """AWS service configuration.
    
    WHY SEPARATE AWS CONFIG:
    - Groups AWS-specific settings for clarity
    - Enables easy testing with mock AWS services
    - Provides single place for AWS resource configuration
    - Supports multi-region deployments
    """
    
    region: str = field(default="us-east-1")
    bucket_name: str = field(default="macbook-transcriptions")
    lambda_timeout: int = field(default=300)  # 5 minutes
    lambda_memory: int = field(default=512)   # MB
    enable_xray: bool = field(default=False)
    
    # Bedrock configuration
    bedrock_model: str = field(default="anthropic.claude-3-5-sonnet-20241022-v2:0")
    max_tokens: int = field(default=2000)
    bedrock_timeout: int = field(default=30)  # seconds
    
    # S3 configuration
    s3_max_connections: int = field(default=50)
    s3_retry_attempts: int = field(default=3)
    s3_retry_mode: str = field(default="adaptive")
    
    def __post_init__(self):
        """Validate AWS configuration after initialization."""
        if self.lambda_timeout > 900:  # AWS Lambda max timeout
            raise ValueError("Lambda timeout cannot exceed 900 seconds")
        if self.lambda_memory < 128 or self.lambda_memory > 10240:
            raise ValueError("Lambda memory must be between 128MB and 10240MB")


@dataclass
class StrandsConfig:
    """Strands SDK configuration.
    
    WHY STRANDS CONFIG:
    - Manages Strands SDK availability and fallback behavior
    - Configures mock vs. real Strands based on environment
    - Provides agent-specific configuration
    - Handles service discovery and registration
    """
    
    enabled: bool = field(default=False)
    use_mocks: bool = field(default=True)
    endpoint: Optional[str] = field(default=None)
    api_key: Optional[str] = field(default=None)
    
    # Agent configuration
    agent_timeout: int = field(default=60)  # seconds
    max_retry_attempts: int = field(default=3)
    enable_agent_warmup: bool = field(default=True)
    
    def __post_init__(self):
        """Validate Strands configuration."""
        if self.enabled and not self.use_mocks and not self.endpoint:
            raise ValueError("Strands endpoint required when not using mocks")


@dataclass
class SecurityConfig:
    """Security and authentication configuration.
    
    WHY SECURITY CONFIG:
    - Centralizes security-related settings
    - Manages secret names and access patterns
    - Configures encryption and access controls
    - Supports compliance and audit requirements
    """
    
    # GitHub token configuration
    github_secret_name: str = field(default="github/personal_token")
    github_secret_region: str = field(default="us-east-1")
    
    # Encryption configuration
    enable_s3_encryption: bool = field(default=True)
    kms_key_id: Optional[str] = field(default=None)
    
    # Access control
    require_tls: bool = field(default=True)
    max_transcript_size: int = field(default=1024 * 1024)  # 1MB
    allowed_content_types: List[str] = field(default_factory=lambda: [
        "text/plain",
        "audio/wav", 
        "audio/mp3",
        "audio/m4a"
    ])
    
    def __post_init__(self):
        """Validate security configuration."""
        if self.max_transcript_size > 10 * 1024 * 1024:  # 10MB
            raise ValueError("Maximum transcript size cannot exceed 10MB")


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration.
    
    WHY MONITORING CONFIG:
    - Centralizes observability settings
    - Configures metrics, logging, and tracing
    - Manages alert thresholds and notification settings
    - Supports different monitoring strategies per environment
    """
    
    # Logging configuration
    log_level: LogLevel = field(default=LogLevel.INFO)
    enable_structured_logging: bool = field(default=True)
    log_retention_days: int = field(default=30)
    
    # Metrics configuration
    enable_custom_metrics: bool = field(default=True)
    metrics_namespace: str = field(default="WhisperSync")
    
    # Tracing configuration
    enable_xray: bool = field(default=False)
    enable_opentelemetry: bool = field(default=True)
    tracing_sample_rate: float = field(default=0.1)  # 10% sampling
    
    # Alert thresholds
    error_rate_threshold: float = field(default=0.05)  # 5%
    latency_threshold_ms: int = field(default=5000)    # 5 seconds
    
    def __post_init__(self):
        """Validate monitoring configuration."""
        if not 0.0 <= self.tracing_sample_rate <= 1.0:
            raise ValueError("Tracing sample rate must be between 0.0 and 1.0")
        if not 0.0 <= self.error_rate_threshold <= 1.0:
            raise ValueError("Error rate threshold must be between 0.0 and 1.0")


@dataclass
class AgentConfig:
    """Agent-specific configuration.
    
    WHY AGENT CONFIG:
    - Configures individual agent behavior
    - Manages routing confidence thresholds
    - Controls agent coordination and fallback behavior
    - Enables agent-specific performance tuning
    """
    
    # Routing configuration
    min_routing_confidence: float = field(default=0.6)
    enable_multi_agent_routing: bool = field(default=True)
    max_agents_per_request: int = field(default=3)
    
    # Processing configuration
    max_processing_time: int = field(default=30)  # seconds per agent
    enable_parallel_processing: bool = field(default=True)
    
    # Fallback configuration
    enable_keyword_fallback: bool = field(default=True)
    unknown_agent_threshold: float = field(default=0.3)
    
    # GitHub agent specific
    github_default_visibility: str = field(default="public")
    github_default_license: str = field(default="MIT")
    
    # Work agent specific
    work_log_format: str = field(default="markdown")
    enable_weekly_summaries: bool = field(default=True)
    
    # Memory agent specific
    memory_format: str = field(default="jsonl")
    enable_sentiment_analysis: bool = field(default=False)
    
    def __post_init__(self):
        """Validate agent configuration."""
        if not 0.0 <= self.min_routing_confidence <= 1.0:
            raise ValueError("Routing confidence must be between 0.0 and 1.0")
        if self.max_agents_per_request < 1:
            raise ValueError("Maximum agents per request must be at least 1")


@dataclass
class WhisperSyncConfig:
    """Main application configuration.
    
    WHY MAIN CONFIG:
    - Combines all configuration sections into single interface
    - Provides environment-specific factory methods
    - Enables configuration validation and testing
    - Supports configuration serialization and debugging
    """
    
    environment: Environment = field(default=Environment.DEVELOPMENT)
    aws: AWSConfig = field(default_factory=AWSConfig)
    strands: StrandsConfig = field(default_factory=StrandsConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    agents: AgentConfig = field(default_factory=AgentConfig)
    
    @classmethod
    def from_environment(cls, env: Optional[str] = None) -> WhisperSyncConfig:
        """Create configuration from environment variables.
        
        Args:
            env: Environment name override (development, testing, staging, production)
            
        Returns:
            Configuration instance with environment-specific values
            
        WHY ENVIRONMENT FACTORY:
        - Enables different configurations for different deployment environments
        - Supports environment variable overrides for sensitive values
        - Provides sensible defaults while allowing customization
        - Centralizes environment detection logic
        """
        # Determine environment
        env_name = env or os.environ.get("WHISPERSYNC_ENV", "development")
        try:
            environment = Environment(env_name.lower())
        except ValueError:
            logger.warning(f"Unknown environment '{env_name}', using development")
            environment = Environment.DEVELOPMENT
        
        # AWS configuration from environment
        aws_config = AWSConfig(
            region=os.environ.get("AWS_REGION", "us-east-1"),
            bucket_name=os.environ.get("TRANSCRIPT_BUCKET_NAME", os.environ.get("BUCKET_NAME", "macbook-transcriptions")),
            lambda_timeout=int(os.environ.get("LAMBDA_TIMEOUT", "300")),
            lambda_memory=int(os.environ.get("LAMBDA_MEMORY", "512")),
            enable_xray=os.environ.get("ENABLE_XRAY", "false").lower() == "true",
            bedrock_model=os.environ.get(
                "BEDROCK_MODEL", 
                "anthropic.claude-3-5-sonnet-20241022-v2:0"
            ),
            max_tokens=int(os.environ.get("MAX_TOKENS", "2000")),
        )
        
        # Strands configuration from environment
        strands_config = StrandsConfig(
            enabled=os.environ.get("STRANDS_ENABLED", "false").lower() == "true",
            use_mocks=os.environ.get("STRANDS_USE_MOCKS", "true").lower() == "true",
            endpoint=os.environ.get("STRANDS_ENDPOINT"),
            api_key=os.environ.get("STRANDS_API_KEY"),
        )
        
        # Security configuration from environment
        security_config = SecurityConfig(
            github_secret_name=os.environ.get("GITHUB_SECRET_NAME", "github/personal_token"),
            enable_s3_encryption=os.environ.get("ENABLE_S3_ENCRYPTION", "true").lower() == "true",
            require_tls=os.environ.get("REQUIRE_TLS", "true").lower() == "true",
        )
        
        # Monitoring configuration from environment
        log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
        try:
            log_level = LogLevel(log_level_str)
        except ValueError:
            log_level = LogLevel.INFO
            
        monitoring_config = MonitoringConfig(
            log_level=log_level,
            enable_custom_metrics=os.environ.get("ENABLE_METRICS", "true").lower() == "true",
            enable_opentelemetry=os.environ.get("ENABLE_OTEL", "true").lower() == "true",
        )
        
        # Agent configuration from environment
        agent_config = AgentConfig(
            min_routing_confidence=float(os.environ.get("MIN_ROUTING_CONFIDENCE", "0.6")),
            enable_multi_agent_routing=os.environ.get("ENABLE_MULTI_AGENT", "true").lower() == "true",
        )
        
        # Environment-specific overrides
        if environment == Environment.PRODUCTION:
            monitoring_config.log_level = LogLevel.WARNING
            monitoring_config.enable_xray = True
            aws_config.enable_xray = True
            security_config.require_tls = True
        elif environment == Environment.TESTING:
            strands_config.use_mocks = True
            monitoring_config.log_level = LogLevel.DEBUG
            aws_config.lambda_timeout = 60  # Shorter for tests
        
        return cls(
            environment=environment,
            aws=aws_config,
            strands=strands_config,
            security=security_config,
            monitoring=monitoring_config,
            agents=agent_config
        )
    
    @classmethod
    def for_testing(cls) -> WhisperSyncConfig:
        """Create configuration optimized for testing.
        
        Returns:
            Configuration instance with testing-friendly values
        """
        config = cls.from_environment("testing")
        
        # Override for testing
        config.strands.use_mocks = True
        config.aws.bucket_name = "test-bucket"
        config.monitoring.log_level = LogLevel.DEBUG
        config.agents.max_processing_time = 10  # Faster tests
        
        return config
    
    def validate(self) -> List[str]:
        """Validate the complete configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Validate AWS configuration
        try:
            # Triggers __post_init__ validation
            AWSConfig(**self.aws.__dict__)
        except ValueError as e:
            errors.append(f"AWS config: {e}")
        
        # Validate Strands configuration
        try:
            StrandsConfig(**self.strands.__dict__)
        except ValueError as e:
            errors.append(f"Strands config: {e}")
        
        # Validate Security configuration
        try:
            SecurityConfig(**self.security.__dict__)
        except ValueError as e:
            errors.append(f"Security config: {e}")
        
        # Validate Monitoring configuration
        try:
            MonitoringConfig(**self.monitoring.__dict__)
        except ValueError as e:
            errors.append(f"Monitoring config: {e}")
            
        # Validate Agent configuration
        try:
            AgentConfig(**self.agents.__dict__)
        except ValueError as e:
            errors.append(f"Agent config: {e}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Union[str, int, float, bool]]:
        """Convert configuration to dictionary for serialization.
        
        Returns:
            Flattened configuration dictionary
        """
        result = {"environment": self.environment.value}
        
        # Flatten nested configurations with prefixes
        for key, value in self.aws.__dict__.items():
            result[f"aws_{key}"] = value
        for key, value in self.strands.__dict__.items():
            result[f"strands_{key}"] = value
        for key, value in self.security.__dict__.items():
            result[f"security_{key}"] = value
        for key, value in self.monitoring.__dict__.items():
            if isinstance(value, Enum):
                result[f"monitoring_{key}"] = value.value
            else:
                result[f"monitoring_{key}"] = value
        for key, value in self.agents.__dict__.items():
            result[f"agents_{key}"] = value
            
        return result


# Global configuration instance
_config: Optional[WhisperSyncConfig] = None


def get_config() -> WhisperSyncConfig:
    """Get the global configuration instance.
    
    Returns:
        Global configuration instance
        
    WHY GLOBAL INSTANCE:
    - Ensures consistent configuration across the application
    - Avoids re-parsing environment variables on every access
    - Provides single source of truth for configuration
    - Supports configuration caching for performance
    """
    global _config
    if _config is None:
        _config = WhisperSyncConfig.from_environment()
        
        # Validate configuration on first access
        errors = _config.validate()
        if errors:
            logger.error(f"Configuration validation errors: {errors}")
            raise ValueError(f"Invalid configuration: {'; '.join(errors)}")
        
        logger.info(f"Configuration loaded for environment: {_config.environment.value}")
    
    return _config


def set_config(config: WhisperSyncConfig) -> None:
    """Set the global configuration instance.
    
    Args:
        config: Configuration instance to use globally
        
    WHY SET CONFIG:
    - Enables configuration injection for testing
    - Supports dynamic configuration updates
    - Allows configuration overrides in special contexts
    - Provides clean interface for configuration management
    """
    global _config
    _config = config
    logger.info(f"Configuration updated for environment: {config.environment.value}")


def reset_config() -> None:
    """Reset configuration to force reload from environment.
    
    WHY RESET CONFIG:
    - Enables configuration refresh without restarting
    - Supports testing with different configurations
    - Allows hot configuration updates in development
    - Provides clean slate for configuration testing
    """
    global _config
    _config = None
    logger.info("Configuration reset - will reload from environment on next access")


# Export main configuration interface
__all__ = [
    "WhisperSyncConfig",
    "Environment", 
    "LogLevel",
    "get_config",
    "set_config", 
    "reset_config"
]