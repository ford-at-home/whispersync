"""
Enhanced WhisperSync MCP Stack - Advanced Voice Memo Processing Infrastructure

This CDK stack implements an enhanced serverless architecture with:
- SQS for agent decoupling and reliable message processing
- DynamoDB for Theory of Mind persistence and state management
- Lambda functions for each agent with proper isolation
- ElevenLabs API integration for voice synthesis
- Long-term memory storage with tiered S3 lifecycle policies
- Enhanced observability and monitoring

ARCHITECTURAL IMPROVEMENTS:

1. SQS Message Decoupling:
   - Separate queues per agent type for independent scaling
   - Dead letter queues for failed processing
   - FIFO queues for ordered processing where needed
   - Message visibility timeout aligned with Lambda execution time

2. DynamoDB Theory of Mind:
   - Agent state persistence across invocations
   - User context and preferences storage
   - Conversation history and memory chains
   - Global secondary indexes for efficient queries

3. Enhanced Security:
   - Separate KMS keys for different data types
   - VPC endpoints for private connectivity
   - Secrets rotation for API keys
   - Fine-grained IAM policies

4. Cost Optimization:
   - S3 Intelligent-Tiering for automatic cost savings
   - DynamoDB On-Demand for unpredictable workloads
   - Lambda Reserved Concurrency to control costs
   - SQS Long Polling to reduce API calls
"""

import os
from aws_cdk import (
    Stack,
    CfnOutput,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_sqs as sqs,
    aws_dynamodb as dynamodb,
    aws_s3_notifications as s3n,
    aws_lambda_event_sources as lambda_events,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
    aws_sns as sns,
    aws_kms as kms,
    aws_ec2 as ec2,
    aws_logs as logs,
    aws_secretsmanager as secrets,
    aws_events as events,
    aws_events_targets as targets,
    Duration,
    RemovalPolicy,
    Tags,
)
from constructs import Construct
from pathlib import Path
from typing import Dict, List, Optional


