"""Shared utilities for WhisperSync agents.

This module provides common functionality used across all agents to reduce code
duplication and ensure consistency. It follows the DRY (Don't Repeat Yourself)
principle and provides tested, reusable components.

WHY SHARED UTILITIES:
- Eliminates code duplication across agents
- Ensures consistent behavior and error handling
- Centralizes common patterns for maintenance
- Provides tested building blocks for agent development
- Enables unified logging and monitoring

DESIGN PRINCIPLES:
- Pure functions where possible for testability
- Clear error handling with proper exception types
- Comprehensive type hints for IDE support
- Detailed docstrings with examples
- Performance-optimized implementations
"""

from __future__ import annotations

import re
import json
import hashlib
import datetime
import logging
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import urllib.parse

from .config import get_config

logger = logging.getLogger(__name__)


@dataclass
class ProcessingMetrics:
    """Metrics for agent processing operations.
    
    WHY STRUCTURED METRICS:
    - Consistent metric collection across all agents
    - Type safety for metric data
    - Easy serialization for monitoring systems
    - Clear metric definitions and units
    """
    
    agent_type: str
    processing_time_ms: float
    transcript_length: int
    confidence_score: float
    tokens_used: int = 0
    api_calls_made: int = 0
    success: bool = True
    error_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class AgentResult:
    """Standardized result structure for all agents.
    
    WHY STANDARDIZED RESULTS:
    - Consistent API across all agents
    - Type safety for result handling
    - Clear success/failure indication
    - Metadata for debugging and monitoring
    """
    
    status: str  # 'success', 'failure', 'partial'
    data: Dict[str, Any]
    metrics: ProcessingMetrics
    timestamp: str
    agent_type: str
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            'status': self.status,
            'data': self.data,
            'metrics': self.metrics.to_dict(),
            'timestamp': self.timestamp,
            'agent_type': self.agent_type,
            'correlation_id': self.correlation_id
        }
    
    def is_success(self) -> bool:
        """Check if the result indicates success."""
        return self.status == 'success'


