"""Base Agent Module with Strands Integration and Fallback.

This module provides base functionality for all WhisperSync agents, including
Strands SDK integration with graceful fallback to mock implementations, shared
utilities, and common error handling patterns.

WHY BASE MODULE:
- Centralizes Strands SDK integration and fallback logic
- Provides common utilities used across all agents
- Standardizes error handling and logging patterns
- Enables consistent configuration management
- Supports testing with unified mock strategies

DESIGN PATTERNS:
- Strategy Pattern: Strands vs Mock implementations
- Factory Pattern: Client creation with optimization
- Template Pattern: Common agent initialization steps
- Observer Pattern: Centralized logging and monitoring
"""

from __future__ import annotations

import os
import time
import logging
from typing import Any, Dict, Optional, Union, Callable
from functools import wraps

# Import configuration system
from .config import get_config, WhisperSyncConfig

# Try to import real Strands SDK, fall back to mocks
try:
    from strands import Agent, tool
    from strands_tools import bedrock_knowledge_base_retrieve
    from strands_sdk import register_agent, invoke_agent
    STRANDS_AVAILABLE = True
except ImportError:
    from .strands_mock import (
        MockAgent as Agent, 
        tool,
        bedrock_knowledge_base_retrieve,
        register_agent,
        invoke_agent
    )
    STRANDS_AVAILABLE = False

# AWS SDK with configuration
try:
    import boto3
    from botocore.config import Config
    AWS_AVAILABLE = True
except ImportError:
    boto3 = None
    Config = None
    AWS_AVAILABLE = False

logger = logging.getLogger(__name__)


def requires_aws(func: Callable) -> Callable:
    """Decorator to ensure AWS services are available.
    
    WHY DECORATOR: Provides consistent error handling for AWS-dependent operations
    without repeating error checking logic in every function.
    
    Args:
        func: Function that requires AWS services
        
    Returns:
        Wrapped function with AWS availability checking
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not AWS_AVAILABLE:
            logger.error(f"AWS SDK not available for {func.__name__}")
            return {"error": "AWS services unavailable", "retry": False}
        return func(*args, **kwargs)
    
    wrapper._requires_aws = True
    return wrapper


def requires_strands(func: Callable) -> Callable:
    """Decorator to ensure Strands SDK is available.
    
    WHY DECORATOR: Enables graceful degradation when Strands SDK is unavailable
    while clearly marking functions that depend on it.
    
    Args:
        func: Function that requires Strands SDK
        
    Returns:
        Wrapped function with Strands availability checking
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        config = get_config()
        if not STRANDS_AVAILABLE and not config.strands.use_mocks:
            logger.error(f"Strands SDK not available for {func.__name__}")
            return {"error": "Strands services unavailable", "retry": False}
        return func(*args, **kwargs)
    
    wrapper._requires_strands = True
    return wrapper


def get_optimized_s3_client() -> Optional[Any]:
    """Get S3 client with optimized connection settings.
    
    WHY OPTIMIZED CLIENT:
    - Connection pooling improves performance for multiple requests
    - Retry configuration handles transient AWS failures gracefully
    - Regional optimization reduces latency
    - Connection reuse reduces Lambda cold start impact
    
    Returns:
        Configured S3 client or None if AWS unavailable
    """
    if not AWS_AVAILABLE:
        logger.warning("AWS SDK not available, S3 operations will fail")
        return None
    
    config = get_config()
    
    # Optimized connection configuration
    boto_config = Config(
        region_name=config.aws.region,
        retries={
            'max_attempts': config.aws.s3_retry_attempts,
            'mode': config.aws.s3_retry_mode
        },
        max_pool_connections=config.aws.s3_max_connections,
        connect_timeout=30,
        read_timeout=30,
    )
    
    return boto3.client('s3', config=boto_config)


def get_optimized_bedrock_client() -> Optional[Any]:
    """Get Bedrock client with optimized settings.
    
    WHY OPTIMIZED BEDROCK:
    - Timeout configuration prevents hanging requests
    - Retry logic handles model availability issues
    - Regional configuration optimizes latency
    - Connection reuse improves Lambda performance
    
    Returns:
        Configured Bedrock client or None if AWS unavailable
    """
    if not AWS_AVAILABLE:
        logger.warning("AWS SDK not available, Bedrock operations will fail")
        return None
    
    config = get_config()
    
    boto_config = Config(
        region_name=config.aws.region,
        retries={
            'max_attempts': 3,
            'mode': 'adaptive'
        },
        connect_timeout=config.aws.bedrock_timeout,
        read_timeout=config.aws.bedrock_timeout,
    )
    
    return boto3.client('bedrock-runtime', config=boto_config)


