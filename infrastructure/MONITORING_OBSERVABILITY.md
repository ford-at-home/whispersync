# WhisperSync Monitoring and Observability Plan

## Executive Summary

This document outlines a comprehensive monitoring and observability strategy for WhisperSync, enabling proactive issue detection, performance optimization, and operational excellence.

## Observability Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   User Experience                        │
│                  (Real User Monitoring)                  │
├─────────────────────────────────────────────────────────┤
│                Application Performance                   │
│              (X-Ray, Custom Metrics, Logs)              │
├─────────────────────────────────────────────────────────┤
│               Infrastructure Monitoring                  │
│           (CloudWatch, Health Checks, Alarms)           │
├─────────────────────────────────────────────────────────┤
│                 Security Monitoring                      │
│            (GuardDuty, CloudTrail, Config)             │
└─────────────────────────────────────────────────────────┘
```

## 1. Metrics Strategy

### Core Business Metrics

```python
# Voice Memo Processing Metrics
class BusinessMetrics:
    NAMESPACE = "WhisperSync/Business"
    
    @staticmethod
    def publish_transcript_processed(agent_type: str, success: bool):
        cloudwatch.put_metric_data(
            Namespace=BusinessMetrics.NAMESPACE,
            MetricData=[{
                "MetricName": "TranscriptsProcessed",
                "Value": 1,
                "Unit": "Count",
                "Dimensions": [
                    {"Name": "AgentType", "Value": agent_type},
                    {"Name": "Status", "Value": "Success" if success else "Failed"}
                ]
            }]
        )
    
    @staticmethod
    def publish_processing_time(agent_type: str, duration_ms: float):
        cloudwatch.put_metric_data(
            Namespace=BusinessMetrics.NAMESPACE,
            MetricData=[{
                "MetricName": "ProcessingDuration",
                "Value": duration_ms,
                "Unit": "Milliseconds",
                "Dimensions": [
                    {"Name": "AgentType", "Value": agent_type}
                ],
                "StatisticValues": {
                    "SampleCount": 1,
                    "Sum": duration_ms,
                    "Minimum": duration_ms,
                    "Maximum": duration_ms
                }
            }]
        )
```

### Technical Metrics

```python
# Lambda Performance Metrics
lambda_metrics = {
    "Invocations": lambda_fn.metric_invocations(),
    "Errors": lambda_fn.metric_errors(),
    "Duration": lambda_fn.metric_duration(),
    "Throttles": lambda_fn.metric_throttles(),
    "ConcurrentExecutions": lambda_fn.metric("ConcurrentExecutions"),
    "UnreservedConcurrentExecutions": lambda_fn.metric("UnreservedConcurrentExecutions")
}

# SQS Queue Metrics
queue_metrics = {
    "MessagesVisible": queue.metric_approximate_number_of_messages_visible(),
    "MessagesNotVisible": queue.metric_approximate_number_of_messages_not_visible(),
    "MessagesDelayed": queue.metric_approximate_number_of_messages_delayed(),
    "MessageAge": queue.metric("ApproximateAgeOfOldestMessage")
}

# DynamoDB Metrics
dynamodb_metrics = {
    "ConsumedReadCapacity": table.metric_consumed_read_capacity_units(),
    "ConsumedWriteCapacity": table.metric_consumed_write_capacity_units(),
    "UserErrors": table.metric_user_errors(),
    "SystemErrors": table.metric_system_errors()
}
```

## 2. Distributed Tracing

### AWS X-Ray Implementation

```python
# Enable X-Ray tracing
from aws_lambda_powertools import Tracer
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

tracer = Tracer()