class EnhancedMcpStack(Stack):
    """Enhanced WhisperSync infrastructure with SQS, DynamoDB, and advanced features."""
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str, 
        environment: str = "development",
        enable_vpc: bool = False,  # VPC adds cost but improves security
        enable_eleven_labs: bool = True,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.environment = environment
        self.is_production = environment == "production"
        self.enable_vpc = enable_vpc
        self.enable_eleven_labs = enable_eleven_labs
        
        # Tag all resources for cost tracking
        Tags.of(self).add("Project", "WhisperSync")
        Tags.of(self).add("Environment", environment)
        Tags.of(self).add("ManagedBy", "CDK")
        
        # Create core infrastructure components
        self._create_kms_keys()
        self._create_vpc() if enable_vpc else None
        self._create_s3_buckets()
        self._create_dynamodb_tables()
        self._create_sqs_queues()
        self._create_secrets()
        self._create_lambda_layers()
        self._create_lambda_functions()
        self._create_event_bridge_rules()
        self._create_monitoring()
        self._create_outputs()
    
    def _create_kms_keys(self):
        """Create KMS keys for encryption with proper key policies."""
        
        # Master key for all WhisperSync encryption
        self.master_key = kms.Key(
            self, "WhisperSyncMasterKey",
            description="Master encryption key for WhisperSync",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN if self.is_production else RemovalPolicy.DESTROY,
            alias=f"whispersync-master-{self.environment}"
        )
        
        # Separate key for PII data (memories, user context)
        self.pii_key = kms.Key(
            self, "WhisperSyncPIIKey",
            description="Encryption key for PII data in WhisperSync",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN,
            alias=f"whispersync-pii-{self.environment}"
        )
    
    def _create_vpc(self):
        """Create VPC for enhanced security (optional)."""
        
        self.vpc = ec2.Vpc(
            self, "WhisperSyncVPC",
            vpc_name=f"whispersync-{self.environment}",
            max_azs=2,  # Cost optimization: 2 AZs for HA
            nat_gateways=1 if self.is_production else 0,  # NAT is expensive
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS if self.is_production else ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24
                )
            ]
        )
        
        # VPC Endpoints for AWS services (reduces data transfer costs)
        self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3
        )
        
        self.vpc.add_gateway_endpoint(
            "DynamoDBEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.DYNAMODB
        )
        
        # Interface endpoints for other services (more expensive, production only)
        if self.is_production:
            for service_name in ["sqs", "secretsmanager", "kms"]:
                self.vpc.add_interface_endpoint(
                    f"{service_name}Endpoint",
                    service=ec2.InterfaceVpcEndpointAwsService(service_name)
                )
    
    def _create_s3_buckets(self):
        """Create S3 buckets with lifecycle policies for cost optimization."""
        
        # Main bucket with intelligent tiering
        bucket_name = os.environ.get('TRANSCRIPT_BUCKET_NAME', 'macbook-transcriptions')
        if self.environment != "production":
            bucket_name = f"{bucket_name}-{self.environment}"
        
        self.main_bucket = s3.Bucket(
            self, "WhisperSyncMainBucket",
            bucket_name=bucket_name,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.master_key,
            versioned=self.is_production,
            removal_policy=RemovalPolicy.RETAIN if self.is_production else RemovalPolicy.DESTROY,
            auto_delete_objects=not self.is_production,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            event_bridge_enabled=True,
            
            # Lifecycle rules for cost optimization
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="TransitionToIntelligentTiering",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INTELLIGENT_TIERING,
                            transition_after=Duration.days(0)  # Immediate
                        )
                    ]
                ),
                s3.LifecycleRule(
                    id="DeleteOldTranscripts",
                    enabled=True,
                    prefix="transcripts/",
                    expiration=Duration.days(90),  # Delete after 90 days
                    noncurrent_version_expiration=Duration.days(30)
                ),
                s3.LifecycleRule(
                    id="ArchiveOldMemories",
                    enabled=True,
                    prefix="memories/",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER_INSTANT_RETRIEVAL,
                            transition_after=Duration.days(180)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.DEEP_ARCHIVE,
                            transition_after=Duration.days(365)
                        )
                    ]
                )
            ]
        )
        
        # Separate bucket for long-term memory storage
        self.memory_bucket = s3.Bucket(
            self, "WhisperSyncMemoryBucket",
            bucket_name=f"whispersync-{self.environment}-memory",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.pii_key,
            versioned=True,  # Always version memories
            removal_policy=RemovalPolicy.RETAIN,  # Never delete memories
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            
            # Cost-optimized lifecycle for memories
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="OptimizeMemoryStorage",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.STANDARD_IA,
                            transition_after=Duration.days(30)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER_INSTANT_RETRIEVAL,
                            transition_after=Duration.days(90)
                        )
                    ]
                )
            ]
        )
    
    def _create_dynamodb_tables(self):
        """Create DynamoDB tables for Theory of Mind and state management."""
        
        # Theory of Mind table - stores agent understanding of users
        self.theory_of_mind_table = dynamodb.Table(
            self, "TheoryOfMindTable",
            table_name=f"whispersync-theory-of-mind-{self.environment}",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,  # Cost optimization
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.pii_key,
            point_in_time_recovery=self.is_production,
            removal_policy=RemovalPolicy.RETAIN if self.is_production else RemovalPolicy.DESTROY,
            
            # Enable DynamoDB Streams for change tracking
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES
        )
        
        # GSI for querying by agent type
        self.theory_of_mind_table.add_global_secondary_index(
            index_name="AgentTypeIndex",
            partition_key=dynamodb.Attribute(
                name="agent_type",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.NUMBER
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )
        
        # Agent state table - stores agent execution state
        self.agent_state_table = dynamodb.Table(
            self, "AgentStateTable",
            table_name=f"whispersync-agent-state-{self.environment}",
            partition_key=dynamodb.Attribute(
                name="agent_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="execution_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            time_to_live_attribute="ttl",  # Auto-cleanup old states
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Memory chains table - stores conversation/memory chains
        self.memory_chains_table = dynamodb.Table(
            self, "MemoryChainsTable",
            table_name=f"whispersync-memory-chains-{self.environment}",
            partition_key=dynamodb.Attribute(
                name="chain_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="sequence_number",
                type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.pii_key,
            removal_policy=RemovalPolicy.RETAIN if self.is_production else RemovalPolicy.DESTROY
        )
    
    def _create_sqs_queues(self):
        """Create SQS queues for reliable agent message processing."""
        
        self.agent_queues: Dict[str, sqs.Queue] = {}
        self.dlqs: Dict[str, sqs.Queue] = {}
        
        # Define agent types and their queue configurations
        agent_configs = {
            "orchestrator": {
                "fifo": True,  # Ordered processing for orchestration
                "visibility_timeout": Duration.minutes(15),
                "retention": Duration.days(14)
            },
            "work_journal": {
                "fifo": False,
                "visibility_timeout": Duration.minutes(5),
                "retention": Duration.days(7)
            },
            "memory": {
                "fifo": False,
                "visibility_timeout": Duration.minutes(10),
                "retention": Duration.days(14)
            },
            "github_idea": {
                "fifo": False,
                "visibility_timeout": Duration.minutes(5),
                "retention": Duration.days(7)
            },
            "executive_assistant": {
                "fifo": True,  # Ordered task processing
                "visibility_timeout": Duration.minutes(10),
                "retention": Duration.days(7)
            },
            "spiritual_advisor": {
                "fifo": False,
                "visibility_timeout": Duration.minutes(5),
                "retention": Duration.days(7)
            }
        }
        
        for agent_type, config in agent_configs.items():
            # Create DLQ first
            dlq_name = f"whispersync-{agent_type}-dlq-{self.environment}"
            if config["fifo"]:
                dlq_name += ".fifo"
                
            dlq = sqs.Queue(
                self, f"{agent_type}DLQ",
                queue_name=dlq_name,
                fifo=config["fifo"],
                encryption=sqs.QueueEncryption.KMS,
                encryption_master_key=self.master_key,
                retention_period=Duration.days(14)  # Max retention for debugging
            )
            self.dlqs[agent_type] = dlq
            
            # Create main queue with DLQ
            queue_name = f"whispersync-{agent_type}-{self.environment}"
            if config["fifo"]:
                queue_name += ".fifo"
                
            queue = sqs.Queue(
                self, f"{agent_type}Queue",
                queue_name=queue_name,
                fifo=config["fifo"],
                content_based_deduplication=config["fifo"],  # Dedup for FIFO
                encryption=sqs.QueueEncryption.KMS,
                encryption_master_key=self.master_key,
                visibility_timeout=config["visibility_timeout"],
                retention_period=config["retention"],
                dead_letter_queue=sqs.DeadLetterQueue(
                    max_receive_count=3,
                    queue=dlq
                ),
                # Cost optimization: long polling reduces API calls
                receive_message_wait_time=Duration.seconds(20)
            )
            self.agent_queues[agent_type] = queue
            
            # CloudWatch alarms for queue monitoring
            queue.metric_approximate_number_of_messages_visible().create_alarm(
                self, f"{agent_type}QueueDepthAlarm",
                alarm_name=f"whispersync-{agent_type}-queue-depth-{self.environment}",
                threshold=100,
                evaluation_periods=2,
                alarm_description=f"High message count in {agent_type} queue"
            )
            
            dlq.metric_approximate_number_of_messages_visible().create_alarm(
                self, f"{agent_type}DLQAlarm",
                alarm_name=f"whispersync-{agent_type}-dlq-messages-{self.environment}",
                threshold=1,
                evaluation_periods=1,
                alarm_description=f"Messages in {agent_type} DLQ"
            )
    
    def _create_secrets(self):
        """Create secrets for API keys and sensitive configuration."""
        
        # ElevenLabs API key
        if self.enable_eleven_labs:
            self.eleven_labs_secret = secrets.Secret(
                self, "ElevenLabsAPIKey",
                secret_name=f"whispersync/eleven-labs-api-key-{self.environment}",
                description="ElevenLabs API key for voice synthesis",
                encryption_key=self.master_key,
                generate_secret_string=secrets.SecretStringGenerator(
                    secret_string_template='{"api_key": "PLACEHOLDER"}',
                    generate_string_key="api_key"
                ) if not self.is_production else None  # Manual entry for production
            )
        
        # GitHub token (existing)
        self.github_secret = secrets.Secret(
            self, "GitHubToken",
            secret_name=f"whispersync/github-token-{self.environment}",
            description="GitHub personal access token",
            encryption_key=self.master_key
        )
        
        # Claude API configuration
        self.claude_secret = secrets.Secret(
            self, "ClaudeAPIConfig",
            secret_name=f"whispersync/claude-config-{self.environment}",
            description="Claude API configuration",
            encryption_key=self.master_key,
            generate_secret_string=secrets.SecretStringGenerator(
                secret_string_template='{"api_key": "PLACEHOLDER", "model": "claude-3-opus-20240229"}',
                generate_string_key="config"
            ) if not self.is_production else None
        )
    
    def _create_lambda_layers(self):
        """Create Lambda layers for shared dependencies."""
        
        # Common dependencies layer
        self.common_layer = _lambda.LayerVersion(
            self, "CommonDependencies",
            layer_version_name=f"whispersync-common-{self.environment}",
            code=_lambda.Code.from_asset(
                str(Path(__file__).resolve().parent.parent / "layers" / "common")
            ),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            description="Common dependencies for WhisperSync agents"
        )
        
        # AI/ML dependencies layer (if exists)
        ai_layer_path = Path(__file__).resolve().parent.parent / "layers" / "ai"
        if ai_layer_path.exists():
            self.ai_layer = _lambda.LayerVersion(
                self, "AIDependencies",
                layer_version_name=f"whispersync-ai-{self.environment}",
                code=_lambda.Code.from_asset(str(ai_layer_path)),
                compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
                description="AI/ML dependencies for WhisperSync"
            )
    
    def _create_lambda_functions(self):
        """Create Lambda functions for each agent with proper configuration."""
        
        # Common environment variables
        common_env = {
            "ENVIRONMENT": self.environment,
            "MAIN_BUCKET": self.main_bucket.bucket_name,
            "MEMORY_BUCKET": self.memory_bucket.bucket_name,
            "THEORY_OF_MIND_TABLE": self.theory_of_mind_table.table_name,
            "AGENT_STATE_TABLE": self.agent_state_table.table_name,
            "MEMORY_CHAINS_TABLE": self.memory_chains_table.table_name,
            "LOG_LEVEL": "WARNING" if self.is_production else "INFO",
            "ENABLE_XRAY": "true" if self.is_production else "false",
            "GITHUB_SECRET_NAME": self.github_secret.secret_name,
            "CLAUDE_SECRET_NAME": self.claude_secret.secret_name,
        }
        
        if self.enable_eleven_labs:
            common_env["ELEVEN_LABS_SECRET_NAME"] = self.eleven_labs_secret.secret_name
        
        # VPC configuration if enabled
        vpc_config = {
            "vpc": self.vpc,
            "vpc_subnets": ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
        } if self.enable_vpc else {}
        
        # Create Lambda functions for each agent
        self.agent_functions: Dict[str, _lambda.Function] = {}
        
        agent_configs = {
            "orchestrator": {
                "memory": 1024,  # More memory for orchestration logic
                "timeout": Duration.minutes(15),
                "reserved_concurrent": 5 if self.is_production else None
            },
            "work_journal": {
                "memory": 512,
                "timeout": Duration.minutes(5),
                "reserved_concurrent": 3 if self.is_production else None
            },
            "memory": {
                "memory": 768,  # More memory for sentiment analysis
                "timeout": Duration.minutes(10),
                "reserved_concurrent": 3 if self.is_production else None
            },
            "github_idea": {
                "memory": 512,
                "timeout": Duration.minutes(5),
                "reserved_concurrent": 2 if self.is_production else None
            },
            "executive_assistant": {
                "memory": 768,
                "timeout": Duration.minutes(10),
                "reserved_concurrent": 3 if self.is_production else None
            },
            "spiritual_advisor": {
                "memory": 512,
                "timeout": Duration.minutes(5),
                "reserved_concurrent": 2 if self.is_production else None
            }
        }
        
        for agent_type, config in agent_configs.items():
            # Agent-specific environment
            agent_env = common_env.copy()
            agent_env["AGENT_TYPE"] = agent_type
            agent_env["QUEUE_URL"] = self.agent_queues[agent_type].queue_url
            
            function = _lambda.Function(
                self, f"{agent_type.title().replace('_', '')}Function",
                function_name=f"whispersync-{agent_type}-{self.environment}",
                runtime=_lambda.Runtime.PYTHON_3_11,
                handler=f"agents.{agent_type}_agent.lambda_handler",
                code=_lambda.Code.from_asset(
                    str(Path(__file__).resolve().parent.parent / "lambda_fn")
                ),
                memory_size=config["memory"],
                timeout=config["timeout"],
                reserved_concurrent_executions=config["reserved_concurrent"],
                environment=agent_env,
                tracing=_lambda.Tracing.ACTIVE if self.is_production else _lambda.Tracing.DISABLED,
                layers=[self.common_layer],
                description=f"WhisperSync {agent_type} agent ({self.environment})",
                **vpc_config
            )
            
            self.agent_functions[agent_type] = function
            
            # Grant permissions
            self._grant_agent_permissions(function, agent_type)
            
            # Add SQS event source
            function.add_event_source(
                lambda_events.SqsEventSource(
                    self.agent_queues[agent_type],
                    batch_size=10 if not agent_configs[agent_type].get("fifo") else 1,
                    max_batching_window_in_seconds=20,  # Wait up to 20s to batch
                    report_batch_item_failures=True  # Individual message failure handling
                )
            )
        
        # Router Lambda (processes S3 events and routes to SQS)
        self.router_function = _lambda.Function(
            self, "RouterFunction",
            function_name=f"whispersync-router-{self.environment}",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lambda_fn.enhanced_router.lambda_handler",
            code=_lambda.Code.from_asset(
                str(Path(__file__).resolve().parent.parent / "lambda_fn")
            ),
            memory_size=256,
            timeout=Duration.minutes(1),
            environment={
                **common_env,
                "ORCHESTRATOR_QUEUE_URL": self.agent_queues["orchestrator"].queue_url,
            },
            tracing=_lambda.Tracing.ACTIVE if self.is_production else _lambda.Tracing.DISABLED,
            layers=[self.common_layer],
            description=f"WhisperSync S3 event router ({self.environment})",
            **vpc_config
        )
        
        # Grant router permissions
        self.main_bucket.grant_read(self.router_function)
        self.agent_queues["orchestrator"].grant_send_messages(self.router_function)
        
        # S3 event notification to router
        self.main_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.router_function),
            s3.NotificationKeyFilter(prefix="transcripts/", suffix=".txt")
        )
    
    def _grant_agent_permissions(self, function: _lambda.Function, agent_type: str):
        """Grant appropriate permissions to agent Lambda functions."""
        
        # Common permissions for all agents
        self.main_bucket.grant_read_write(function)
        self.memory_bucket.grant_read_write(function)
        self.theory_of_mind_table.grant_read_write_data(function)
        self.agent_state_table.grant_read_write_data(function)
        self.memory_chains_table.grant_read_write_data(function)
        
        # Queue permissions
        self.agent_queues[agent_type].grant_consume_messages(function)
        
        # Forward to other queues if orchestrator
        if agent_type == "orchestrator":
            for queue in self.agent_queues.values():
                queue.grant_send_messages(function)
        
        # Secrets access
        self.claude_secret.grant_read(function)
        
        if agent_type == "github_idea":
            self.github_secret.grant_read(function)
            
        if self.enable_eleven_labs and agent_type in ["memory", "spiritual_advisor"]:
            self.eleven_labs_secret.grant_read(function)
        
        # Bedrock access
        function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            resources=["*"]  # Bedrock doesn't support resource-level permissions
        ))
        
        # CloudWatch metrics
        function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["cloudwatch:PutMetricData"],
            resources=["*"],
            conditions={
                "StringEquals": {
                    "cloudwatch:namespace": "WhisperSync"
                }
            }
        ))
    
    def _create_event_bridge_rules(self):
        """Create EventBridge rules for scheduled tasks and maintenance."""
        
        # Warm-up rule to prevent cold starts
        warm_up_rule = events.Rule(
            self, "WarmUpRule",
            rule_name=f"whispersync-warmup-{self.environment}",
            schedule=events.Schedule.rate(Duration.minutes(5)),
            description="Keep Lambda functions warm"
        )
        
        # Add all agent functions as targets
        for agent_type, function in self.agent_functions.items():
            warm_up_rule.add_target(
                targets.LambdaFunction(
                    function,
                    event=events.RuleTargetInput.from_object({"action": "warmup"})
                )
            )
        
        # DLQ processing rule (runs hourly)
        dlq_rule = events.Rule(
            self, "DLQProcessingRule",
            rule_name=f"whispersync-dlq-processing-{self.environment}",
            schedule=events.Schedule.rate(Duration.hours(1)),
            description="Process messages in DLQs"
        )
        
        # Memory optimization rule (runs daily)
        memory_rule = events.Rule(
            self, "MemoryOptimizationRule",
            rule_name=f"whispersync-memory-optimization-{self.environment}",
            schedule=events.Schedule.cron(hour="2", minute="0"),  # 2 AM daily
            description="Optimize memory storage and cleanup"
        )
    
    def _create_monitoring(self):
        """Create comprehensive monitoring and alerting."""
        
        # SNS topic for alerts
        self.alert_topic = sns.Topic(
            self, "AlertTopic",
            topic_name=f"whispersync-alerts-{self.environment}",
            display_name="WhisperSync Alerts"
        )
        
        # CloudWatch Dashboard
        dashboard = cloudwatch.Dashboard(
            self, "WhisperSyncDashboard",
            dashboard_name=f"whispersync-{self.environment}",
            default_interval=Duration.hours(1)
        )
        
        # Add widgets for each agent
        for agent_type, function in self.agent_functions.items():
            dashboard.add_widgets(
                cloudwatch.GraphWidget(
                    title=f"{agent_type.title()} Performance",
                    left=[
                        function.metric_invocations(),
                        function.metric_errors(),
                        function.metric_throttles()
                    ],
                    right=[function.metric_duration()]
                ),
                cloudwatch.GraphWidget(
                    title=f"{agent_type.title()} Queue Metrics",
                    left=[
                        self.agent_queues[agent_type].metric_approximate_number_of_messages_visible(),
                        self.agent_queues[agent_type].metric_approximate_number_of_messages_not_visible()
                    ]
                )
            )
        
        # Cost tracking dashboard widgets
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="DynamoDB Consumed Capacity",
                left=[
                    self.theory_of_mind_table.metric_consumed_read_capacity_units(),
                    self.theory_of_mind_table.metric_consumed_write_capacity_units()
                ]
            ),
            cloudwatch.GraphWidget(
                title="S3 Request Metrics",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/S3",
                        metric_name="NumberOfObjects",
                        dimensions_map={"BucketName": self.main_bucket.bucket_name}
                    )
                ]
            )
        )
    
    def _create_outputs(self):
        """Create stack outputs for reference."""
        
        outputs = {
            "MainBucketName": self.main_bucket.bucket_name,
            "MemoryBucketName": self.memory_bucket.bucket_name,
            "TheoryOfMindTableName": self.theory_of_mind_table.table_name,
            "AgentStateTableName": self.agent_state_table.table_name,
            "MemoryChainsTableName": self.memory_chains_table.table_name,
            "AlertTopicArn": self.alert_topic.topic_arn,
            "DashboardURL": f"https://console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={self.stack_name}"
        }
        
        # Queue URLs
        for agent_type, queue in self.agent_queues.items():
            outputs[f"{agent_type.title().replace('_', '')}QueueUrl"] = queue.queue_url
        
        # Lambda function ARNs
        for agent_type, function in self.agent_functions.items():
            outputs[f"{agent_type.title().replace('_', '')}FunctionArn"] = function.function_arn
        
        # Create CloudFormation outputs
        for key, value in outputs.items():
            CfnOutput(
                self, key,
                value=value,
                export_name=f"WhisperSync-{key}-{self.environment}"
            )