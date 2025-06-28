"""
WhisperSync Observability - Distributed Tracing and Monitoring

This module implements comprehensive observability for the voice memo processing pipeline
using OpenTelemetry standards for distributed tracing, metrics, and structured logging.

OBSERVABILITY STRATEGY:

1. Three Pillars of Observability:
   - WHY: Complete system visibility requires logs, metrics, and traces
   - LOGS: Structured events with correlation IDs for debugging
   - METRICS: Quantitative measurements for alerting and dashboards  
   - TRACES: Request flow across distributed components

2. OpenTelemetry Standard:
   - WHY: Vendor-neutral, future-proof observability instrumentation
   - HOW: OTLP export to any compatible backend (Jaeger, Zipkin, DataDog, etc.)

3. Automatic Instrumentation:
   - WHY: Reduces manual instrumentation effort, ensures consistency
   - AWS SDK: Automatic boto3 call tracing
   - Strands SDK: Agent execution tracing and metrics

ARCHITECTURAL DECISIONS:

1. Centralized Configuration:
   - WHY: Single source of truth for observability settings
   - Consistent telemetry across all components (Lambda, agents, local tools)

2. Graceful Degradation:
   - WHY: System continues functioning if observability fails
   - Import error handling, no-op fallbacks

3. Environment-Aware:
   - WHY: Different telemetry needs for dev/staging/production
   - Configurable sampling rates, endpoints, and retention

MONITORING PHILOSOPHY:

1. Golden Signals Focus:
   - Latency: Processing time for voice memos and agent actions
   - Traffic: Volume of transcripts processed
   - Errors: Failed agent executions and routing errors  
   - Saturation: Lambda concurrency and memory utilization

2. User Journey Tracking:
   - Voice memo → Transcript → Agent → Action completion
   - End-to-end visibility into the cognitive pipeline

COST CONSIDERATIONS:

1. Sampling Strategy: Balance observability depth with ingestion costs
2. Metric Aggregation: Pre-aggregate common queries to reduce storage
3. Retention Policies: Shorter retention for high-volume debug traces
4. Alert Optimization: Reduce noise, focus on actionable alerts
"""

import os
import logging
from typing import Optional, Dict, Any

# OpenTelemetry imports
try:
    from opentelemetry import trace, metrics
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    
    # Strands-specific instrumentation
    from strands.observability import init_observability as strands_init
    
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    
logger = logging.getLogger(__name__)