@tracer.capture_lambda_handler
def lambda_handler(event, context):
    # Automatic tracing of Lambda execution
    
    # Custom subsegments for detailed tracing
    with tracer.provider.get_trace_entity().add_subsegment("transcript_download") as subsegment:
        transcript = download_from_s3(bucket, key)
        subsegment.put_metadata("transcript_length", len(transcript))
    
    with tracer.provider.get_trace_entity().add_subsegment("agent_processing") as subsegment:
        result = process_with_agent(transcript)
        subsegment.put_annotation("agent_type", agent_type)
        subsegment.put_annotation("success", result.success)
    
    return result

# Trace external calls
@xray_recorder.capture("eleven_labs_api")
def synthesize_voice(text: str) -> bytes:
    # API call automatically traced
    response = requests.post(
        "https://api.elevenlabs.io/v1/text-to-speech",
        headers={"xi-api-key": api_key},
        json={"text": text}
    )
    return response.content
```

### Correlation IDs

```python
# Implement correlation ID tracking
import uuid
from aws_lambda_powertools import Logger

logger = Logger()

class CorrelationContext:
    def __init__(self, event, context):
        # Extract or generate correlation ID
        self.correlation_id = (
            event.get("headers", {}).get("X-Correlation-ID") or
            event.get("Records", [{}])[0].get("messageAttributes", {})
            .get("correlationId", {}).get("stringValue") or
            str(uuid.uuid4())
        )
        
        # Add to logger context
        logger.append_keys(correlation_id=self.correlation_id)
        
        # Add to X-Ray annotations
        xray_recorder.put_annotation("correlation_id", self.correlation_id)
    
    def propagate_to_sqs(self, message):
        """Add correlation ID to SQS message attributes"""
        message["MessageAttributes"]["correlationId"] = {
            "StringValue": self.correlation_id,
            "DataType": "String"
        }
        return message
```

## 3. Logging Strategy

### Structured Logging

```python
# Use AWS Lambda Powertools for structured logging
from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging import correlation_paths

logger = Logger(service="whispersync")

@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.API_GATEWAY_REST,
    log_event=True  # Log incoming event
)
def lambda_handler(event, context):
    logger.info("Processing transcript", extra={
        "agent_type": agent_type,
        "transcript_key": key,
        "transcript_size": len(transcript),
        "request_id": context.request_id
    })
    
    try:
        result = process_transcript(transcript)
        logger.info("Processing successful", extra={
            "duration_ms": elapsed_time,
            "result_size": len(result)
        })
    except Exception as e:
        logger.exception("Processing failed", extra={
            "error_type": type(e).__name__,
            "agent_type": agent_type
        })
        raise
```

### Log Aggregation and Analysis

```python
# CloudWatch Insights queries
insights_queries = {
    "error_analysis": """
        fields @timestamp, @message, error_type, agent_type
        | filter @message like /ERROR/
        | stats count() by error_type, agent_type
        | sort count desc
    """,
    
    "performance_analysis": """
        fields @timestamp, duration_ms, agent_type
        | filter @message like /Processing successful/
        | stats avg(duration_ms), max(duration_ms), min(duration_ms) by agent_type
    """,
    
    "user_activity": """
        fields @timestamp, correlation_id, agent_type
        | filter @message like /Processing transcript/
        | stats count() by bin(5m) as time_bucket, agent_type
        | sort time_bucket desc
    """
}

# Create metric filters from logs
log_group.add_metric_filter(
    "ErrorMetricFilter",
    filter_pattern=logs.FilterPattern.literal("[ERROR]"),
    metric_name="LogErrors",
    metric_namespace="WhisperSync/Logs",
    metric_value="1"
)
```

## 4. Alerting Strategy

### Alert Hierarchy

```python
# Priority-based alerting
class AlertPriority:
    CRITICAL = "P1"  # Immediate response required
    HIGH = "P2"      # Response within 1 hour
    MEDIUM = "P3"    # Response within 4 hours
    LOW = "P4"       # Next business day

