# Interaction Diagrams & Data Flow Specifications

## Overview

This document provides detailed interaction diagrams and data flow specifications for the enhanced WhisperSync agent system, illustrating how voice memos transform into intelligent, personalized responses through multiple processing layers.

## 🌊 Complete System Data Flow

### End-to-End Voice Memo Processing

```mermaid
graph TB
    subgraph "1. Capture Layer"
        VM[Voice Memo] --> WT[Whisper Transcription]
        WT --> S3U[S3 Upload]
        S3U --> S3E[S3 Event]
    end
    
    subgraph "2. Classification Layer"
        S3E --> CL[Classifier Lambda]
        CL --> TC[Transcript Classifier]
        TC --> CS[Confidence Score]
        CS --> RD{Routing Decision}
    end
    
    subgraph "3. Distribution Layer"
        RD -->|Single Agent| SAQ[Single Agent Queue]
        RD -->|Multi Agent| MAQ[Multi Agent Queues]
        RD -->|Low Confidence| HRQ[Human Review Queue]
    end
    
    subgraph "4. Agent Processing Layer"
        SAQ --> AP[Agent Processor]
        MAQ --> MAP[Multi-Agent Processor]
        
        AP --> TOM[Theory of Mind]
        MAP --> TOM
        
        AP --> KB[Knowledge Base]
        MAP --> KB
        
        TOM --> PS[Persona Selector]
        KB --> PS
    end
    
    subgraph "5. Synthesis Layer"
        PS --> VS[Voice Synthesizer]
        AP --> RG[Response Generator]
        MAP --> SYN[Response Synthesizer]
        
        RG --> VS
        SYN --> VS
        
        VS --> EL[ElevenLabs API]
    end
    
    subgraph "6. Output Layer"
        EL --> AO[Audio Output]
        RG --> TO[Text Output]
        SYN --> TO
        
        AO --> S3O[S3 Storage]
        TO --> S3O
        
        S3O --> UN[User Notification]
    end
    
    subgraph "7. Learning Layer"
        S3O --> AL[Analytics Lambda]
        AL --> TOM
        AL --> CL
        AL --> ML[Machine Learning]
    end
```

## 📊 Detailed Interaction Sequences

### 1. Single Agent Processing Flow

```mermaid
sequenceDiagram
    participant U as User
    participant VM as Voice Memo
    participant S3 as S3 Storage
    participant CL as Classifier
    participant Q as SQS Queue
    participant A as Agent
    participant TOM as Theory of Mind
    participant PS as Persona Selector
    participant EL as ElevenLabs
    participant OUT as Output
    
    U->>VM: Records voice memo
    VM->>S3: Upload transcript
    S3->>CL: Trigger classification
    
    CL->>CL: Analyze transcript
    Note over CL: Confidence: 0.92<br/>Agent: SpiritualAgent<br/>Category: personal_memory
    
    CL->>Q: Send to agent queue
    Q->>A: Deliver message
    
    A->>TOM: Load user theory
    TOM-->>A: Current state & patterns
    
    A->>A: Process transcript
    Note over A: Extract emotions<br/>Identify themes<br/>Calculate significance
    
    A->>PS: Request persona
    PS->>PS: Analyze context
    Note over PS: Emotion: nostalgic<br/>Energy: moderate<br/>Phase: reflecting
    PS-->>A: Sage persona selected
    
    A->>EL: Synthesize response
    EL-->>A: Audio stream
    
    A->>OUT: Store results
    OUT->>U: Notify completion
    
    A->>TOM: Update theory
    Note over TOM: Pattern detected:<br/>Increased family themes
```

### 2. Multi-Agent Collaboration Flow

