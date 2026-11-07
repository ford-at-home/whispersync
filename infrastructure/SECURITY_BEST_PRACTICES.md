# WhisperSync Security Best Practices

## Overview

This document outlines comprehensive security measures for the WhisperSync voice memo processing system, following AWS Well-Architected Framework security pillar principles.

## Security Architecture

### Defense in Depth Strategy

```
┌─────────────────────────────────────────────────────────┐
│                   CloudFront + WAF                       │
├─────────────────────────────────────────────────────────┤
│                   API Gateway + Auth                     │
├─────────────────────────────────────────────────────────┤
│                  Lambda Functions                        │
│                  (VPC + Security Groups)                 │
├─────────────────────────────────────────────────────────┤
│     S3 Buckets        SQS Queues       DynamoDB        │
│   (Encryption +     (Encryption +    (Encryption +     │
│    Versioning)      DLQ + Auth)       Row-Level)       │
└─────────────────────────────────────────────────────────┘
```

## 1. Identity and Access Management (IAM)

### Principle of Least Privilege

```python
# Lambda execution role with minimal permissions
lambda_role = iam.Role(
    self, "LambdaRole",
    assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
    inline_policies={
        "MinimalPolicy": iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["s3:GetObject"],
                    resources=[f"{bucket.bucket_arn}/transcripts/*"],
                    conditions={
                        "StringEquals": {
                            "s3:ExistingObjectTag/approved": "true"
                        }
                    }
                )
            ]
        )
    }
)
```

### Service-to-Service Authentication

```python
# STS assume role for cross-account access
assume_role_policy = iam.PolicyStatement(
    effect=iam.Effect.ALLOW,
    principals=[iam.ServicePrincipal("lambda.amazonaws.com")],
    actions=["sts:AssumeRole"],
    conditions={
        "StringEquals": {
            "sts:ExternalId": "unique-external-id"
        }
    }
)
```

## 2. Data Protection

### Encryption at Rest

```python
# Multi-layer encryption strategy
class EncryptionConfig:
    # S3 Encryption
    s3_bucket = s3.Bucket(
        encryption=s3.BucketEncryption.KMS,
        encryption_key=kms.Key(
            enable_key_rotation=True,
            key_policy=key_policy
        ),
        bucket_key_enabled=True  # Reduce KMS costs
    )
    
    # DynamoDB Encryption
    dynamodb_table = dynamodb.Table(
        encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
        encryption_key=pii_kms_key
    )
    
    # SQS Encryption
    sqs_queue = sqs.Queue(
        encryption=sqs.QueueEncryption.KMS,
        encryption_master_key=kms_key,
        data_key_reuse=Duration.hours(1)  # Cache for performance
    )
```

### Encryption in Transit

```python
# Enforce TLS for all communications
bucket.add_to_resource_policy(
    iam.PolicyStatement(
        effect=iam.Effect.DENY,
        principals=[iam.AnyPrincipal()],
        actions=["s3:*"],
        resources=[bucket.arn_for_objects("*")],
        conditions={
            "Bool": {"aws:SecureTransport": "false"}
        }
    )
)
```

### Sensitive Data Handling

```python
# Secrets Manager for API keys
api_secret = secrets.Secret(
    self, "APIKeys",
    generate_secret_string=secrets.SecretStringGenerator(
        secret_string_template=json.dumps({
            "eleven_labs_key": "PLACEHOLDER",
            "github_token": "PLACEHOLDER"
        }),
        generate_string_key="nonce"
    ),
    removal_policy=RemovalPolicy.RETAIN,
    replica_regions=[
        secrets.ReplicaRegion(
            region="us-west-2",
            encryption_key=disaster_recovery_key
        )
    ]
)

# Automatic rotation
api_secret.add_rotation_schedule(
    "RotationSchedule",
    rotation_lambda=rotation_lambda,
    automatically_after=Duration.days(30)
)
```

## 3. Network Security

### VPC Configuration

