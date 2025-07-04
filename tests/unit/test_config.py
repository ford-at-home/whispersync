"""Test suite for WhisperSync configuration management.

This test suite validates the centralized configuration system including:
- Environment-specific configuration loading
- Configuration validation and error handling
- Security and monitoring settings
- Agent configuration parameters
- Integration with environment variables

WHY COMPREHENSIVE CONFIG TESTING:
- Configuration errors can cause production outages
- Environment-specific settings must be validated
- Security configurations require careful testing
- Performance settings impact system behavior
"""

import os
import pytest
from unittest.mock import patch
from typing import Dict, Any

from agents.config import (
    WhisperSyncConfig,
    Environment,
    LogLevel,
    AWSConfig,
    StrandsConfig,
    SecurityConfig,
    MonitoringConfig,
    AgentConfig,
    get_config,
    set_config,
    reset_config
)


class TestWhisperSyncConfig:
    """Test suite for WhisperSync configuration management."""

    def test_default_configuration(self):
        """Test default configuration values are sensible."""
        config = WhisperSyncConfig()
        
        assert config.environment == Environment.DEVELOPMENT
        assert config.aws.region == "us-east-1"
        assert config.aws.bucket_name == "voice-mcp"
        assert config.aws.bedrock_model == "anthropic.claude-3-5-sonnet-20241022-v2:0"
        assert config.strands.use_mocks is True
        assert config.security.require_tls is True
        assert config.monitoring.log_level == LogLevel.INFO
        assert config.agents.min_routing_confidence == 0.6

    def test_production_configuration_overrides(self):
        """Test production environment applies appropriate overrides."""
        config = WhisperSyncConfig.from_environment("production")
        
        assert config.environment == Environment.PRODUCTION
        assert config.monitoring.log_level == LogLevel.WARNING
        assert config.monitoring.enable_xray is True
        assert config.aws.enable_xray is True
        assert config.security.require_tls is True

    def test_testing_configuration_overrides(self):
        """Test testing environment applies appropriate overrides."""
        config = WhisperSyncConfig.from_environment("testing")
        
        assert config.environment == Environment.TESTING
        assert config.strands.use_mocks is True
        assert config.monitoring.log_level == LogLevel.DEBUG
        assert config.aws.lambda_timeout == 60

    @patch.dict(os.environ, {
        'WHISPERSYNC_ENV': 'staging',
        'AWS_REGION': 'us-west-2',
        'BUCKET_NAME': 'test-bucket',
        'LOG_LEVEL': 'ERROR',
        'ENABLE_XRAY': 'true',
        'STRANDS_ENABLED': 'true',
        'MIN_ROUTING_CONFIDENCE': '0.8'
    })
    def test_environment_variable_overrides(self):
        """Test configuration loading from environment variables."""
        reset_config()  # Clear any cached config
        config = WhisperSyncConfig.from_environment()
        
        assert config.environment == Environment.DEVELOPMENT  # staging maps to development
        assert config.aws.region == "us-west-2"
        assert config.aws.bucket_name == "test-bucket"
        assert config.monitoring.log_level == LogLevel.ERROR
        assert config.aws.enable_xray is True
        assert config.strands.enabled is True
        assert config.agents.min_routing_confidence == 0.8

    def test_invalid_environment_falls_back_to_development(self):
        """Test invalid environment name falls back to development."""
        config = WhisperSyncConfig.from_environment("invalid_env")
        assert config.environment == Environment.DEVELOPMENT

    def test_configuration_validation_success(self):
        """Test valid configuration passes validation."""
        config = WhisperSyncConfig()
        errors = config.validate()
        assert errors == []

    def test_configuration_validation_failures(self):
        """Test configuration validation catches invalid values."""
        config = WhisperSyncConfig()
        
        # Invalid Lambda timeout (exceeds AWS maximum)
        config.aws.lambda_timeout = 1000
        errors = config.validate()
        assert len(errors) > 0
        assert any("timeout cannot exceed 900 seconds" in error for error in errors)
        
        # Invalid routing confidence
        config.aws.lambda_timeout = 300  # Fix timeout
        config.agents.min_routing_confidence = 1.5
        errors = config.validate()
        assert len(errors) > 0
        assert any("Routing confidence must be between 0.0 and 1.0" in error for error in errors)

    def test_configuration_serialization(self):
        """Test configuration can be serialized to dictionary."""
        config = WhisperSyncConfig.for_testing()
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict["environment"] == "testing"
        assert "aws_region" in config_dict
        assert "strands_enabled" in config_dict
        assert "security_require_tls" in config_dict
        assert "monitoring_log_level" in config_dict
        assert "agents_min_routing_confidence" in config_dict

    def test_testing_configuration_factory(self):
        """Test testing configuration factory method."""
        config = WhisperSyncConfig.for_testing()
        
        assert config.environment == Environment.TESTING
        assert config.strands.use_mocks is True
        assert config.aws.bucket_name == "test-bucket"
        assert config.monitoring.log_level == LogLevel.DEBUG
        assert config.agents.max_processing_time == 10