def get_secrets_manager_client() -> Optional[Any]:
    """Get Secrets Manager client for secure credential access.
    
    WHY SECRETS MANAGER:
    - Centralized secret storage with encryption at rest
    - Automatic secret rotation capabilities
    - Audit trail for secret access
    - Integration with IAM for access control
    
    Returns:
        Configured Secrets Manager client or None if AWS unavailable
    """
    if not AWS_AVAILABLE:
        logger.warning("AWS SDK not available, secrets access will fail")
        return None
    
    config = get_config()
    
    boto_config = Config(
        region_name=config.security.github_secret_region,
        retries={'max_attempts': 3, 'mode': 'adaptive'}
    )
    
    return boto3.client('secretsmanager', config=boto_config)


class BaseAgent:
    """Base class for all WhisperSync agents.
    
    WHY BASE CLASS:
    - Provides common initialization and configuration
    - Standardizes error handling across agents
    - Centralizes AWS client management
    - Enables consistent logging and monitoring
    - Supports unified testing strategies
    
    COMMON FUNCTIONALITY:
    - Configuration management
    - AWS client initialization with optimization
    - Error handling with retry logic
    - Logging with correlation IDs
    - Performance monitoring and metrics
    """
    
    def __init__(
        self, 
        bucket: Optional[str] = None,
        correlation_id: Optional[str] = None
    ):
        """Initialize base agent functionality.
        
        Args:
            bucket: S3 bucket name override
            correlation_id: Request correlation ID for tracing
        """
        self.config = get_config()
        self.bucket = bucket or self.config.aws.bucket_name
        self.correlation_id = correlation_id
        
        # Initialize AWS clients with optimization
        self.s3 = get_optimized_s3_client()
        self.bedrock = get_optimized_bedrock_client()
        self.secrets = get_secrets_manager_client()
        
        # Performance tracking
        self.start_time = time.time()
        
        logger.info(
            f"Base agent initialized: bucket={self.bucket}, "
            f"correlation_id={correlation_id}"
        )
    
    def get_processing_time(self) -> float:
        """Get processing time since agent initialization.
        
        Returns:
            Processing time in seconds
        """
        return time.time() - self.start_time
    
    @requires_aws
    def store_result(
        self, 
        result: Dict[str, Any], 
        output_key: str,
        content_type: str = "application/json"
    ) -> bool:
        """Store agent result to S3.
        
        Args:
            result: Result data to store
            output_key: S3 key for storage
            content_type: MIME type for the content
            
        Returns:
            True if successful, False otherwise
            
        WHY CENTRALIZED STORAGE:
        - Consistent error handling across agents
        - Standard metadata and tagging
        - Encryption and security policy application
        - Performance optimization with client reuse
        """
        try:
            import json
            
            # Add metadata to result
            enriched_result = {
                **result,
                "agent_metadata": {
                    "processing_time": self.get_processing_time(),
                    "correlation_id": self.correlation_id,
                    "timestamp": time.time(),
                    "bucket": self.bucket,
                    "agent_type": self.__class__.__name__
                }
            }
            
            # Store with encryption if enabled
            put_kwargs = {
                "Bucket": self.bucket,
                "Key": output_key,
                "Body": json.dumps(enriched_result, indent=2).encode("utf-8"),
                "ContentType": content_type
            }
            
            if self.config.security.enable_s3_encryption:
                put_kwargs["ServerSideEncryption"] = "AES256"
                if self.config.security.kms_key_id:
                    put_kwargs["SSEKMSKeyId"] = self.config.security.kms_key_id
            
            self.s3.put_object(**put_kwargs)
            
            logger.info(f"Result stored successfully: {output_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store result to {output_key}: {e}")
            return False
    
    @requires_aws
    def get_github_token(self) -> Optional[str]:
        """Retrieve GitHub token from AWS Secrets Manager.
        
        Returns:
            GitHub token or None if unavailable
            
        WHY SECRETS MANAGER:
        - Secure storage with encryption at rest
        - Automatic rotation capabilities
        - Audit trail for access
        - IAM-based access control
        """
        try:
            response = self.secrets.get_secret_value(
                SecretId=self.config.security.github_secret_name
            )
            return response["SecretString"]
            
        except Exception as e:
            logger.error(f"Failed to retrieve GitHub token: {e}")
            return None
    
    def emit_metric(self, metric_name: str, value: float, unit: str = "Count") -> None:
        """Emit custom CloudWatch metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Metric unit (Count, Seconds, etc.)
            
        WHY CUSTOM METRICS:
        - Business-specific monitoring beyond standard AWS metrics
        - Performance tracking and optimization insights
        - Usage pattern analysis
        - SLA compliance monitoring
        """
        if not AWS_AVAILABLE or not self.config.monitoring.enable_custom_metrics:
            return
        
        try:
            cloudwatch = boto3.client('cloudwatch')
            cloudwatch.put_metric_data(
                Namespace=self.config.monitoring.metrics_namespace,
                MetricData=[{
                    'MetricName': metric_name,
                    'Value': value,
                    'Unit': unit,
                    'Timestamp': time.time(),
                    'Dimensions': [
                        {
                            'Name': 'AgentType',
                            'Value': self.__class__.__name__
                        },
                        {
                            'Name': 'Environment', 
                            'Value': self.config.environment.value
                        }
                    ]
                }]
            )
        except Exception as e:
            logger.warning(f"Failed to emit metric {metric_name}: {e}")
    
    def handle_error(
        self, 
        error: Exception, 
        operation: str,
        retryable: bool = True
    ) -> Dict[str, Any]:
        """Standardized error handling across agents.
        
        Args:
            error: The exception that occurred
            operation: Description of the operation that failed
            retryable: Whether the operation can be retried
            
        Returns:
            Standardized error response
            
        WHY STANDARDIZED ERRORS:
        - Consistent error format across all agents
        - Proper error classification for retry logic
        - Detailed logging for debugging
        - Metrics emission for monitoring
        """
        error_response = {
            "error": str(error),
            "operation": operation,
            "retry": retryable,
            "timestamp": time.time(),
            "correlation_id": self.correlation_id,
            "agent_type": self.__class__.__name__
        }
        
        # Log with appropriate level based on error type
        if retryable:
            logger.warning(f"Retryable error in {operation}: {error}")
        else:
            logger.error(f"Non-retryable error in {operation}: {error}")
        
        # Emit error metric
        self.emit_metric("AgentErrors", 1.0)
        
        return error_response


