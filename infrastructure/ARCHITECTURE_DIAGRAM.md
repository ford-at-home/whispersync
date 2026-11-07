# WhisperSync Enhanced Architecture Diagram

## High-Level Architecture

```mermaid
graph TB
    subgraph "Voice Input"
        iPhone[iPhone Voice Memos]
        Whisper[Local Whisper ASR]
    end
    
    subgraph "AWS Cloud"
        subgraph "Entry Layer"
            S3[S3 Main Bucket<br/>Intelligent Tiering]
            CF[CloudFront CDN]
        end
        
        subgraph "Processing Layer"
            Router[Router Lambda<br/>Event Handler]
            SQS_Orch[Orchestrator Queue<br/>FIFO]
            Orch[Orchestrator Lambda<br/>1GB Memory]
            
            subgraph "Agent Queues"
                SQS_Work[Work Journal Queue]
                SQS_Memory[Memory Queue]
                SQS_GitHub[GitHub Ideas Queue]
                SQS_EA[Executive Assistant Queue<br/>FIFO]
                SQS_Spirit[Spiritual Advisor Queue]
            end
            
            subgraph "Agent Lambdas"
                Work[Work Journal Agent<br/>512MB]
                Memory[Memory Agent<br/>768MB]
                GitHub[GitHub Agent<br/>512MB]
                EA[Executive Assistant<br/>768MB]
                Spirit[Spiritual Advisor<br/>512MB]
            end
        end
        
        subgraph "Data Layer"
            subgraph "DynamoDB Tables"
                ToM[Theory of Mind Table<br/>User Context]
                State[Agent State Table<br/>Execution State]
                Chains[Memory Chains Table<br/>Conversation History]
            end
            
            S3_Memory[S3 Memory Bucket<br/>Long-term Storage]
            Cache[ElastiCache Redis<br/>Hot Data Cache]
        end
        
        subgraph "Integration Layer"
            Secrets[Secrets Manager<br/>API Keys]
            Bedrock[Amazon Bedrock<br/>Claude API]
            ElevenLabs[ElevenLabs API<br/>Voice Synthesis]
            GitHubAPI[GitHub API<br/>Repo Creation]
        end
        
        subgraph "Monitoring"
            CW[CloudWatch<br/>Logs & Metrics]
            XRay[X-Ray<br/>Distributed Tracing]
            Dashboard[CloudWatch Dashboard]
            SNS[SNS Alerts]
        end
    end
    
    %% Data Flow
    iPhone --> Whisper
    Whisper --> S3
    S3 --> Router
    Router --> SQS_Orch
    SQS_Orch --> Orch
    
    Orch --> SQS_Work
    Orch --> SQS_Memory
    Orch --> SQS_GitHub
    Orch --> SQS_EA
    Orch --> SQS_Spirit
    
    SQS_Work --> Work
    SQS_Memory --> Memory
    SQS_GitHub --> GitHub
    SQS_EA --> EA
    SQS_Spirit --> Spirit
    
    %% Agent Data Access
    Work --> ToM
    Work --> S3_Memory
    Memory --> ToM
    Memory --> Chains
    Memory --> S3_Memory
    GitHub --> State
    EA --> ToM
    EA --> State
    Spirit --> ToM
    Spirit --> Chains
    
    %% External Integration
    Work --> Bedrock
    Memory --> Bedrock
    Memory --> ElevenLabs
    GitHub --> GitHubAPI
    EA --> Bedrock
    Spirit --> Bedrock
    Spirit --> ElevenLabs
    
    %% Monitoring
    Router --> CW
    Orch --> XRay
    Work --> XRay
    Memory --> XRay
    CW --> Dashboard
    CW --> SNS
    
    %% Caching
    Memory -.-> Cache
    EA -.-> Cache
    
    %% Secrets
    GitHub --> Secrets
    Memory --> Secrets
    Spirit --> Secrets
```

## Detailed Component Flow