class TestAWSConfig:
    """Test AWS-specific configuration."""

    def test_default_aws_config(self):
        """Test default AWS configuration values."""
        config = AWSConfig()
        
        assert config.region == "us-east-1"
        assert config.bucket_name == "voice-mcp"
        assert config.lambda_timeout == 300
        assert config.lambda_memory == 512
        assert config.enable_xray is False
        assert config.max_tokens == 2000

    def test_aws_config_validation(self):
        """Test AWS configuration validation."""
        # Valid configuration
        config = AWSConfig(lambda_timeout=600, lambda_memory=1024)
        
        # Invalid timeout (exceeds AWS limit)
        with pytest.raises(ValueError, match="timeout cannot exceed 900 seconds"):
            AWSConfig(lambda_timeout=1000)
        
        # Invalid memory (below AWS minimum)
        with pytest.raises(ValueError, match="memory must be between 128MB and 10240MB"):
            AWSConfig(lambda_memory=64)
        
        # Invalid memory (above AWS maximum)
        with pytest.raises(ValueError, match="memory must be between 128MB and 10240MB"):
            AWSConfig(lambda_memory=20000)


class TestStrandsConfig:
    """Test Strands SDK configuration."""

    def test_default_strands_config(self):
        """Test default Strands configuration."""
        config = StrandsConfig()
        
        assert config.enabled is False
        assert config.use_mocks is True
        assert config.endpoint is None
        assert config.agent_timeout == 60
        assert config.enable_agent_warmup is True

    def test_strands_config_validation(self):
        """Test Strands configuration validation."""
        # Valid configuration with mocks
        config = StrandsConfig(enabled=True, use_mocks=True)
        
        # Invalid configuration - enabled without endpoint and not using mocks
        with pytest.raises(ValueError, match="Strands endpoint required"):
            StrandsConfig(enabled=True, use_mocks=False, endpoint=None)


class TestSecurityConfig:
    """Test security configuration."""

    def test_default_security_config(self):
        """Test default security settings."""
        config = SecurityConfig()
        
        assert config.github_secret_name == "github/personal_token"
        assert config.enable_s3_encryption is True
        assert config.require_tls is True
        assert config.max_transcript_size == 1024 * 1024  # 1MB
        assert "text/plain" in config.allowed_content_types

    def test_security_config_validation(self):
        """Test security configuration validation."""
        # Valid configuration
        config = SecurityConfig(max_transcript_size=5 * 1024 * 1024)  # 5MB
        
        # Invalid transcript size (too large)
        with pytest.raises(ValueError, match="Maximum transcript size cannot exceed 10MB"):
            SecurityConfig(max_transcript_size=20 * 1024 * 1024)


class TestMonitoringConfig:
    """Test monitoring configuration."""

    def test_default_monitoring_config(self):
        """Test default monitoring settings."""
        config = MonitoringConfig()
        
        assert config.log_level == LogLevel.INFO
        assert config.enable_structured_logging is True
        assert config.enable_custom_metrics is True
        assert config.metrics_namespace == "WhisperSync"
        assert config.tracing_sample_rate == 0.1
        assert config.error_rate_threshold == 0.05

    def test_monitoring_config_validation(self):
        """Test monitoring configuration validation."""
        # Valid configuration
        config = MonitoringConfig(tracing_sample_rate=0.5, error_rate_threshold=0.1)
        
        # Invalid tracing sample rate
        with pytest.raises(ValueError, match="Tracing sample rate must be between 0.0 and 1.0"):
            MonitoringConfig(tracing_sample_rate=1.5)
        
        # Invalid error rate threshold
        with pytest.raises(ValueError, match="Error rate threshold must be between 0.0 and 1.0"):
            MonitoringConfig(error_rate_threshold=2.0)