```python
# Production VPC with proper segmentation
vpc = ec2.Vpc(
    self, "SecureVPC",
    max_azs=3,  # High availability
    nat_gateways=1,
    subnet_configuration=[
        # Public subnet for ALB only
        ec2.SubnetConfiguration(
            name="Public",
            subnet_type=ec2.SubnetType.PUBLIC,
            cidr_mask=28  # Small subnet
        ),
        # Private subnet for compute
        ec2.SubnetConfiguration(
            name="Private",
            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            cidr_mask=24
        ),
        # Isolated subnet for databases
        ec2.SubnetConfiguration(
            name="Isolated",
            subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            cidr_mask=24
        )
    ]
)

# Security groups with explicit rules
lambda_sg = ec2.SecurityGroup(
    self, "LambdaSG",
    vpc=vpc,
    description="Lambda function security group",
    allow_all_outbound=False  # Explicit egress rules
)

# Only allow HTTPS outbound
lambda_sg.add_egress_rule(
    peer=ec2.Peer.any_ipv4(),
    connection=ec2.Port.tcp(443),
    description="HTTPS to AWS services"
)
```

### VPC Endpoints

```python
# Private connectivity to AWS services
endpoints = [
    ("S3", ec2.GatewayVpcEndpointAwsService.S3),
    ("DynamoDB", ec2.GatewayVpcEndpointAwsService.DYNAMODB)
]

for name, service in endpoints:
    vpc.add_gateway_endpoint(f"{name}Endpoint", service=service)

# Interface endpoints for other services
interface_endpoints = ["sqs", "kms", "secretsmanager", "lambda"]
for service in interface_endpoints:
    vpc.add_interface_endpoint(
        f"{service}Endpoint",
        service=ec2.InterfaceVpcEndpointAwsService(service),
        subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
    )
```

## 4. Logging and Monitoring

### Comprehensive Logging

```python
# CloudTrail for API calls
trail = cloudtrail.Trail(
    self, "SecurityTrail",
    bucket=audit_bucket,
    encryption_key=audit_kms_key,
    include_global_service_events=True,
    enable_file_validation=True,
    event_selectors=[
        cloudtrail.EventSelector(
            read_write_type=cloudtrail.ReadWriteType.ALL,
            include_management_events=True,
            data_resources=[
                cloudtrail.DataResource(
                    data_resource_type=cloudtrail.DataResourceType.S3_OBJECT,
                    values=[f"{bucket.bucket_arn}/*"]
                )
            ]
        )
    ]
)

# VPC Flow Logs
vpc.add_flow_log(
    "FlowLog",
    destination=logs.LogGroup(
        self, "VPCFlowLogs",
        retention=logs.RetentionDays.ONE_MONTH
    ),
    traffic_type=ec2.TrafficType.ALL
)
```

### Security Monitoring

```python
# GuardDuty for threat detection
guardduty = guardduty.CfnDetector(
    self, "ThreatDetection",
    enable=True,
    finding_publishing_frequency="FIFTEEN_MINUTES"
)

# Security Hub for compliance
securityhub = securityhub.CfnHub(
    self, "SecurityHub",
    standards=[
        "arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0",
        "arn:aws:securityhub:::standards/aws-foundational-security-best-practices/v/1.0.0"
    ]
)
```

## 5. Application Security

### Input Validation

```python
def validate_transcript(transcript: str) -> bool:
    """Validate transcript input to prevent injection attacks."""
    # Size limits
    if len(transcript) > 100000:  # 100KB max
        raise ValueError("Transcript too large")
    
    # Character validation
    if not transcript.isprintable():
        raise ValueError("Invalid characters in transcript")
    
    # Content validation
    suspicious_patterns = [
        r"<script",  # XSS
        r"'; DROP TABLE",  # SQL injection
        r"\$\{.*\}",  # Template injection
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, transcript, re.IGNORECASE):
            raise ValueError(f"Suspicious content detected: {pattern}")
    
    return True
```

### API Security

```python
# API Gateway with authentication
api = apigateway.RestApi(
    self, "SecureAPI",
    default_cors_preflight_options={
        "allow_origins": ["https://whispersync.app"],
        "allow_methods": ["GET", "POST"],
        "allow_headers": ["Content-Type", "X-Amz-Date", "Authorization"]
    }
)

# Cognito authorizer
authorizer = apigateway.CognitoUserPoolsAuthorizer(
    self, "APIAuthorizer",
    cognito_user_pools=[user_pool]
)

# Rate limiting
api.add_usage_plan(
    "UsagePlan",
    throttle={
        "rate_limit": 10,  # requests per second
        "burst_limit": 20
    },
    quota={
        "limit": 1000,
        "period": apigateway.Period.DAY
    }
)
```

## 6. Incident Response

### Automated Response