# Critical alerts
critical_alerts = [
    {
        "name": "SystemDown",
        "metric": lambda_fn.metric_errors(),
        "threshold": 10,
        "evaluation_periods": 1,
        "period": Duration.minutes(1),
        "priority": AlertPriority.CRITICAL
    },
    {
        "name": "DLQMessages",
        "metric": dlq.metric_approximate_number_of_messages_visible(),
        "threshold": 5,
        "evaluation_periods": 1,
        "period": Duration.minutes(5),
        "priority": AlertPriority.CRITICAL
    }
]

# Create composite alarms
composite_alarm = cloudwatch.CompositeAlarm(
    self, "SystemHealthAlarm",
    alarm_description="Overall system health degraded",
    composite_alarm_name=f"whispersync-system-health-{environment}",
    alarm_rule=cloudwatch.AlarmRule.any_of(
        cloudwatch.AlarmRule.from_alarm(lambda_error_alarm, cloudwatch.AlarmState.ALARM),
        cloudwatch.AlarmRule.from_alarm(dlq_alarm, cloudwatch.AlarmState.ALARM),
        cloudwatch.AlarmRule.from_alarm(api_5xx_alarm, cloudwatch.AlarmState.ALARM)
    )
)
```

### Alert Routing

```python
# SNS topics for different priorities
alert_topics = {
    AlertPriority.CRITICAL: sns.Topic(
        self, "CriticalAlerts",
        display_name="WhisperSync Critical Alerts"
    ),
    AlertPriority.HIGH: sns.Topic(
        self, "HighAlerts",
        display_name="WhisperSync High Priority Alerts"
    )
}

# Lambda for intelligent alert routing
alert_router = _lambda.Function(
    self, "AlertRouter",
    handler="alerts.route_alert",
    environment={
        "SLACK_CRITICAL_WEBHOOK": critical_webhook_secret.secret_arn,
        "SLACK_HIGH_WEBHOOK": high_webhook_secret.secret_arn,
        "PAGERDUTY_TOKEN": pagerduty_secret.secret_arn
    }
)

# Subscribe router to all alert topics
for priority, topic in alert_topics.items():
    topic.add_subscription(
        subscriptions.LambdaSubscription(alert_router)
    )
```

## 5. Performance Monitoring

### Lambda Performance Dashboard

```python
# Comprehensive Lambda dashboard
lambda_dashboard = cloudwatch.Dashboard(
    self, "LambdaPerformance",
    widgets=[
        [
            # Row 1: Overview metrics
            cloudwatch.GraphWidget(
                title="Invocation Rate",
                left=[lambda_fn.metric_invocations()],
                period=Duration.minutes(1)
            ),
            cloudwatch.GraphWidget(
                title="Error Rate",
                left=[lambda_fn.metric_errors()],
                left_y_axis={"label": "Errors", "showUnits": False},
                right=[
                    cloudwatch.MathExpression(
                        expression="errors/invocations*100",
                        using_metrics={
                            "errors": lambda_fn.metric_errors(),
                            "invocations": lambda_fn.metric_invocations()
                        },
                        label="Error %"
                    )
                ],
                right_y_axis={"label": "Error Percentage", "showUnits": False}
            )
        ],
        [
            # Row 2: Performance metrics
            cloudwatch.GraphWidget(
                title="Duration",
                left=[
                    lambda_fn.metric_duration(statistic="Average"),
                    lambda_fn.metric_duration(statistic="p99"),
                    lambda_fn.metric_duration(statistic="Maximum")
                ]
            ),
            cloudwatch.GraphWidget(
                title="Memory Utilization",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/Lambda",
                        metric_name="MemoryUtilization",
                        dimensions_map={
                            "FunctionName": lambda_fn.function_name
                        }
                    )
                ]
            )
        ]
    ]
)
```

### SQS Queue Monitoring

```python
# Queue health dashboard
queue_dashboard = cloudwatch.Dashboard(
    self, "QueueHealth",
    widgets=[
        [
            cloudwatch.GraphWidget(
                title="Queue Depth",
                left=[
                    queue.metric_approximate_number_of_messages_visible(),
                    queue.metric_approximate_number_of_messages_not_visible()
                ],
                statistic="Average"
            ),
            cloudwatch.GraphWidget(
                title="Message Age",
                left=[queue.metric("ApproximateAgeOfOldestMessage")],
                statistic="Maximum"
            )
        ],
        [
            cloudwatch.SingleValueWidget(
                title="Messages in DLQ",
                metrics=[dlq.metric_approximate_number_of_messages_visible()]
            ),
            cloudwatch.GraphWidget(
                title="Message Processing Rate",
                left=[
                    cloudwatch.MathExpression(
                        expression="RATE(sent)",
                        using_metrics={
                            "sent": queue.metric("NumberOfMessagesSent")
                        }
                    )
                ]
            )
        ]
    ]
)
```

## 6. Synthetic Monitoring

### Health Check Implementation

```python
# Synthetic health check Lambda
health_check_lambda = _lambda.Function(
    self, "SyntheticHealthCheck",
    handler="synthetic.health_check",
    environment={
        "TEST_BUCKET": test_bucket.bucket_name,
        "TEST_QUEUE": test_queue.queue_url,
        "ALERT_TOPIC": alert_topic.topic_arn
    }
)

