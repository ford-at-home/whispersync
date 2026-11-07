# [Comms] EPIC-004: Inter-Agent Communication Architecture

## Why This Matters

Currently, WhisperSync agents operate in isolation - each processes its transcript independently without awareness of other agents' actions or insights. This limits the platform's ability to:
- Coordinate complex multi-step workflows (e.g., "Create a GitHub repo AND add it to my work journal")
- Share discovered patterns across agents (e.g., Executive Agent's productivity insights informing GitHub Agent's project suggestions)
- Prevent duplicate work or conflicting actions
- Build a holistic understanding of user behavior across all contexts

Inter-agent communication unlocks compound intelligence where the whole becomes greater than the sum of its parts.

## Acceptance Criteria

### 1. Message Bus Implementation
- [ ] Agents can publish messages to shared event bus (EventBridge or SQS)
- [ ] Agents can subscribe to relevant message types from other agents
- [ ] Messages include correlation IDs for tracking related actions
- [ ] Dead letter queue handles failed message processing
- [ ] Message schema validation prevents malformed communications

### 2. Communication Patterns
- [ ] Request/Response pattern for synchronous agent queries
- [ ] Pub/Sub pattern for broadcasting insights and events
- [ ] Workflow orchestration for multi-agent sequences
- [ ] Circuit breaker pattern prevents cascading failures

### 3. Message Types & Schemas
- [ ] Standardized message envelope with metadata (timestamp, source, correlation)
- [ ] Domain-specific message types (InsightDiscovered, ActionCompleted, etc.)
- [ ] Schema registry for message validation
- [ ] Backwards compatibility for message evolution

### 4. Security & Privacy
- [ ] Messages encrypted in transit and at rest
- [ ] Agent authentication and authorization
- [ ] Message filtering based on agent permissions
- [ ] Audit trail of all inter-agent communications

### 5. Performance & Reliability
- [ ] < 100ms message delivery latency
- [ ] Support for 1000+ messages/second
- [ ] Automatic retries with exponential backoff
- [ ] Message deduplication

## Technical Approach

### Architecture Options

#### Option 1: Amazon EventBridge (Recommended)
```python
# Agent publishes insight
eventbridge_client.put_events(
    Entries=[{
        'Source': 'whispersync.executive_agent',
        'DetailType': 'ProductivityInsight',
        'Detail': json.dumps({
            'correlation_id': transcript_id,
            'insight': 'User most productive 6-9am',
            'confidence': 0.85,
            'applicable_agents': ['github', 'spiritual']
        })
    }]
)

# Other agents subscribe via event rules
```

**Pros:**
- Native AWS integration
- Built-in filtering and routing
- Serverless, no infrastructure to manage
- Schema discovery and registry

**Cons:**
- AWS-specific lock-in
- Limited message size (256KB)
- Eventually consistent

#### Option 2: Amazon SQS + SNS
```python
# Fan-out pattern with SNS
sns_client.publish(
    TopicArn='arn:aws:sns:region:account:whispersync-agent-events',
    Message=json.dumps(message),
    MessageAttributes={
        'agent': {'DataType': 'String', 'StringValue': 'executive'},
        'event_type': {'DataType': 'String', 'StringValue': 'insight'}
    }
)
```

**Pros:**
- Battle-tested messaging
- FIFO queues for ordering
- Large message support (256KB, extendable with S3)
- Fine-grained access control

**Cons:**
- More complex setup
- Higher operational overhead
- Manual schema management

### Message Schema Design

```typescript
interface AgentMessage {
  // Envelope
  messageId: string;
  timestamp: string;
  source: {
    agentType: 'executive' | 'github' | 'spiritual';
    agentId: string;
    version: string;
  };
  correlation: {
    transcriptId: string;
    sessionId?: string;
    userId: string;
  };
  
  // Payload
  eventType: string;
  payload: any; // Validated against schema
  
  // Routing
  targetAgents?: string[];
  priority: 'low' | 'normal' | 'high';
  ttl?: number;
}

// Example: Theory of Mind Update
interface TheoryOfMindUpdate extends AgentMessage {
  eventType: 'theory_of_mind.update';
  payload: {
    category: string;
    patterns: string[];
    confidence: number;
    examples: string[];
  };
}
```

### Implementation Phases

1. **Phase 1: Basic Pub/Sub**
   - EventBridge setup with basic routing
   - Simple message publishing from agents
   - Manual subscriptions for testing

2. **Phase 2: Advanced Patterns**
   - Request/response correlation
   - Workflow orchestration
   - Message persistence and replay

3. **Phase 3: Intelligence Layer**
   - Semantic message routing
   - Auto-discovery of relevant messages
   - Cross-agent learning patterns

## Testing Scenarios

### 1. Multi-Agent Workflow Test
```
Transcript: "Create a habit tracker app and add it to my work log"
Expected:
1. Orchestrator routes to both GitHub and Executive agents
2. GitHub Agent publishes "RepositoryCreated" event
3. Executive Agent receives event and adds to work journal
4. Both agents publish completion events
5. Orchestrator aggregates results
```

### 2. Pattern Sharing Test
```
Executive Agent discovers: "User mentions family in 80% of evening memos"
Expected:
1. Executive publishes "PatternDiscovered" event
2. Spiritual Agent receives and adjusts persona selection
3. Future family-related memos get Mystic persona responses
```

### 3. Failure Handling Test
```
Scenario: GitHub Agent fails to create repository
Expected:
1. GitHub Agent publishes "ActionFailed" event
2. Executive Agent receives notification
3. Executive adds failure note to work journal
4. Orchestrator notifies user of partial completion
```

### 4. Performance Test
```
Load: 100 simultaneous transcripts
Expected:
- All messages delivered within 100ms
- No message loss
- Correct routing and processing
- System remains responsive
```

## Dependencies

### Technical Dependencies
- AWS EventBridge or SQS/SNS setup
- Message schema registry (EventBridge Schema Registry or custom)
- Monitoring and tracing infrastructure
- Dead letter queue configuration

### Feature Dependencies
- Base agent architecture must support async operations
- Correlation ID generation in orchestrator
- Agent versioning for compatibility

## Effort Estimation

### Development Tasks
- Message bus infrastructure setup: 3 days
- Agent integration framework: 5 days
- Message schemas and validation: 3 days
- Testing framework: 3 days
- Documentation: 2 days

**Total: 16 days**

### Risk Factors
- Learning curve for EventBridge/SQS patterns
- Complex testing scenarios
- Performance tuning requirements

## Labels

- `epic`
- `infrastructure`
- `priority-high`
- `size-xl`
- `needs-architecture-review`
- `affects-all-agents`

## Success Metrics

1. **Functional Success**
   - 100% of multi-agent workflows execute correctly
   - Zero message loss under normal operations
   - < 100ms message delivery latency

2. **Developer Success**
   - New message types added in < 1 hour
   - Clear debugging and tracing tools
   - Comprehensive test coverage

3. **Business Success**
   - Enables 5+ new compound agent behaviors
   - Reduces user friction for complex tasks
   - Improves overall system intelligence

## Architecture Decision Record (ADR)

**Decision**: Use EventBridge for inter-agent communication

**Context**: Need loosely coupled, scalable messaging between agents

**Consequences**:
- (+) Native AWS integration
- (+) Built-in schema registry
- (+) Powerful routing rules
- (-) AWS vendor lock-in
- (-) Message size limitations

**Alternatives Considered**: SQS/SNS, Kafka, Redis Pub/Sub