```mermaid
sequenceDiagram
    participant T as Transcript
    participant C as Classifier
    participant O as Orchestrator
    participant EA as ExecutiveAgent
    participant GA as GitHubAgent
    participant SA as SpiritualAgent
    participant S as Synthesizer
    participant V as Voice Layer
    
    T->>C: "Had a breakthrough at work..."
    C->>C: Detect multiple domains
    Note over C: Work: 0.7<br/>Technical: 0.6<br/>Personal: 0.5
    
    C->>O: Multi-agent required
    
    par Parallel Processing
        O->>EA: Process work aspect
        and
        O->>GA: Process technical aspect
        and
        O->>SA: Process personal growth
    end
    
    EA-->>S: Work insights
    Note over EA: Key achievement<br/>Career milestone
    
    GA-->>S: Project opportunity
    Note over GA: Tool idea identified<br/>Architecture suggested
    
    SA-->>S: Growth reflection
    Note over SA: Confidence building<br/>Pattern of breakthroughs
    
    S->>S: Synthesize perspectives
    Note over S: Weighting:<br/>EA: 40%<br/>GA: 35%<br/>SA: 25%
    
    S->>V: Select primary persona
    Note over V: Executive voice chosen<br/>Professional celebration tone
    
    V->>V: Generate response
    Note over V: "Congratulations on your breakthrough!<br/>This demonstrates your growing expertise..."
```

### 3. Theory of Mind Evolution Flow

```mermaid
stateDiagram-v2
    [*] --> Observation
    
    Observation --> PatternDetection
    
    PatternDetection --> SignificantPattern: Confidence > 0.7
    PatternDetection --> Discard: Confidence < 0.7
    
    SignificantPattern --> LayerDetermination
    
    LayerDetermination --> CoreIdentity: Fundamental change
    LayerDetermination --> BehavioralPatterns: Behavior shift
    LayerDetermination --> ContextualPreferences: Context change
    LayerDetermination --> CurrentState: State update
    
    CoreIdentity --> ValidationCheck: Threshold: 0.95
    BehavioralPatterns --> ValidationCheck: Threshold: 0.85
    ContextualPreferences --> ValidationCheck: Threshold: 0.70
    CurrentState --> ValidationCheck: Threshold: 0.50
    
    ValidationCheck --> ConsistencyCheck: Passed
    ValidationCheck --> Rejected: Failed
    
    ConsistencyCheck --> UpdateTheory: Consistent
    ConsistencyCheck --> Rejected: Inconsistent
    
    UpdateTheory --> RecordHistory
    RecordHistory --> NotifyAgents
    NotifyAgents --> [*]
    
    Rejected --> [*]
    Discard --> [*]
```

### 4. Persona Selection Decision Tree

```mermaid
graph TD
    Start[Transcript Received] --> EA[Emotional Analysis]
    
    EA --> HE{High Emotion?>0.8}
    HE -->|Yes| ET{Emotion Type?}
    HE -->|No| AC[Agent Context]
    
    ET -->|Grief/Fear| Friend[Friend Persona<br/>Comfort Mode]
    ET -->|Joy/Achievement| Celebrate[Friend Persona<br/>Celebration Mode]
    ET -->|Awe/Profound| Sage[Sage Persona<br/>Deep Insight Mode]
    
    AC --> AT{Agent Type?}
    AT -->|GitHub| Builder[Builder Persona]
    AT -->|Executive| Exec[Executive Persona]
    AT -->|Spiritual| SC{Significance?>7}
    
    SC -->|Yes| Sage2[Sage Persona]
    SC -->|No| Friend2[Friend Persona]
    
    Builder --> BV{Context?}
    BV -->|New Idea| Excited[Excited Discovery]
    BV -->|Problem| Solving[Problem Solving]
    BV -->|Learning| Teaching[Teaching Mode]
    
    Exec --> EV{Context?}
    EV -->|Urgent| Priority[High Priority]
    EV -->|Review| Review[Weekly Review]
    EV -->|Success| Celebration[Celebration]
    
    Friend --> Output[Voice Synthesis]
    Celebrate --> Output
    Sage --> Output
    Excited --> Output
    Solving --> Output
    Teaching --> Output
    Priority --> Output
    Review --> Output
    Celebration --> Output
    Sage2 --> Output
    Friend2 --> Output
```

## 🔄 Data Transformation Pipeline

### Voice Memo to Actionable Insight

