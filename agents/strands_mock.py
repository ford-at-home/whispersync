"""Strands SDK Mock Implementation for Development and Testing.

This module provides mock implementations of the Strands SDK components to enable
development and testing when the actual Strands packages are not available.

WHY MOCK LAYER:
- Enables development without AWS Strands dependencies
- Allows unit testing without external service dependencies
- Provides fallback when Strands services are unavailable
- Maintains API compatibility with real Strands SDK

PHILOSOPHY:
The mock layer should be functionally equivalent to the real Strands SDK
for basic operations, while being clearly identified as a mock in logs.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from functools import wraps

logger = logging.getLogger(__name__)


class MockAgent:
    """Mock implementation of Strands Agent class.
    
    WHY MOCK AGENT:
    - Provides same interface as real Agent for seamless fallback
    - Simulates basic conversational AI responses
    - Maintains tool registry and system prompt compatibility
    - Enables local development and testing
    """
    
    def __init__(
        self, 
        system_prompt: Optional[str] = None, 
        tools: Optional[List[Callable]] = None, 
        model: Optional[str] = None
    ):
        """Initialize mock agent.
        
        Args:
            system_prompt: System prompt for agent behavior
            tools: List of tool functions available to agent
            model: Model identifier (ignored in mock)
        """
        self.system_prompt = system_prompt or "You are a helpful AI assistant."
        self.tools = tools or []
        self.model = model or "mock-model"
        self.tool_registry = {}
        
        # Register tools by name for lookup
        for tool in self.tools:
            if hasattr(tool, '__name__'):
                self.tool_registry[tool.__name__] = tool
                
        logger.info(f"MockAgent initialized with {len(self.tools)} tools")
    
    def __call__(self, prompt: str) -> Dict[str, Any]:
        """Process a prompt and return mock response.
        
        Args:
            prompt: User prompt to process
            
        Returns:
            Mock response simulating agent processing
        """
        logger.info(f"MockAgent processing prompt: {prompt[:100]}...")
        
        # Simulate processing time
        time.sleep(0.1)
        
        # Generate mock response based on prompt analysis
        response = self._generate_mock_response(prompt)
        
        return {
            "response": response,
            "model": self.model,
            "timestamp": time.time(),
            "mock": True
        }
    
    def _generate_mock_response(self, prompt: str) -> str:
        """Generate contextual mock response.
        
        Args:
            prompt: Input prompt to analyze
            
        Returns:
            Generated mock response
        """
        prompt_lower = prompt.lower()
        
        # Route-specific responses for different agent types
        if "work" in prompt_lower or "meeting" in prompt_lower or "task" in prompt_lower:
            return "Mock work journal entry created. Logged professional activities."
        elif "memory" in prompt_lower or "remember" in prompt_lower or "feel" in prompt_lower:
            return "Mock memory preserved. Personal experience archived with emotional context."
        elif "github" in prompt_lower or "idea" in prompt_lower or "project" in prompt_lower:
            return "Mock GitHub repository created. Project idea implemented with initial structure."
        elif "route" in prompt_lower or "orchestrate" in prompt_lower:
            return "Mock routing decision made. Transcript analyzed and directed to appropriate agent."
        else:
            return f"Mock response to: {prompt[:50]}..."


def tool(func: Callable) -> Callable:
    """Mock tool decorator.
    
    WHY DECORATOR PATTERN:
    - Maintains compatibility with real Strands tool decorator
    - Marks functions as available tools for agents
    - Enables introspection and tool registry
    - Preserves original function while adding metadata
    
    Args:
        func: Function to mark as a tool
        
    Returns:
        Decorated function with tool metadata
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"MockTool '{func.__name__}' called")
        return func(*args, **kwargs)
    
    # Mark function as a tool
    wrapper._is_tool = True
    wrapper._tool_name = func.__name__
    wrapper._original_func = func
    
    return wrapper


@dataclass 
class MockWorkflowStep:
    """Mock workflow step for multi-agent coordination."""
    
    id: str
    agent: str
    description: str
    depends_on: List[str] = None


class MockWorkflow:
    """Mock workflow orchestration for complex multi-agent tasks.
    
    WHY WORKFLOW MOCK:
    - Simulates multi-step agent coordination
    - Provides dependency management between steps
    - Enables testing of complex orchestration logic
    - Maintains state across multiple operations
    """
    
    def __init__(self, name: str):
        self.name = name
        self.steps: List[MockWorkflowStep] = []
        self.results: Dict[str, Any] = {}
        
    def add_step(
        self, 
        step_id: str, 
        agent: str, 
        description: str,
        depends_on: List[str] = None
    ):
        """Add a step to the workflow.
        
        Args:
            step_id: Unique identifier for the step
            agent: Agent type to execute the step
            description: Human-readable step description
            depends_on: List of step IDs this step depends on
        """
        step = MockWorkflowStep(
            id=step_id,
            agent=agent,
            description=description,
            depends_on=depends_on or []
        )
        self.steps.append(step)
        
    def execute(self) -> Dict[str, Any]:
        """Execute the workflow steps in dependency order.
        
        Returns:
            Dictionary containing execution results for each step
        """
        logger.info(f"Executing mock workflow '{self.name}' with {len(self.steps)} steps")
        
        # Simple execution - in real implementation would handle dependencies
        for step in self.steps:
            self.results[step.id] = {
                "status": "completed",
                "agent": step.agent,
                "description": step.description,
                "output": f"Mock result for {step.description}",
                "timestamp": time.time()
            }
            
        return self.results