```mermaid
sequenceDiagram
    participant User
    participant iPhone
    participant Whisper
    participant S3
    participant Router
    participant SQS
    participant Orchestrator
    participant Agent
    participant DynamoDB
    participant External
    
    User->>iPhone: Record voice memo
    iPhone->>Whisper: Audio file
    Whisper->>Whisper: Transcribe to text
    Whisper->>S3: Upload transcript
    S3->>Router: S3 Event notification
    Router->>Router: Extract metadata
    Router->>SQS: Send to orchestrator queue
    
    SQS->>Orchestrator: Deliver message
    Orchestrator->>DynamoDB: Load user context
    Orchestrator->>Orchestrator: Analyze & route
    Orchestrator->>SQS: Send to agent queue(s)
    
    SQS->>Agent: Deliver message
    Agent->>DynamoDB: Load agent state
    Agent->>External: Call APIs (Bedrock/GitHub/etc)
    Agent->>DynamoDB: Update Theory of Mind
    Agent->>S3: Store results
    Agent->>SQS: Acknowledge message
    
    Note over Agent: If processing fails,<br/>message returns to queue<br/>after visibility timeout
```

## Security Architecture

```mermaid
graph TB
    subgraph "Security Layers"
        subgraph "Network Security"
            VPC[VPC with Private Subnets]
            SG[Security Groups]
            NACL[Network ACLs]
            VPCEndpoints[VPC Endpoints]
        end
        
        subgraph "Identity & Access"
            IAM[IAM Roles & Policies]
            STS[STS Assume Role]
            ResourcePolicy[Resource Policies]
        end
        
        subgraph "Data Protection"
            KMS_Master[Master KMS Key]
            KMS_PII[PII KMS Key]
            S3_Encrypt[S3 Encryption]
            DDB_Encrypt[DynamoDB Encryption]
            SQS_Encrypt[SQS Encryption]
            TLS[TLS in Transit]
        end
        
        subgraph "Monitoring & Compliance"
            CloudTrail[CloudTrail Logging]
            GuardDuty[GuardDuty Threat Detection]
            Config[AWS Config Rules]
            SecurityHub[Security Hub]
        end
    end
    
    %% Relationships
    VPC --> SG
    VPC --> VPCEndpoints
    IAM --> STS
    KMS_Master --> S3_Encrypt
    KMS_Master --> SQS_Encrypt
    KMS_PII --> DDB_Encrypt
    CloudTrail --> S3_Encrypt
    GuardDuty --> SecurityHub
    Config --> SecurityHub
```

## Cost Optimization Flow

```mermaid
graph LR
    subgraph "Storage Optimization"
        S3_Hot[S3 Standard<br/>0-30 days]
        S3_IA[S3 Intelligent Tiering<br/>30+ days]
        S3_Glacier[Glacier Instant<br/>180+ days]
        S3_Deep[Deep Archive<br/>365+ days]
    end
    
    subgraph "Compute Optimization"
        Lambda_ARM[ARM Architecture<br/>20% cheaper]
        Lambda_Right[Right-sized Memory]
        Lambda_Reserved[Reserved Concurrency]
    end
    
    subgraph "Database Optimization"
        DDB_OnDemand[DynamoDB On-Demand]
        DDB_TTL[TTL for Cleanup]
        Cache_Layer[Cache Layer]
    end
    
    S3_Hot --> S3_IA
    S3_IA --> S3_Glacier
    S3_Glacier --> S3_Deep
    
    Lambda_ARM --> Lambda_Right
    Lambda_Right --> Lambda_Reserved
    
    DDB_OnDemand --> DDB_TTL
    DDB_TTL --> Cache_Layer
```

## Scalability Architecture

```mermaid
graph TB
    subgraph "Load Distribution"
        ALB[Application Load Balancer]
        CF_Dist[CloudFront Distribution]
        Route53[Route 53 DNS]
    end
    
    subgraph "Queue Sharding"
        Router_Shard[Router with Sharding Logic]
        Shard1[Queue Shard 1]
        Shard2[Queue Shard 2]
        Shard3[Queue Shard 3]
        ShardN[Queue Shard N]
    end
    
    subgraph "Auto Scaling"
        ASG[Auto Scaling Groups]
        Lambda_Scale[Lambda Concurrency Scaling]
        DDB_Scale[DynamoDB Auto Scaling]
    end
    
    subgraph "Global Distribution"
        Region1[US-East-1<br/>Primary]
        Region2[US-West-2<br/>DR]
        Region3[EU-West-1<br/>GDPR]
        GlobalTable[DynamoDB Global Table]
    end
    
    Route53 --> CF_Dist
    CF_Dist --> ALB
    ALB --> Router_Shard
    
    Router_Shard --> Shard1
    Router_Shard --> Shard2
    Router_Shard --> Shard3
    Router_Shard --> ShardN
    
    ASG --> Lambda_Scale
    Lambda_Scale --> DDB_Scale
    
    Region1 --> GlobalTable
    Region2 --> GlobalTable
    Region3 --> GlobalTable
```