```yaml
Stage 1 - Raw Input:
  Input: Audio file (m4a, wav, mp3)
  Output: 
    Format: UTF-8 text
    Structure: Unstructured natural language
    Metadata:
      - timestamp
      - duration
      - source_device

Stage 2 - Classification:
  Input: Raw transcript text
  Process:
    - Sentiment analysis
    - Theme extraction
    - Entity recognition
    - Confidence scoring
  Output:
    Format: ClassificationResult
    Fields:
      - primary_agent: string
      - confidence: float (0.0-1.0)
      - themes: string[]
      - entities: Entity[]
      - emotional_tone: EmotionalProfile

Stage 3 - Agent Processing:
  Input: ClassificationResult + Transcript
  Context Loading:
    - Theory of Mind state
    - Recent interaction history
    - Knowledge base queries
  Processing:
    ExecutiveAgent:
      - Work pattern analysis
      - Task extraction
      - Priority assessment
      - Energy level inference
    GitHubAgent:
      - Technical concept extraction
      - Architecture planning
      - Implementation roadmap
      - Technology selection
    SpiritualAgent:
      - Emotional processing
      - Memory significance scoring
      - Life pattern recognition
      - Growth insight extraction
  Output:
    Format: AgentResponse
    Fields:
      - processed_content: ProcessedMemory
      - suggested_actions: Action[]
      - theory_updates: TheoryUpdate[]
      - storage_paths: string[]

Stage 4 - Synthesis:
  Input: AgentResponse(s)
  Multi-Agent Synthesis:
    - Weight responses by confidence
    - Resolve conflicts
    - Merge insights
    - Select primary narrative
  Persona Selection:
    - Analyze emotional context
    - Check Theory of Mind state
    - Apply selection rules
    - Choose voice variation
  Output:
    Format: SynthesizedResponse
    Fields:
      - text_response: string
      - voice_persona: PersonaConfig
      - merged_insights: Insight[]
      - combined_actions: Action[]

Stage 5 - Voice Generation:
  Input: SynthesizedResponse
  Processing:
    - Text preparation (SSML)
    - Prosody marking
    - Emotion injection
    - Voice synthesis (ElevenLabs)
  Output:
    Format: VoiceOutput
    Fields:
      - audio_url: string
      - duration: number
      - transcript: string
      - synthesis_metadata: object

Stage 6 - Storage & Analytics:
  Input: Complete processing result
  Storage:
    S3 Structure:
      - /transcripts/{date}/{id}.txt
      - /outputs/{agent}/{date}/{id}.json
      - /audio/{date}/{id}.mp3
      - /analytics/{date}/summary.json
  Analytics Events:
    - Processing metrics
    - Agent performance
    - User patterns
    - System health
```

## 📐 Component Interaction Specifications

### 1. Queue Message Formats

```typescript
// Classification to Agent Queue
interface AgentQueueMessage {
  messageId: string;
  correlationId: string;
  timestamp: string;
  
  // Core data
  transcript: string;
  s3Key: string;
  bucket: string;
  
  // Classification results
  classification: {
    agent: AgentType;
    confidence: number;
    themes: string[];
    sentiment: SentimentProfile;
    entities: Entity[];
  };
  
  // Routing metadata
  routing: {
    isPrimary: boolean;
    secondaryAgents?: AgentType[];
    handoffFrom?: string;
    priority: 'normal' | 'high';
  };
  
  // Context
  context: {
    userId: string;
    sessionId?: string;
    previousInteraction?: string;
  };
}

// Agent to Agent Handoff
interface HandoffMessage {
  handoffId: string;
  sourceAgent: AgentType;
  targetAgent: AgentType;
  timestamp: string;
  
  // Original data
  originalTranscript: string;
  originalClassification: Classification;
  
  // Partial processing
  partialAnalysis: {
    extractedConcepts: Concept[];
    identifiedOpportunity: string;
    confidence: number;
    processingNotes: string;
  };
  
  // Handoff metadata
  handoffReason: HandoffReason;
  suggestedPersona?: VoicePersona;
  preserveContext: boolean;
}

// Theory of Mind Update Broadcast
interface TheoryUpdateMessage {
  updateId: string;
  timestamp: string;
  source: AgentType;
  
  // Update details
  update: {
    layer: TheoryLayer;
    changes: Record<string, any>;
    confidence: number;
    evidence: Evidence[];
  };
  
  // Impact assessment
  impact: {
    affectedAgents: AgentType[];
    suggestedAdaptations: Adaptation[];
    risk: RiskLevel;
  };
  
  // Validation
  validation: {
    checksPerformed: ValidationCheck[];
    allPassed: boolean;
    warnings: string[];
  };
}
```