def workflow(name: str) -> MockWorkflow:
    """Create a mock workflow instance.
    
    Args:
        name: Name for the workflow
        
    Returns:
        MockWorkflow instance for orchestration
    """
    return MockWorkflow(name)


class MockGraph:
    """Mock graph representation for agent relationships.
    
    WHY GRAPH MOCK:
    - Represents agent dependencies and data flow
    - Enables visualization of complex workflows
    - Provides foundation for optimization algorithms
    - Maintains compatibility with real graph implementations
    """
    
    def __init__(self):
        self.nodes = {}
        self.edges = []
        
    def add_node(self, node_id: str, agent_type: str, metadata: Dict[str, Any] = None):
        """Add a node representing an agent or process.
        
        Args:
            node_id: Unique identifier for the node
            agent_type: Type of agent (work, memory, github, orchestrator)
            metadata: Additional node information
        """
        self.nodes[node_id] = {
            "id": node_id,
            "type": agent_type,
            "metadata": metadata or {}
        }
        
    def add_edge(self, from_node: str, to_node: str, relationship: str = "processes"):
        """Add an edge representing data flow or dependency.
        
        Args:
            from_node: Source node ID
            to_node: Target node ID
            relationship: Type of relationship between nodes
        """
        self.edges.append({
            "from": from_node,
            "to": to_node,
            "relationship": relationship
        })
        
    def to_dict(self) -> Dict[str, Any]:
        """Export graph as dictionary for serialization.
        
        Returns:
            Dictionary representation of the graph
        """
        return {
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
            "mock": True
        }


def graph() -> MockGraph:
    """Create a mock graph instance.
    
    Returns:
        MockGraph instance for agent relationship modeling
    """
    return MockGraph()


# Mock knowledge base retrieval tool
def bedrock_knowledge_base_retrieve(
    query: str, 
    knowledge_base_id: str = None,
    num_results: int = 5
) -> List[Dict[str, Any]]:
    """Mock knowledge base retrieval function.
    
    WHY MOCK KNOWLEDGE BASE:
    - Simulates Bedrock knowledge base queries
    - Provides realistic response structure
    - Enables testing without AWS resources
    - Maintains API compatibility
    
    Args:
        query: Search query string
        knowledge_base_id: Knowledge base identifier (ignored in mock)
        num_results: Number of results to return
        
    Returns:
        List of mock knowledge base results
    """
    logger.info(f"Mock knowledge base query: {query}")
    
    # Generate mock results based on query
    results = []
    for i in range(min(num_results, 3)):  # Return 1-3 mock results
        results.append({
            "content": f"Mock knowledge base result {i+1} for query: {query}",
            "score": 0.9 - (i * 0.1),
            "source": f"mock_document_{i+1}.md",
            "metadata": {
                "type": "mock_result",
                "query": query,
                "index": i
            }
        })
    
    return results


# Agent registration mocks
def register_agent(
    name: str,
    description: str,
    entrypoint: str,
    **kwargs
) -> Dict[str, Any]:
    """Mock agent registration function.
    
    Args:
        name: Agent name
        description: Agent description
        entrypoint: Entry point module path
        **kwargs: Additional registration parameters
        
    Returns:
        Mock registration result
    """
    logger.info(f"Mock agent registration: {name}")
    
    return {
        "name": name,
        "description": description,
        "entrypoint": entrypoint,
        "status": "registered",
        "mock": True,
        "registration_time": time.time()
    }


def invoke_agent(
    name: str,
    input: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """Mock agent invocation function.
    
    Args:
        name: Agent name to invoke
        input: Input data for the agent
        **kwargs: Additional invocation parameters
        
    Returns:
        Mock agent response
    """
    logger.info(f"Mock agent invocation: {name}")
    
    # Simulate processing based on agent name
    transcript = input.get("transcript", "")
    
    if "work" in name:
        response = f"Work journal updated with: {transcript[:50]}..."
    elif "memory" in name:
        response = f"Memory archived: {transcript[:50]}..."
    elif "github" in name:
        response = f"GitHub repository created for: {transcript[:50]}..."
    else:
        response = f"Agent {name} processed: {transcript[:50]}..."
    
    return {
        "response": response,
        "agent": name,
        "input": input,
        "mock": True,
        "processing_time": 0.1
    }


# Environment detection
def is_strands_available() -> bool:
    """Check if real Strands SDK is available.
    
    Returns:
        True if Strands SDK is available, False if using mocks
    """
    try:
        import strands
        return True
    except ImportError:
        return False


# Export mock implementations
__all__ = [
    "MockAgent",
    "tool", 
    "workflow",
    "graph",
    "bedrock_knowledge_base_retrieve",
    "register_agent",
    "invoke_agent",
    "is_strands_available"
]