class TextAnalyzer:
    """Advanced text analysis utilities for transcript processing.
    
    WHY CENTRALIZED TEXT ANALYSIS:
    - Consistent text processing across all agents
    - Optimized algorithms for common operations
    - Extensible framework for new analysis types
    - Cached results for performance
    """
    
    def __init__(self):
        """Initialize text analyzer with cached patterns."""
        # Compile regex patterns once for performance
        self.sentence_pattern = re.compile(r'[.!?]+')
        self.word_pattern = re.compile(r'\b\w+\b')
        self.time_pattern = re.compile(r'\b\d{1,2}:\d{2}\b')
        self.url_pattern = re.compile(r'https?://\S+')
        
        # Keywords for different analysis types
        self.emotion_keywords = {
            'positive': ['happy', 'excited', 'love', 'amazing', 'wonderful', 'great', 'fantastic'],
            'negative': ['sad', 'angry', 'frustrated', 'terrible', 'awful', 'hate', 'worried'],
            'neutral': ['okay', 'fine', 'normal', 'regular', 'standard', 'typical']
        }
        
        self.technical_keywords = {
            'programming': ['code', 'bug', 'api', 'database', 'function', 'variable', 'algorithm'],
            'business': ['meeting', 'project', 'deadline', 'client', 'revenue', 'strategy'],
            'creative': ['design', 'art', 'music', 'story', 'creative', 'inspiration']
        }
    
    def extract_sentences(self, text: str) -> List[str]:
        """Extract individual sentences from text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of cleaned sentences
            
        Example:
            >>> analyzer = TextAnalyzer()
            >>> sentences = analyzer.extract_sentences("Hello world. How are you?")
            >>> print(sentences)
            ['Hello world', 'How are you']
        """
        sentences = self.sentence_pattern.split(text)
        return [s.strip() for s in sentences if s.strip()]
    
    def extract_keywords(self, text: str, min_length: int = 3) -> List[str]:
        """Extract meaningful keywords from text.
        
        Args:
            text: Input text to analyze
            min_length: Minimum word length to consider
            
        Returns:
            List of extracted keywords
        """
        words = self.word_pattern.findall(text.lower())
        
        # Filter out common stop words
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'among', 'this', 'that', 'these',
            'those', 'is', 'was', 'are', 'were', 'be', 'been', 'being', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'
        }
        
        keywords = [word for word in words 
                   if len(word) >= min_length and word not in stop_words]
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(keywords))
    
    def analyze_sentiment(self, text: str) -> Tuple[str, float]:
        """Analyze emotional sentiment of text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Tuple of (sentiment_label, confidence_score)
        """
        text_lower = text.lower()
        
        pos_count = sum(1 for word in self.emotion_keywords['positive'] 
                       if word in text_lower)
        neg_count = sum(1 for word in self.emotion_keywords['negative'] 
                       if word in text_lower)
        
        total_emotional_words = pos_count + neg_count
        
        if total_emotional_words == 0:
            return 'neutral', 0.5
        
        if pos_count > neg_count:
            confidence = pos_count / total_emotional_words
            return 'positive', confidence
        elif neg_count > pos_count:
            confidence = neg_count / total_emotional_words
            return 'negative', confidence
        else:
            return 'neutral', 0.5
    
    def extract_topics(self, text: str) -> Dict[str, float]:
        """Extract topic scores from text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary mapping topics to relevance scores
        """
        text_lower = text.lower()
        topic_scores = {}
        
        for topic, keywords in self.technical_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                # Normalize by text length
                topic_scores[topic] = score / len(text.split())
        
        return topic_scores
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary mapping entity types to extracted entities
        """
        entities = {
            'times': self.time_pattern.findall(text),
            'urls': self.url_pattern.findall(text),
            'people': self._extract_people_names(text),
            'technologies': self._extract_technologies(text)
        }
        
        return {k: v for k, v in entities.items() if v}
    
    def _extract_people_names(self, text: str) -> List[str]:
        """Extract potential people names from text."""
        # Simple heuristic - capitalized words that could be names
        words = text.split()
        potential_names = []
        
        common_names = [
            'john', 'jane', 'mike', 'sarah', 'david', 'mary', 'chris', 'lisa',
            'dad', 'mom', 'father', 'mother', 'brother', 'sister', 'friend'
        ]
        
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word.lower())
            if clean_word in common_names:
                potential_names.append(word)
        
        return potential_names
    
    def _extract_technologies(self, text: str) -> List[str]:
        """Extract technology mentions from text."""
        tech_keywords = [
            'python', 'javascript', 'react', 'vue', 'angular', 'node', 'django',
            'flask', 'aws', 'azure', 'docker', 'kubernetes', 'mongodb', 'postgresql',
            'mysql', 'redis', 'elasticsearch', 'tensorflow', 'pytorch'
        ]
        
        text_lower = text.lower()
        found_tech = [tech for tech in tech_keywords if tech in text_lower]
        return found_tech


class S3KeyGenerator:
    """Utility for generating consistent S3 key patterns.
    
    WHY CENTRALIZED KEY GENERATION:
    - Consistent naming conventions across all agents
    - Easy to change patterns globally
    - URL-safe and filesystem-safe naming
    - Support for partitioning and organization
    """
    
    @staticmethod
    def generate_transcript_key(
        agent_type: str, 
        timestamp: Optional[datetime.datetime] = None
    ) -> str:
        """Generate S3 key for input transcript.
        
        Args:
            agent_type: Type of agent (work, memory, github)
            timestamp: Timestamp for the transcript
            
        Returns:
            S3 key in format: transcripts/{agent_type}/{date}/{timestamp}.txt
        """
        if timestamp is None:
            timestamp = datetime.datetime.utcnow()
        
        date_path = timestamp.strftime('%Y/%m/%d')
        timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')
        
        return f'transcripts/{agent_type}/{date_path}/{timestamp_str}.txt'
    
    @staticmethod
    def generate_output_key(
        agent_type: str,
        operation: str = 'response',
        timestamp: Optional[datetime.datetime] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Generate S3 key for agent output.
        
        Args:
            agent_type: Type of agent (work, memory, github)
            operation: Type of operation (response, summary, analysis)
            timestamp: Timestamp for the output
            correlation_id: Optional correlation ID for tracking
            
        Returns:
            S3 key in format: outputs/{agent_type}/{date}/{operation}_{timestamp}.json
        """
        if timestamp is None:
            timestamp = datetime.datetime.utcnow()
        
        date_path = timestamp.strftime('%Y/%m/%d')
        timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')
        
        filename = f'{operation}_{timestamp_str}'
        if correlation_id:
            # Use first 8 chars of correlation ID for brevity
            filename += f'_{correlation_id[:8]}'
        filename += '.json'
        
        return f'outputs/{agent_type}/{date_path}/{filename}'
    
    @staticmethod
    def generate_log_key(
        agent_type: str,
        log_type: str = 'weekly',
        timestamp: Optional[datetime.datetime] = None
    ) -> str:
        """Generate S3 key for agent logs.
        
        Args:
            agent_type: Type of agent
            log_type: Type of log (weekly, daily, monthly)
            timestamp: Timestamp for the log
            
        Returns:
            S3 key for log storage
        """
        if timestamp is None:
            timestamp = datetime.datetime.utcnow()
        
        if log_type == 'weekly':
            year, week, _ = timestamp.isocalendar()
            return f'{agent_type}/weekly_logs/{year}-W{week:02d}.md'
        elif log_type == 'daily':
            date_str = timestamp.strftime('%Y-%m-%d')
            return f'{agent_type}/daily_logs/{date_str}.jsonl'
        elif log_type == 'monthly':
            month_str = timestamp.strftime('%Y-%m')
            return f'{agent_type}/monthly_logs/{month_str}.md'
        else:
            raise ValueError(f'Unsupported log type: {log_type}')