### 2. State Synchronization Protocol

```typescript
class StateSyncProtocol {
  // State change event
  interface StateChangeEvent {
    eventId: string;
    timestamp: string;
    eventType: 'create' | 'update' | 'delete';
    
    // What changed
    stateType: 'theory_of_mind' | 'knowledge' | 'memory';
    entityId: string;
    changes: StateDelta;
    
    // Causality
    triggeredBy: {
      source: 'agent' | 'user' | 'system';
      agentId?: string;
      reason: string;
    };
    
    // Ordering
    vectorClock: VectorClock;
    dependsOn: string[]; // Previous event IDs
  }
  
  // Synchronization checkpoint
  interface SyncCheckpoint {
    checkpointId: string;
    timestamp: string;
    
    // State snapshot
    states: {
      theoryOfMind: TheorySnapshot;
      knowledgeBase: KnowledgeSnapshot;
      recentMemories: MemorySnapshot;
    };
    
    // Consistency markers
    consistency: {
      lastEventId: string;
      eventCount: number;
      checksum: string;
    };
  }
  
  // Conflict resolution
  interface ConflictResolution {
    conflictId: string;
    detectedAt: string;
    
    // Conflicting updates
    updates: ConflictingUpdate[];
    
    // Resolution strategy
    strategy: 'last_write_wins' | 'merge' | 'user_override';
    resolution: StateUpdate;
    
    // Notification
    notifyAgents: AgentType[];
    requiresUserReview: boolean;
  }
}
```

### 3. Performance Monitoring Events

```typescript
interface PerformanceEvent {
  // Identification
  eventId: string;
  timestamp: string;
  correlationId: string;
  
  // Timing
  timings: {
    totalDuration: number;
    stages: {
      classification: number;
      agentProcessing: number;
      synthesis: number;
      voiceGeneration: number;
    };
  };
  
  // Resource usage
  resources: {
    lambdaMemoryUsed: number;
    lambdaDuration: number;
    apiCalls: {
      elevenlabs: number;
      anthropic: number;
      dynamodb: number;
      s3: number;
    };
  };
  
  // Quality metrics
  quality: {
    classificationConfidence: number;
    agentConfidence: number;
    synthesisCoherence: number;
    voiceNaturalness: number;
  };
  
  // Errors and warnings
  issues: {
    errors: ErrorDetail[];
    warnings: string[];
    retries: RetryInfo[];
  };
}
```

## 🔍 Detailed Processing Examples

### Example 1: Complex Work Memory with Embedded Idea

```mermaid
sequenceDiagram
    participant User
    participant System
    participant Executive as ExecutiveAgent
    participant GitHub as GitHubAgent
    participant Theory as Theory of Mind
    participant Voice
    
    User->>System: "Finished the API refactor today.<br/>Realized we could build a tool<br/>to automate this pattern detection"
    
    System->>System: Classify transcript
    Note over System: Primary: Executive (0.75)<br/>Secondary: GitHub (0.65)
    
    System->>Executive: Process work update
    System->>GitHub: Process tool idea
    
    Executive->>Theory: Load work patterns
    Theory-->>Executive: Recent refactoring focus
    
    Executive->>Executive: Extract work insights
    Note over Executive: Achievement: API refactor<br/>Pattern: Increasing automation interest
    
    GitHub->>Theory: Load technical preferences  
    Theory-->>GitHub: Prefers Python, serverless
    
    GitHub->>GitHub: Design tool architecture
    Note over GitHub: Tool: Pattern Detection API<br/>Stack: Python, Lambda, DynamoDB
    
    Executive->>System: Work update processed
    GitHub->>System: Project plan ready
    
    System->>System: Synthesize responses
    Note over System: Executive narrative with<br/>GitHub details embedded
    
    System->>Voice: Select persona
    Note over Voice: Executive voice chosen<br/>Achievement celebration tone
    
    Voice->>User: "Great work on the API refactor!<br/>Your idea for automating pattern<br/>detection is brilliant..."
    
    System->>Theory: Update patterns
    Note over Theory: Automation interest: +0.1<br/>Project completion: +1
```