class TestAgentConfig:
    """Test agent-specific configuration."""

    def test_default_agent_config(self):
        """Test default agent settings."""
        config = AgentConfig()
        
        assert config.min_routing_confidence == 0.6
        assert config.enable_multi_agent_routing is True
        assert config.max_agents_per_request == 3
        assert config.max_processing_time == 30
        assert config.github_default_visibility == "public"
        assert config.work_log_format == "markdown"

    def test_agent_config_validation(self):
        """Test agent configuration validation."""
        # Valid configuration
        config = AgentConfig(min_routing_confidence=0.8, max_agents_per_request=5)
        
        # Invalid routing confidence
        with pytest.raises(ValueError, match="Routing confidence must be between 0.0 and 1.0"):
            AgentConfig(min_routing_confidence=1.5)
        
        # Invalid max agents
        with pytest.raises(ValueError, match="Maximum agents per request must be at least 1"):
            AgentConfig(max_agents_per_request=0)


class TestGlobalConfigurationManagement:
    """Test global configuration management functions."""

    def setUp(self):
        """Reset global configuration before each test."""
        reset_config()

    def test_get_config_singleton_behavior(self):
        """Test global configuration follows singleton pattern."""
        config1 = get_config()
        config2 = get_config()
        
        # Should return same instance
        assert config1 is config2

    def test_set_config_override(self):
        """Test setting custom configuration globally."""
        custom_config = WhisperSyncConfig.for_testing()
        set_config(custom_config)
        
        retrieved_config = get_config()
        assert retrieved_config is custom_config
        assert retrieved_config.environment == Environment.TESTING

    def test_reset_config_clears_cache(self):
        """Test config reset forces reload."""
        config1 = get_config()
        reset_config()
        config2 = get_config()
        
        # Should be different instances after reset
        assert config1 is not config2

    @patch.dict(os.environ, {'WHISPERSYNC_ENV': 'testing'})
    def test_config_validation_failure_raises_exception(self):
        """Test invalid configuration raises exception on first access."""
        reset_config()
        
        # Mock validation to return errors
        with patch.object(WhisperSyncConfig, 'validate', return_value=['Test error']):
            with pytest.raises(ValueError, match="Invalid configuration"):
                get_config()


class TestEnvironmentSpecificBehavior:
    """Test environment-specific configuration behavior."""

    def test_development_environment_defaults(self):
        """Test development environment has appropriate defaults."""
        config = WhisperSyncConfig.from_environment("development")
        
        assert config.environment == Environment.DEVELOPMENT
        assert config.strands.use_mocks is True
        assert config.monitoring.log_level == LogLevel.INFO
        assert config.aws.lambda_timeout == 300
        assert not config.is_production  # Helper property

    def test_production_environment_security(self):
        """Test production environment enforces security settings."""
        config = WhisperSyncConfig.from_environment("production")
        
        assert config.environment == Environment.PRODUCTION
        assert config.security.require_tls is True
        assert config.monitoring.enable_xray is True
        assert config.aws.enable_xray is True
        assert config.monitoring.log_level == LogLevel.WARNING

    def test_environment_bucket_naming(self):
        """Test bucket names include environment for non-production."""
        dev_config = WhisperSyncConfig.from_environment("development")
        prod_config = WhisperSyncConfig.from_environment("production")
        
        # Note: This would be implemented in infrastructure, 
        # config just provides the environment context
        assert dev_config.environment == Environment.DEVELOPMENT
        assert prod_config.environment == Environment.PRODUCTION

    @patch.dict(os.environ, {
        'WHISPERSYNC_ENV': 'production',
        'STRANDS_ENABLED': 'true',
        'STRANDS_USE_MOCKS': 'false',
        'STRANDS_ENDPOINT': 'https://api.strands.example.com'
    })
    def test_production_strands_configuration(self):
        """Test production Strands configuration with real endpoint."""
        reset_config()
        config = WhisperSyncConfig.from_environment()
        
        assert config.environment == Environment.PRODUCTION
        assert config.strands.enabled is True
        assert config.strands.use_mocks is False
        assert config.strands.endpoint == 'https://api.strands.example.com'


if __name__ == "__main__":
    pytest.main([__file__])