class WhisperSyncObservability:
    """Manages observability for WhisperSync components."""
    
    def __init__(
        self,
        service_name: str = "whispersync",
        environment: str = None,
        otlp_endpoint: str = None,
        enable_tracing: bool = True,
        enable_metrics: bool = True,
        enable_logging: bool = True
    ):
        """Initialize observability configuration.
        
        Args:
            service_name: Name of the service for identification
            environment: Deployment environment (dev, staging, prod)
            otlp_endpoint: OTLP endpoint for exporting telemetry
            enable_tracing: Whether to enable distributed tracing
            enable_metrics: Whether to enable metrics collection
            enable_logging: Whether to enable structured logging
        """
        self.service_name = service_name
        self.environment = environment or os.environ.get("ENVIRONMENT", "dev")
        self.otlp_endpoint = otlp_endpoint or os.environ.get(
            "OTEL_EXPORTER_OTLP_ENDPOINT", 
            "http://localhost:4317"
        )
        
        self.enable_tracing = enable_tracing
        self.enable_metrics = enable_metrics
        self.enable_logging = enable_logging
        
        self.tracer = None
        self.meter = None
        
        # Initialize if OpenTelemetry is available
        if OTEL_AVAILABLE:
            self._initialize()
        else:
            logger.warning("OpenTelemetry not available; observability disabled")
    
    def _initialize(self):
        """Initialize OpenTelemetry components."""
        # Create resource with service information
        resource = Resource.create({
            "service.name": self.service_name,
            "service.version": "1.0.0",
            "deployment.environment": self.environment,
            "service.instance.id": os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "local")
        })
        
        # Initialize tracing
        if self.enable_tracing:
            self._init_tracing(resource)
        
        # Initialize metrics
        if self.enable_metrics:
            self._init_metrics(resource)
        
        # Initialize logging instrumentation
        if self.enable_logging:
            self._init_logging()
        
        # Initialize AWS instrumentation
        self._init_aws_instrumentation()
        
        # Initialize Strands-specific observability
        self._init_strands_observability()
    
    def _init_tracing(self, resource: Resource):
        """Initialize distributed tracing."""
        # Create tracer provider
        provider = TracerProvider(resource=resource)
        
        # Add OTLP exporter
        exporter = OTLPSpanExporter(
            endpoint=self.otlp_endpoint,
            insecure=True  # Use insecure for local development
        )
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(provider)
        
        # Get tracer for this module
        self.tracer = trace.get_tracer(__name__)
        
        logger.info(f"Tracing initialized with endpoint: {self.otlp_endpoint}")
    
    def _init_metrics(self, resource: Resource):
        """Initialize metrics collection."""
        # Create metric reader and provider
        reader = PeriodicExportingMetricReader(
            exporter=OTLPMetricExporter(
                endpoint=self.otlp_endpoint,
                insecure=True
            ),
            export_interval_millis=60000  # Export every minute
        )
        
        provider = MeterProvider(
            resource=resource,
            metric_readers=[reader]
        )
        
        # Set global meter provider
        metrics.set_meter_provider(provider)
        
        # Get meter for this module
        self.meter = metrics.get_meter(__name__)
        
        # Create common metrics
        self._create_metrics()
        
        logger.info("Metrics initialized")
    
    def _init_logging(self):
        """Initialize structured logging with OpenTelemetry."""
        LoggingInstrumentor().instrument()
        
        # Configure structured logging format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - '
            '[%(otelTraceID)s-%(otelSpanID)s] - %(message)s'
        )
        
        # Update root logger
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logging.root.handlers = [handler]
        
        logger.info("Structured logging initialized")
    
    def _init_aws_instrumentation(self):
        """Initialize AWS SDK instrumentation."""
        # Instrument boto3/botocore for automatic tracing
        BotocoreInstrumentor().instrument()
        logger.info("AWS SDK instrumentation enabled")
    
    def _init_strands_observability(self):
        """Initialize Strands-specific observability."""
        if strands_init:
            strands_init(
                service_name=f"{self.service_name}-agents",
                otlp_endpoint=self.otlp_endpoint
            )
            logger.info("Strands observability initialized")
    
    def _create_metrics(self):
        """Create application-specific metrics."""
        if not self.meter:
            return
        
        # Transcript processing metrics
        self.transcript_counter = self.meter.create_counter(
            "whispersync.transcripts.processed",
            description="Number of transcripts processed",
            unit="1"
        )
        
        self.transcript_duration = self.meter.create_histogram(
            "whispersync.transcript.duration",
            description="Duration of transcript processing",
            unit="ms"
        )
        
        # Agent routing metrics
        self.routing_counter = self.meter.create_counter(
            "whispersync.routing.decisions",
            description="Number of routing decisions made",
            unit="1"
        )
        
        self.routing_confidence = self.meter.create_histogram(
            "whispersync.routing.confidence",
            description="Confidence scores for routing decisions",
            unit="1"
        )
        
        # Agent execution metrics
        self.agent_counter = self.meter.create_counter(
            "whispersync.agents.executions",
            description="Number of agent executions",
            unit="1"
        )
        
        self.agent_duration = self.meter.create_histogram(
            "whispersync.agents.duration",
            description="Duration of agent executions",
            unit="ms"
        )
        
        # Error metrics
        self.error_counter = self.meter.create_counter(
            "whispersync.errors",
            description="Number of errors encountered",
            unit="1"
        )
    
    def create_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Create a new span for tracing.
        
        Args:
            name: Name of the span
            attributes: Optional attributes to add to the span
            
        Returns:
            Span context manager
        """
        if not self.tracer:
            # Return a no-op context manager
            class NoOpSpan:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
                def set_attribute(self, key, value):
                    pass
                def add_event(self, name, attributes=None):
                    pass
            return NoOpSpan()
        
        span = self.tracer.start_as_current_span(name)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        return span
    
    def record_transcript_processed(
        self, 
        agent_type: str, 
        success: bool, 
        duration_ms: float,
        confidence: Optional[float] = None
    ):
        """Record metrics for a processed transcript.
        
        Args:
            agent_type: Type of agent that processed the transcript
            success: Whether processing was successful
            duration_ms: Processing duration in milliseconds
            confidence: Routing confidence score
        """
        if not self.meter:
            return
        
        # Common attributes
        attributes = {
            "agent.type": agent_type,
            "success": str(success),
            "environment": self.environment
        }
        
        # Record transcript counter
        self.transcript_counter.add(1, attributes)
        
        # Record duration
        self.transcript_duration.record(duration_ms, attributes)
        
        # Record routing confidence if provided
        if confidence is not None:
            self.routing_confidence.record(confidence, attributes)
    
    def record_agent_execution(
        self,
        agent_name: str,
        tool_name: str,
        duration_ms: float,
        success: bool
    ):
        """Record metrics for agent execution.
        
        Args:
            agent_name: Name of the agent
            tool_name: Name of the tool executed
            duration_ms: Execution duration in milliseconds
            success: Whether execution was successful
        """
        if not self.meter:
            return
        
        attributes = {
            "agent.name": agent_name,
            "tool.name": tool_name,
            "success": str(success),
            "environment": self.environment
        }
        
        self.agent_counter.add(1, attributes)
        self.agent_duration.record(duration_ms, attributes)
    
    def record_error(self, error_type: str, agent: Optional[str] = None):
        """Record an error occurrence.
        
        Args:
            error_type: Type of error
            agent: Optional agent where error occurred
        """
        if not self.meter:
            return
        
        attributes = {
            "error.type": error_type,
            "environment": self.environment
        }
        
        if agent:
            attributes["agent.name"] = agent
        
        self.error_counter.add(1, attributes)


# Global observability instance
_observability: Optional[WhisperSyncObservability] = None


def init_observability(
    service_name: str = "whispersync",
    environment: Optional[str] = None,
    otlp_endpoint: Optional[str] = None
) -> WhisperSyncObservability:
    """Initialize global observability.
    
    Args:
        service_name: Name of the service
        environment: Deployment environment
        otlp_endpoint: OTLP endpoint for telemetry export
        
    Returns:
        WhisperSyncObservability instance
    """
    global _observability
    
    _observability = WhisperSyncObservability(
        service_name=service_name,
        environment=environment,
        otlp_endpoint=otlp_endpoint
    )
    
    return _observability


def get_observability() -> Optional[WhisperSyncObservability]:
    """Get the global observability instance.
    
    Returns:
        WhisperSyncObservability instance or None
    """
    return _observability


def trace_agent_execution(agent_name: str, tool_name: str):
    """Decorator for tracing agent tool execution.
    
    Args:
        agent_name: Name of the agent
        tool_name: Name of the tool
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            obs = get_observability()
            if not obs:
                return func(*args, **kwargs)
            
            import time
            start_time = time.time()
            
            with obs.create_span(
                f"{agent_name}.{tool_name}",
                attributes={
                    "agent.name": agent_name,
                    "tool.name": tool_name
                }
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    
                    obs.record_agent_execution(
                        agent_name=agent_name,
                        tool_name=tool_name,
                        duration_ms=duration_ms,
                        success=True
                    )
                    
                    return result
                    
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    obs.record_agent_execution(
                        agent_name=agent_name,
                        tool_name=tool_name,
                        duration_ms=duration_ms,
                        success=False
                    )
                    
                    obs.record_error(
                        error_type=type(e).__name__,
                        agent=agent_name
                    )
                    
                    span.set_attribute("error", True)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    
                    raise
        
        return wrapper
    return decorator