## Theory of Mind Data Model

```mermaid
erDiagram
    USER ||--o{ TRANSCRIPT : creates
    USER ||--o{ PREFERENCE : has
    USER ||--o{ CONTEXT : maintains
    
    TRANSCRIPT ||--o{ PROCESSING : undergoes
    PROCESSING ||--|| AGENT : "handled by"
    PROCESSING ||--o{ MEMORY_CHAIN : creates
    
    AGENT ||--o{ THEORY_OF_MIND : updates
    THEORY_OF_MIND ||--|| USER : "about"
    
    MEMORY_CHAIN ||--o{ MEMORY_NODE : contains
    MEMORY_NODE ||--|| EMBEDDING : has
    
    USER {
        string user_id PK
        string email
        timestamp created_at
        json preferences
    }
    
    TRANSCRIPT {
        string transcript_id PK
        string user_id FK
        string content
        string agent_type
        timestamp created_at
    }
    
    THEORY_OF_MIND {
        string user_id PK
        timestamp updated_at SK
        json user_context
        json preferences
        json behavioral_patterns
        json communication_style
    }
    
    MEMORY_CHAIN {
        string chain_id PK
        number sequence SK
        string content
        json metadata
        timestamp created_at
    }
```

## Monitoring Dashboard Layout

```mermaid
graph TB
    subgraph "Executive Dashboard"
        KPI1[Total Transcripts<br/>Today]
        KPI2[Success Rate<br/>99.5%]
        KPI3[Avg Processing Time<br/>2.3s]
        KPI4[System Health<br/>✅]
    end
    
    subgraph "Technical Metrics"
        subgraph "Lambda Performance"
            Invocations[Invocation Rate]
            Errors[Error Rate]
            Duration[Duration P99]
            Concurrency[Concurrent Executions]
        end
        
        subgraph "Queue Health"
            QueueDepth[Queue Depth]
            MessageAge[Message Age]
            DLQ[DLQ Messages]
        end
        
        subgraph "Cost Tracking"
            DailyCost[Daily Cost]
            ProjectedMonthly[Projected Monthly]
            CostByService[Cost by Service]
        end
    end
    
    subgraph "Alerts & Actions"
        Critical[🔴 Critical Alerts]
        High[🟡 High Priority]
        Low[🟢 Low Priority]
        Runbooks[Automated Runbooks]
    end
```

## Deployment Pipeline

```mermaid
graph LR
    subgraph "Development"
        LocalDev[Local Development]
        UnitTests[Unit Tests]
        IntegrationTests[Integration Tests]
    end
    
    subgraph "CI/CD"
        GitHub[GitHub Push]
        CodeBuild[AWS CodeBuild]
        SecurityScan[Security Scanning]
        CDKSynth[CDK Synth]
    end
    
    subgraph "Deployment"
        DevEnv[Dev Environment]
        StagingEnv[Staging Environment]
        ProdEnv[Production Environment]
    end
    
    subgraph "Validation"
        SmokeTests[Smoke Tests]
        E2ETests[E2E Tests]
        Rollback[Rollback Strategy]
    end
    
    LocalDev --> UnitTests
    UnitTests --> IntegrationTests
    IntegrationTests --> GitHub
    
    GitHub --> CodeBuild
    CodeBuild --> SecurityScan
    SecurityScan --> CDKSynth
    
    CDKSynth --> DevEnv
    DevEnv --> SmokeTests
    SmokeTests --> StagingEnv
    StagingEnv --> E2ETests
    E2ETests --> ProdEnv
    ProdEnv --> Rollback
```

## Data Flow Summary

1. **Voice Input**: iPhone → Whisper → S3
2. **Event Processing**: S3 Event → Router Lambda → SQS
3. **Orchestration**: SQS → Orchestrator → Agent Queues
4. **Agent Processing**: Queue → Agent Lambda → External APIs
5. **Data Storage**: Agent → DynamoDB/S3
6. **Monitoring**: All components → CloudWatch/X-Ray

This architecture provides:
- **Reliability**: SQS queues with DLQ for guaranteed processing
- **Scalability**: Queue-based decoupling and auto-scaling
- **Security**: Multiple layers of encryption and access control
- **Observability**: Comprehensive monitoring and tracing
- **Cost Efficiency**: Pay-per-use with optimization strategies