class RetryMechanism:
    """Intelligent retry mechanism for agent operations.
    
    WHY CENTRALIZED RETRY LOGIC:
    - Consistent retry behavior across all agents
    - Exponential backoff for rate limiting
    - Circuit breaker pattern for failing services
    - Detailed retry metrics and logging
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ):
        """Initialize retry mechanism.
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries
            exponential_base: Exponential backoff multiplier
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def execute_with_retry(
        self,
        operation: Callable,
        *args,
        retryable_exceptions: Tuple = (Exception,),
        **kwargs
    ) -> Any:
        """Execute operation with retry logic.
        
        Args:
            operation: Function to execute
            *args: Arguments for the operation
            retryable_exceptions: Exception types that should trigger retry
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Result of the operation
            
        Raises:
            Last exception if all retries fail
        """
        import time
        
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                return operation(*args, **kwargs)
            except retryable_exceptions as e:
                last_exception = e
                
                if attempt == self.max_attempts - 1:
                    # Last attempt failed, re-raise
                    logger.error(
                        f'Operation failed after {self.max_attempts} attempts: {e}'
                    )
                    raise e
                
                # Calculate delay with exponential backoff
                delay = min(
                    self.base_delay * (self.exponential_base ** attempt),
                    self.max_delay
                )
                
                logger.warning(
                    f'Operation failed (attempt {attempt + 1}/{self.max_attempts}), '
                    f'retrying in {delay:.1f}s: {e}'
                )
                
                time.sleep(delay)
        
        # Should never reach here, but just in case
        raise last_exception