```python
# Lambda for automated security response
incident_response_lambda = _lambda.Function(
    self, "IncidentResponse",
    handler="security.incident_handler",
    environment={
        "SLACK_WEBHOOK": slack_webhook_secret.secret_arn,
        "SECURITY_TEAM_EMAIL": "security@example.com"
    }
)

# EventBridge rule for security events
security_rule = events.Rule(
    self, "SecurityEventRule",
    event_pattern={
        "source": ["aws.guardduty", "aws.securityhub"],
        "detail-type": ["GuardDuty Finding", "Security Hub Findings"]
    }
)
security_rule.add_target(targets.LambdaFunction(incident_response_lambda))
```

### Backup and Recovery

```python
# Automated backups
backup_plan = backup.BackupPlan(
    self, "BackupPlan",
    backup_plan_rules=[
        backup.BackupPlanRule(
            backup_vault=backup_vault,
            rule_name="DailyBackups",
            schedule_expression=events.Schedule.cron(hour="3", minute="0"),
            delete_after=Duration.days(30),
            move_to_cold_storage_after=Duration.days(7)
        )
    ]
)

# Add resources to backup
backup_plan.add_selection(
    "BackupSelection",
    resources=[
        backup.BackupResource.from_dynamo_db_table(theory_of_mind_table),
        backup.BackupResource.from_tag("Backup", "Required")
    ]
)
```

## 7. Compliance and Auditing

### Data Residency

```python
# Ensure data stays in specific regions
stack_policy = iam.PolicyDocument(
    statements=[
        iam.PolicyStatement(
            effect=iam.Effect.DENY,
            principals=[iam.AnyPrincipal()],
            actions=["*"],
            resources=["*"],
            conditions={
                "StringNotEquals": {
                    "aws:RequestedRegion": ["us-east-1", "us-west-2"]
                }
            }
        )
    ]
)
```

### GDPR Compliance

```python
# Data deletion Lambda
gdpr_deletion_lambda = _lambda.Function(
    self, "GDPRDeletion",
    handler="gdpr.delete_user_data",
    environment={
        "TABLES": json.dumps([
            theory_of_mind_table.table_name,
            memory_chains_table.table_name
        ]),
        "BUCKETS": json.dumps([
            main_bucket.bucket_name,
            memory_bucket.bucket_name
        ])
    }
)
```

## 8. Security Checklist

### Pre-Deployment
- [ ] All resources tagged with security classification
- [ ] KMS keys have appropriate key policies
- [ ] IAM roles follow least privilege
- [ ] Secrets stored in Secrets Manager
- [ ] VPC endpoints configured
- [ ] Security groups reviewed
- [ ] CloudTrail enabled
- [ ] GuardDuty activated

### Post-Deployment
- [ ] Penetration testing scheduled
- [ ] Security review completed
- [ ] Incident response plan tested
- [ ] Backup restoration verified
- [ ] Compliance scan passed
- [ ] Security training completed

## 9. Security Monitoring Dashboard

```python
# CloudWatch dashboard for security metrics
security_dashboard = cloudwatch.Dashboard(
    self, "SecurityDashboard",
    widgets=[
        [
            cloudwatch.GraphWidget(
                title="Failed Authentication Attempts",
                left=[failed_auth_metric]
            ),
            cloudwatch.GraphWidget(
                title="Encryption Key Usage",
                left=[kms_usage_metric]
            )
        ],
        [
            cloudwatch.SingleValueWidget(
                title="GuardDuty Findings",
                metrics=[guardduty_findings_metric]
            ),
            cloudwatch.SingleValueWidget(
                title="DLQ Messages (Potential Attacks)",
                metrics=[dlq_messages_metric]
            )
        ]
    ]
)
```

## 10. Continuous Security Improvement

### Security Automation

```python
# Automated security scanning
codebuild.Project(
    self, "SecurityScanning",
    source=codebuild.Source.git_hub(
        owner="your-org",
        repo="whispersync"
    ),
    build_spec=codebuild.BuildSpec.from_object({
        "version": "0.2",
        "phases": {
            "pre_build": {
                "commands": [
                    "pip install safety bandit",
                    "npm install -g snyk"
                ]
            },
            "build": {
                "commands": [
                    "safety check",
                    "bandit -r .",
                    "snyk test"
                ]
            }
        }
    })
)
```

## Conclusion

Security is not a one-time implementation but a continuous process. Regular reviews, updates, and improvements ensure WhisperSync maintains the highest security standards while processing sensitive voice data.