### Example 2: Emotional Memory Triggering Sage Response

```mermaid
sequenceDiagram
    participant User
    participant System
    participant Spiritual as SpiritualAgent
    participant Theory as Theory of Mind
    participant Persona
    participant Voice
    
    User->>System: "Sitting by the ocean, I realized<br/>how much I've grown since the divorce.<br/>The waves remind me that everything changes."
    
    System->>System: Emotional analysis
    Note over System: Emotion: Contemplative (0.8)<br/>Significance: High (9/10)<br/>Themes: Growth, Change, Ocean
    
    System->>Spiritual: Process profound memory
    
    Spiritual->>Theory: Load emotional patterns
    Theory-->>Spiritual: Divorce mentioned 3 months ago<br/>Growth theme increasing<br/>Nature as healing pattern
    
    Spiritual->>Spiritual: Deep analysis
    Note over Spiritual: Life phase: Integration<br/>Growth edge: Acceptance<br/>Wisdom emerging: Impermanence
    
    Spiritual->>Persona: Request Sage voice
    Note over Persona: High significance<br/>Philosophical content<br/>Contemplative mood
    
    Persona-->>Spiritual: Sage persona confirmed
    
    Spiritual->>Voice: Generate response
    Note over Voice: Pace: Slow<br/>Tone: Warm, wise<br/>Pauses: Meaningful
    
    Voice->>User: "The ocean has always been<br/>a wise teacher... *pause*<br/>Your recognition of growth<br/>through change is profound..."
    
    Spiritual->>Theory: Update life phase
    Note over Theory: Phase: Healing → Integration<br/>Confidence: 0.85
```

## 📈 Analytics Data Flow

### Event Collection Pipeline

```yaml
Event Sources:
  - Transcript Classification
  - Agent Processing
  - Theory of Mind Updates  
  - Voice Synthesis
  - User Interactions

Event Stream:
  Format: JSON Lines
  Destination: Kinesis Data Streams
  Partitioning: By userId and date
  
Processing:
  Real-time:
    - Lambda processors
    - DynamoDB updates
    - CloudWatch metrics
  
  Batch:
    - Daily aggregations
    - Weekly summaries
    - Monthly reports
    
Storage:
  Hot (< 7 days):
    - DynamoDB
    - ElasticSearch
    
  Warm (7-90 days):
    - S3 Standard
    - Athena queryable
    
  Cold (> 90 days):
    - S3 Glacier
    - Lifecycle policies

Dashboards:
  Real-time:
    - Agent performance
    - System health
    - Active users
    
  Analytics:
    - User patterns
    - Agent accuracy
    - Theory evolution
    - Voice satisfaction
```

## 🚨 Error Handling Flows

### Graceful Degradation Strategy

```mermaid
graph TD
    E[Error Detected] --> T{Error Type?}
    
    T -->|Voice Synthesis| VE[Voice Error]
    T -->|Agent Processing| AE[Agent Error]
    T -->|Theory Update| TE[Theory Error]
    T -->|External API| XE[External Error]
    
    VE --> VF{Fallback Available?}
    VF -->|Yes| BV[Basic Voice]
    VF -->|No| TO[Text Only]
    
    AE --> RT{Retryable?}
    RT -->|Yes| RQ[Requeue]
    RT -->|No| FG[Fallback Agent]
    
    TE --> RB{Rollback Possible?}
    RB -->|Yes| PRV[Previous Version]
    RB -->|No| RM[Read-Only Mode]
    
    XE --> CB{Circuit Open?}
    CB -->|No| RTY[Retry with Backoff]
    CB -->|Yes| CA[Cached Response]
    
    BV --> LOG[Log Degradation]
    TO --> LOG
    RQ --> LOG
    FG --> LOG
    PRV --> LOG
    RM --> LOG
    RTY --> LOG
    CA --> LOG
    
    LOG --> MON[Monitor Recovery]
```

---

This comprehensive data flow architecture ensures smooth, intelligent processing of voice memos while maintaining system reliability and user experience quality through careful orchestration of all components.