class ValidationUtils:
    """Input validation utilities for agent operations.
    
    WHY CENTRALIZED VALIDATION:
    - Consistent validation logic across agents
    - Reusable validation patterns
    - Clear error messages for users
    - Security-focused input sanitization
    """
    
    @staticmethod
    def validate_transcript(transcript: str) -> Tuple[bool, Optional[str]]:
        """Validate transcript input.
        
        Args:
            transcript: Transcript text to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        config = get_config()
        
        if not transcript:
            return False, "Transcript cannot be empty"
        
        if not isinstance(transcript, str):
            return False, "Transcript must be a string"
        
        if len(transcript.strip()) < 10:
            return False, "Transcript too short (minimum 10 characters)"
        
        max_size = config.security.max_transcript_size
        if len(transcript.encode('utf-8')) > max_size:
            return False, f"Transcript too large (maximum {max_size} bytes)"
        
        # Check for suspicious content
        if ValidationUtils._contains_suspicious_content(transcript):
            return False, "Transcript contains suspicious content"
        
        return True, None
    
    @staticmethod
    def validate_agent_type(agent_type: str) -> Tuple[bool, Optional[str]]:
        """Validate agent type parameter.
        
        Args:
            agent_type: Agent type to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        valid_agents = {'work', 'memory', 'github', 'orchestrator'}
        
        if not agent_type:
            return False, "Agent type cannot be empty"
        
        if not isinstance(agent_type, str):
            return False, "Agent type must be a string"
        
        if agent_type.lower() not in valid_agents:
            return False, f"Invalid agent type. Must be one of: {valid_agents}"
        
        return True, None
    
    @staticmethod
    def validate_s3_key(s3_key: str) -> Tuple[bool, Optional[str]]:
        """Validate S3 key format.
        
        Args:
            s3_key: S3 key to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not s3_key:
            return False, "S3 key cannot be empty"
        
        if not isinstance(s3_key, str):
            return False, "S3 key must be a string"
        
        # Check for invalid characters
        invalid_chars = ['..', '//', '\\', '<', '>', ':', '"', '|', '?', '*']
        if any(char in s3_key for char in invalid_chars):
            return False, "S3 key contains invalid characters"
        
        if len(s3_key) > 1024:
            return False, "S3 key too long (maximum 1024 characters)"
        
        return True, None
    
    @staticmethod
    def _contains_suspicious_content(text: str) -> bool:
        """Check for suspicious content in text."""
        # Simple heuristics for suspicious content
        suspicious_patterns = [
            r'<script[^>]*>',  # Script tags
            r'javascript:',     # JavaScript protocol
            r'data:text/html',  # Data URLs
            r'eval\s*\(',      # Eval function calls
        ]
        
        text_lower = text.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False


class PerformanceMonitor:
    """Performance monitoring utilities for agent operations.
    
    WHY PERFORMANCE MONITORING:
    - Track operation latency and throughput
    - Identify performance bottlenecks
    - Support capacity planning
    - Enable performance-based alerting
    """
    
    def __init__(self, operation_name: str):
        """Initialize performance monitor.
        
        Args:
            operation_name: Name of the operation being monitored
        """
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None
        self.metrics = {}
    
    def __enter__(self):
        """Start monitoring operation."""
        import time
        self.start_time = time.time()
        logger.debug(f'Starting performance monitoring for {self.operation_name}')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End monitoring and log results."""
        import time
        self.end_time = time.time()
        
        duration = self.end_time - self.start_time
        self.metrics['duration_seconds'] = duration
        self.metrics['success'] = exc_type is None
        
        if exc_type:
            self.metrics['error_type'] = exc_type.__name__
            logger.warning(
                f'Operation {self.operation_name} failed after {duration:.3f}s: {exc_val}'
            )
        else:
            logger.info(
                f'Operation {self.operation_name} completed in {duration:.3f}s'
            )
    
    def add_metric(self, name: str, value: Union[int, float, str]) -> None:
        """Add custom metric to monitoring data.
        
        Args:
            name: Metric name
            value: Metric value
        """
        self.metrics[name] = value
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics.
        
        Returns:
            Dictionary of collected metrics
        """
        return self.metrics.copy()


def generate_correlation_id() -> str:
    """Generate unique correlation ID for request tracing.
    
    Returns:
        Unique correlation ID string
    """
    import uuid
    return str(uuid.uuid4())


def hash_content(content: str, algorithm: str = 'sha256') -> str:
    """Generate hash of content for deduplication.
    
    Args:
        content: Content to hash
        algorithm: Hash algorithm to use
        
    Returns:
        Hex digest of content hash
    """
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(content.encode('utf-8'))
    return hash_obj.hexdigest()


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize filename for safe filesystem storage.
    
    Args:
        filename: Original filename
        max_length: Maximum filename length
        
    Returns:
        Sanitized filename safe for filesystem use
    """
    # Remove/replace unsafe characters
    safe_filename = re.sub(r'[^\w\-_.]', '_', filename)
    
    # Remove consecutive underscores
    safe_filename = re.sub(r'_+', '_', safe_filename)
    
    # Ensure it's not too long
    if len(safe_filename) > max_length:
        name, ext = os.path.splitext(safe_filename)
        safe_filename = name[:max_length - len(ext)] + ext
    
    return safe_filename


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Human-readable duration string
    """
    if seconds < 1:
        return f'{seconds * 1000:.0f}ms'
    elif seconds < 60:
        return f'{seconds:.1f}s'
    elif seconds < 3600:
        minutes = seconds / 60
        return f'{minutes:.1f}m'
    else:
        hours = seconds / 3600
        return f'{hours:.1f}h'


# Export public interface
__all__ = [
    'ProcessingMetrics',
    'AgentResult', 
    'TextAnalyzer',
    'S3KeyGenerator',
    'RetryMechanism',
    'ValidationUtils',
    'PerformanceMonitor',
    'generate_correlation_id',
    'hash_content',
    'sanitize_filename',
    'format_duration'
]