class AgentError(Exception):
    """Base exception for agent-specific errors.
    
    WHY CUSTOM EXCEPTION:
    - Clear distinction between agent errors and system errors
    - Enables specific error handling strategies
    - Provides context for error classification
    - Supports error recovery logic
    """
    
    def __init__(self, message: str, retryable: bool = True, agent_type: str = None):
        super().__init__(message)
        self.retryable = retryable
        self.agent_type = agent_type


class ProcessingError(AgentError):
    """Error during agent processing operations."""
    pass


class ConfigurationError(AgentError):
    """Error in agent configuration or setup."""
    
    def __init__(self, message: str):
        super().__init__(message, retryable=False)


class ExternalServiceError(AgentError):
    """Error communicating with external services."""
    
    def __init__(self, message: str, service: str):
        super().__init__(message, retryable=True)
        self.service = service


# Utility functions for common operations
def validate_transcript(transcript: str) -> bool:
    """Validate transcript content meets requirements.
    
    Args:
        transcript: Transcript text to validate
        
    Returns:
        True if valid, False otherwise
        
    WHY VALIDATION:
    - Prevents processing of invalid or malicious content
    - Ensures transcript size limits are respected
    - Validates content encoding and format
    - Provides early error detection
    """
    config = get_config()
    
    if not transcript or not isinstance(transcript, str):
        return False
    
    if len(transcript.encode('utf-8')) > config.security.max_transcript_size:
        return False
    
    # Basic content validation
    if len(transcript.strip()) < 10:  # Minimum meaningful content
        return False
    
    return True


def generate_output_key(
    agent_type: str, 
    source_key: Optional[str] = None,
    timestamp: Optional[float] = None
) -> str:
    """Generate standardized output key for S3 storage.
    
    Args:
        agent_type: Type of agent (work, memory, github)
        source_key: Original S3 key for context
        timestamp: Timestamp for the output (defaults to current time)
        
    Returns:
        Standardized S3 key for output storage
        
    WHY STANDARDIZED KEYS:
    - Consistent organization of outputs
    - Easy discovery and filtering
    - Support for time-based partitioning
    - Integration with monitoring and analytics
    """
    if timestamp is None:
        timestamp = time.time()
    
    # Extract date for partitioning
    import datetime
    dt = datetime.datetime.fromtimestamp(timestamp)
    date_path = dt.strftime("%Y/%m/%d")
    
    # Generate unique filename
    if source_key:
        # Derive from source key
        source_name = source_key.split("/")[-1].replace(".txt", "")
        filename = f"{source_name}_response.json"
    else:
        # Generate timestamp-based name
        filename = f"{dt.strftime('%Y%m%d_%H%M%S')}_response.json"
    
    return f"outputs/{agent_type}/{date_path}/{filename}"


# Export public interface
__all__ = [
    "BaseAgent",
    "AgentError",
    "ProcessingError", 
    "ConfigurationError",
    "ExternalServiceError",
    "requires_aws",
    "requires_strands",
    "get_optimized_s3_client",
    "get_optimized_bedrock_client",
    "get_secrets_manager_client",
    "validate_transcript",
    "generate_output_key",
    "STRANDS_AVAILABLE",
    "AWS_AVAILABLE",
    "Agent",
    "tool"
]