# Schedule health checks
events.Rule(
    self, "HealthCheckSchedule",
    schedule=events.Schedule.rate(Duration.minutes(5)),
    targets=[targets.LambdaFunction(health_check_lambda)]
)

# Health check implementation
def health_check(event, context):
    health_results = {
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Check S3 accessibility
    try:
        s3.head_bucket(Bucket=TEST_BUCKET)
        health_results["checks"]["s3"] = {"status": "healthy"}
    except Exception as e:
        health_results["checks"]["s3"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check SQS
    try:
        sqs.get_queue_attributes(
            QueueUrl=TEST_QUEUE,
            AttributeNames=["ApproximateNumberOfMessages"]
        )
        health_results["checks"]["sqs"] = {"status": "healthy"}
    except Exception as e:
        health_results["checks"]["sqs"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check DynamoDB
    try:
        dynamodb.describe_table(TableName=TEST_TABLE)
        health_results["checks"]["dynamodb"] = {"status": "healthy"}
    except Exception as e:
        health_results["checks"]["dynamodb"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Determine overall health
    all_healthy = all(
        check["status"] == "healthy" 
        for check in health_results["checks"].values()
    )
    
    # Publish metrics
    cloudwatch.put_metric_data(
        Namespace="WhisperSync/Health",
        MetricData=[{
            "MetricName": "SystemHealth",
            "Value": 1 if all_healthy else 0,
            "Unit": "None"
        }]
    )
    
    return health_results
```

## 7. Cost Monitoring

### Cost Tracking Dashboard

```python
# Cost monitoring dashboard
cost_dashboard = cloudwatch.Dashboard(
    self, "CostMonitoring",
    widgets=[
        [
            cloudwatch.GraphWidget(
                title="Lambda Cost Estimate",
                left=[
                    cloudwatch.MathExpression(
                        expression="invocations * 0.0000002 + (duration/1000 * memory/1024) * 0.0000166667",
                        using_metrics={
                            "invocations": lambda_fn.metric_invocations(statistic="Sum"),
                            "duration": lambda_fn.metric_duration(statistic="Average"),
                            "memory": cloudwatch.Metric(
                                namespace="AWS/Lambda",
                                metric_name="MemorySize",
                                dimensions_map={"FunctionName": lambda_fn.function_name}
                            )
                        },
                        label="Estimated Cost ($)"
                    )
                ]
            )
        ],
        [
            cloudwatch.GraphWidget(
                title="S3 Request Costs",
                left=[
                    cloudwatch.MathExpression(
                        expression="(get * 0.0004 + put * 0.005) / 1000",
                        using_metrics={
                            "get": cloudwatch.Metric(
                                namespace="AWS/S3",
                                metric_name="NumberOfRequests",
                                dimensions_map={
                                    "BucketName": bucket.bucket_name,
                                    "RequestType": "GetRequests"
                                }
                            ),
                            "put": cloudwatch.Metric(
                                namespace="AWS/S3",
                                metric_name="NumberOfRequests",
                                dimensions_map={
                                    "BucketName": bucket.bucket_name,
                                    "RequestType": "PutRequests"
                                }
                            )
                        },
                        label="Estimated Cost ($)"
                    )
                ]
            )
        ]
    ]
)
```

## 8. Operational Runbooks

### Automated Remediation

```python
# Auto-scaling based on queue depth
queue_depth_alarm = cloudwatch.Alarm(
    self, "HighQueueDepth",
    metric=queue.metric_approximate_number_of_messages_visible(),
    threshold=1000,
    evaluation_periods=2
)

# Lambda to increase concurrency
remediation_lambda = _lambda.Function(
    self, "AutoRemediation",
    handler="remediation.scale_up",
    environment={
        "LAMBDA_FUNCTION_NAME": processing_lambda.function_name,
        "MAX_CONCURRENCY": "100"
    }
)

queue_depth_alarm.add_alarm_action(
    cloudwatch_actions.LambdaAction(remediation_lambda)
)
```

## 9. Dashboards and Visualization

### Executive Dashboard

```python
# High-level business metrics
executive_dashboard = cloudwatch.Dashboard(
    self, "ExecutiveDashboard",
    default_interval=Duration.hours(24),
    widgets=[
        [
            cloudwatch.SingleValueWidget(
                title="Total Transcripts Today",
                metrics=[
                    cloudwatch.Metric(
                        namespace="WhisperSync/Business",
                        metric_name="TranscriptsProcessed",
                        statistic="Sum",
                        period=Duration.days(1)
                    )
                ],
                width=6
            ),
            cloudwatch.SingleValueWidget(
                title="Success Rate",
                metrics=[
                    cloudwatch.MathExpression(
                        expression="success/total*100",
                        using_metrics={
                            "success": successful_transcripts_metric,
                            "total": total_transcripts_metric
                        }
                    )
                ],
                width=6
            ),
            cloudwatch.SingleValueWidget(
                title="Average Processing Time",
                metrics=[processing_time_metric],
                width=6
            ),
            cloudwatch.SingleValueWidget(
                title="System Availability",
                metrics=[system_health_metric],
                width=6
            )
        ]
    ]
)
```

## 10. Continuous Improvement

### Performance Baselines

```python
# Establish and monitor baselines
baseline_calculator = _lambda.Function(
    self, "BaselineCalculator",
    handler="baselines.calculate",
    schedule=events.Schedule.rate(Duration.days(1))
)

def calculate_baselines():
    # Query CloudWatch for historical data
    metrics = ["Duration", "MemoryUtilization", "Errors"]
    
    for metric in metrics:
        response = cloudwatch.get_metric_statistics(
            Namespace="AWS/Lambda",
            MetricName=metric,
            Dimensions=[{"Name": "FunctionName", "Value": function_name}],
            StartTime=datetime.now() - timedelta(days=7),
            EndTime=datetime.now(),
            Period=3600,
            Statistics=["Average", "Maximum"]
        )
        
        # Calculate baseline
        baseline = calculate_statistical_baseline(response["Datapoints"])
        
        # Store in DynamoDB
        dynamodb.put_item(
            TableName="Baselines",
            Item={
                "metric": metric,
                "baseline": baseline,
                "timestamp": datetime.now().isoformat()
            }
        )
```

## Conclusion

This comprehensive monitoring and observability plan ensures WhisperSync maintains high availability, performance, and reliability while providing actionable insights for continuous improvement.