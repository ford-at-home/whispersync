"""WhisperSync Demo Web Application.

A simple Streamlit app to demonstrate the WhisperSync voice memo processing pipeline.

WHY THIS DEMO EXISTS:
- Provides immediate visual feedback for testing without AWS infrastructure
- Allows developers to understand the pipeline behavior before deploying
- Enables rapid iteration on agent logic without cloud costs
- Serves as a living documentation of expected system behavior
- Helps stakeholders visualize the end-user experience

WHY STREAMLIT:
- Zero JavaScript/React knowledge required for Python developers
- Built-in components perfect for ML/AI demos (progress bars, JSON viewers)
- Session state management handles demo scenarios elegantly
- Rapid prototyping matches the "voice-first" philosophy of quick capture
"""

import streamlit as st
import json
import time
import datetime
from typing import Dict, Any, List, Optional
import boto3
from dataclasses import dataclass
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator_agent import get_orchestrator_agent
from scripts.local_test_runner import process_transcript_locally

# Configure Streamlit page
st.set_page_config(
    page_title="WhisperSync Demo",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# WHY CUSTOM CSS: Streamlit's default styling doesn't convey the three-agent system clearly.
# Visual differentiation helps users understand agent specialization at a glance.
# Color coding (green=work, blue=memory, red=github) creates mental model of routing.
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .agent-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 5px solid;
    }
    .work-agent {
        border-left-color: #2ecc71;
    }
    .memory-agent {
        border-left-color: #3498db;
    }
    .github-agent {
        border-left-color: #e74c3c;
    }
    .routing-info {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .result-json {
        background-color: #2d3436;
        color: #dfe6e9;
        padding: 1rem;
        border-radius: 5px;
        font-family: monospace;
        font-size: 0.9rem;
    }
    .demo-scenario {
        background-color: #e8f4f8;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        cursor: pointer;
        transition: all 0.3s;
    }
    .demo-scenario:hover {
        background-color: #d1e7dd;
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)


@dataclass
class DemoScenario:
    """A demo scenario with pre-written transcript.
    
    WHY DEMO SCENARIOS:
    - Real voice memos are messy; controlled examples teach routing patterns
    - Shows edge cases like mixed content that triggers multiple agents
    - Provides consistent testing baseline for UI changes
    - Helps new users understand what kinds of content work best
    - Demonstrates the system's ability to handle ambiguous content
    """
    name: str
    description: str
    transcript: str
    expected_agents: List[str]


# WHY THESE SPECIFIC SCENARIOS:
# 1. Work Update - Most common use case, shows categorization and summarization
# 2. Personal Memory - Demonstrates emotion/theme extraction capabilities  
# 3. Project Idea - Shows transformation from vague idea to structured repo
# 4. Mixed Content - Proves system can handle real-world messy transcripts
# 5. Weekly Summary - Shows agent's ability to handle meta-requests
DEMO_SCENARIOS = [
    DemoScenario(
        name="🏢 Work Update",
        description="A typical work status update",
        transcript="Today I completed the API integration for the payment system. "
                  "The webhook handlers are now working properly and I've added comprehensive "
                  "error handling. Tomorrow I'll start working on the frontend components.",
        expected_agents=["work"]
    ),
    DemoScenario(
        name="💭 Personal Memory",
        description="A cherished personal moment",
        transcript="I'll never forget the sunset we watched from the mountain top yesterday. "
                  "The sky was painted in shades of orange and pink, and Sarah said it was the "
                  "most beautiful thing she'd ever seen. We sat there in silence, just taking it all in.",
        expected_agents=["memory"]
    ),
    DemoScenario(
        name="💡 Project Idea",
        description="A new app concept",
        transcript="I have an idea for a mobile app that helps people track their daily water intake "
                  "using smart reminders and gamification. It could integrate with fitness trackers "
                  "and provide personalized hydration goals based on activity levels.",
        expected_agents=["github"]
    ),
    DemoScenario(
        name="🔀 Mixed Content",
        description="Multiple topics in one memo",
        transcript="Finished debugging the authentication system today - all tests are passing now. "
                  "Oh, and I had this amazing idea for a voice-controlled home automation system "
                  "that could help elderly people. Also, I keep thinking about that conversation "
                  "with Mom last week about her childhood. Such precious memories.",
        expected_agents=["work", "github", "memory"]
    ),
    DemoScenario(
        name="📊 Weekly Summary Request",
        description="Complex request requiring agent coordination",
        transcript="Can you give me a summary of what I worked on this week? I need to prepare "
                  "for my one-on-one meeting with my manager.",
        expected_agents=["work"]
    )
]


def initialize_session_state():
    """Initialize Streamlit session state.
    
    WHY SESSION STATE:
    - Preserves processing history across reruns (Streamlit reruns on every interaction)
    - Demo mode default=True because most users won't have AWS setup
    - Processing history enables pattern recognition and debugging
    - Separate demo bucket name prevents accidental production data access
    """
    if "processing_history" not in st.session_state:
        st.session_state.processing_history = []
    if "demo_mode" not in st.session_state:
        st.session_state.demo_mode = True
    if "s3_bucket" not in st.session_state:
        st.session_state.s3_bucket = "voice-mcp-demo"


def display_agent_result(agent_name: str, result: Dict[str, Any]):
    """Display results from a specific agent.
    
    WHY AGENT-SPECIFIC DISPLAY:
    - Each agent returns different data structures requiring custom visualization
    - Work agent: emphasis on categorization and key points for productivity
    - Memory agent: emotional analysis and themes for personal reflection
    - GitHub agent: technical details and repo link for immediate action
    - Visual consistency through color coding reinforces mental model
    """
    agent_colors = {
        "work": "work-agent",
        "memory": "memory-agent", 
        "github": "github-agent"
    }
    
    agent_icons = {
        "work": "🏢",
        "memory": "💭",
        "github": "💻"
    }
    
    with st.container():
        st.markdown(
            f'<div class="agent-card {agent_colors.get(agent_name, "")}">'
            f'<h4>{agent_icons.get(agent_name, "🤖")} {agent_name.title()} Agent Result</h4>',
            unsafe_allow_html=True
        )
        
        # Display key results based on agent type
        if agent_name == "work":
            if "log_key" in result:
                st.write(f"**Log Location:** `{result['log_key']}`")
            if "summary" in result:
                st.write(f"**Summary:** {result['summary']}")
            if "categories" in result:
                st.write(f"**Categories:** {', '.join(result['categories'])}")
            if "key_points" in result:
                st.write("**Key Points:**")
                for point in result["key_points"]:
                    st.write(f"  • {point}")
        
        elif agent_name == "memory":
            if "memory_key" in result:
                st.write(f"**Memory Location:** `{result['memory_key']}`")
            if "analysis" in result:
                analysis = result["analysis"]
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Sentiment:** {analysis.get('sentiment', 'unknown')}")
                    st.write(f"**Significance:** {analysis.get('significance', 5)}/10")
                with col2:
                    if "themes" in analysis:
                        st.write(f"**Themes:** {', '.join(analysis['themes'])}")
                    if "emotions" in analysis:
                        st.write(f"**Emotions:** {', '.join(analysis['emotions'])}")
        
        elif agent_name == "github":
            if "repo" in result:
                st.write(f"**Repository:** [{result['repo']}]({result.get('url', '#')})")
            if "description" in result:
                st.write(f"**Description:** {result['description']}")
            if "tech_stack" in result:
                st.write(f"**Tech Stack:** {', '.join(result['tech_stack'])}")
            if "features" in result:
                st.write("**Features:**")
                for feature in result["features"]:
                    st.write(f"  • {feature}")
        
        st.markdown('</div>', unsafe_allow_html=True)


def process_transcript(transcript: str, demo_mode: bool = True) -> Dict[str, Any]:
    """Process a transcript through the WhisperSync pipeline.
    
    WHY TWO MODES:
    - Demo mode: Instant feedback without AWS setup barriers
    - AWS mode: Production-ready path for actual deployment
    
    WHY SIMULATED DELAY:
    - Sets realistic expectations (real processing takes 1-3 seconds)
    - Progress bar provides visual feedback reducing perceived wait time
    - Prevents users from thinking the system is frozen
    """
    if demo_mode:
        # Use local processing for demo
        with st.spinner("🤖 AI agents are analyzing your transcript..."):
            # Simulate processing time for demo effect
            progress_bar = st.progress(0)
            for i in range(100):
                time.sleep(0.01)
                progress_bar.progress(i + 1)
            
            # Process locally
            result = process_transcript_locally(transcript)
            return result
    else:
        # Use actual S3/Lambda pipeline
        # This would require AWS credentials and infrastructure
        st.error("AWS mode not implemented in demo. Please use demo mode.")
        return {}


def main():
    """Main application logic."""
    initialize_session_state()
    
    # Header
    st.markdown('<h1 class="main-header">🎙️ WhisperSync Demo</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p style="text-align: center; font-size: 1.2rem; color: #7f8c8d;">'
        'Transform your voice memos into actionable insights with AI agents</p>',
        unsafe_allow_html=True
    )
    
    # WHY SIDEBAR CONFIGURATION:
    # - Keeps main UI clean and focused on core workflow
    # - Statistics provide immediate feedback on system usage
    # - Mode toggle allows testing both local and AWS paths
    # - Clear history button essential for demo/testing scenarios
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        demo_mode = st.checkbox("Demo Mode", value=True, help="Run locally without AWS")
        st.session_state.demo_mode = demo_mode
        
        if not demo_mode:
            st.text_input("S3 Bucket", value=st.session_state.s3_bucket, key="bucket_input")
            st.warning("⚠️ AWS mode requires proper credentials and deployed infrastructure")
        
        st.markdown("---")
        
        st.header("📊 Statistics")
        if st.session_state.processing_history:
            st.metric("Transcripts Processed", len(st.session_state.processing_history))
            
            # Count agent usage
            agent_counts = {"work": 0, "memory": 0, "github": 0}
            for entry in st.session_state.processing_history:
                for agent in entry.get("agents_used", []):
                    if agent in agent_counts:
                        agent_counts[agent] += 1
            
            st.write("**Agent Usage:**")
            for agent, count in agent_counts.items():
                st.write(f"• {agent.title()}: {count}")
        else:
            st.info("No transcripts processed yet")
        
        if st.button("🗑️ Clear History"):
            st.session_state.processing_history = []
            st.rerun()
    
    # WHY TABBED INTERFACE:
    # - Process Transcript: Primary user action, gets top position
    # - Demo Scenarios: Learning tool for new users, quick testing
    # - Processing History: Debugging and pattern recognition
    # - Documentation: In-app help reduces context switching
    tab1, tab2, tab3, tab4 = st.tabs(["🎤 Process Transcript", "🎭 Demo Scenarios", 
                                      "📜 Processing History", "📚 Documentation"])
    
    with tab1:
        st.header("Voice Transcript Input")
        
        # Text input for transcript
        transcript = st.text_area(
            "Enter your voice transcript:",
            height=150,
            placeholder="Type or paste your voice memo transcript here..."
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            process_button = st.button("🚀 Process", type="primary", use_container_width=True)
        
        if process_button and transcript:
            # Process the transcript
            start_time = time.time()
            result = process_transcript(transcript, demo_mode=st.session_state.demo_mode)
            processing_time = time.time() - start_time
            
            if result:
                # WHY DISPLAY ROUTING DECISION:
                # - Transparency builds trust in AI decision-making
                # - Confidence scores help users understand ambiguous cases
                # - Reasoning text teaches users how to structure future memos
                # - Secondary agents show the system's multi-agent capabilities
                routing = result.get("routing_decision", {})
                if routing:
                    st.markdown('<div class="routing-info">', unsafe_allow_html=True)
                    st.subheader("🎯 Routing Decision")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Primary Agent", routing.get("primary_agent", "unknown"))
                    with col2:
                        confidence = routing.get("confidence", 0)
                        st.metric("Confidence", f"{confidence:.2%}")
                    with col3:
                        st.metric("Processing Time", f"{processing_time:.2f}s")
                    
                    if routing.get("reasoning"):
                        st.write(f"**Reasoning:** {routing['reasoning']}")
                    
                    if routing.get("secondary_agents"):
                        st.write(f"**Secondary Agents:** {', '.join(routing['secondary_agents'])}")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Display agent results
                st.subheader("🤖 Agent Results")
                processing_results = result.get("processing_results", {})
                
                if processing_results:
                    for agent_name, agent_result in processing_results.items():
                        display_agent_result(agent_name, agent_result)
                else:
                    st.warning("No agent results available")
                
                # Store in history
                st.session_state.processing_history.append({
                    "timestamp": datetime.datetime.now().isoformat(),
                    "transcript": transcript[:100] + "..." if len(transcript) > 100 else transcript,
                    "routing_decision": routing,
                    "agents_used": list(processing_results.keys()),
                    "processing_time": processing_time
                })
                
                # Show raw JSON in expander
                with st.expander("🔍 View Raw Response"):
                    st.markdown('<div class="result-json">', unsafe_allow_html=True)
                    st.json(result)
                    st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.header("🎭 Demo Scenarios")
        st.write("Click on any scenario below to load it into the processor:")
        
        for scenario in DEMO_SCENARIOS:
            if st.button(f"{scenario.name}", key=f"scenario_{scenario.name}", use_container_width=True):
                # Switch to process tab and load transcript
                st.session_state.demo_transcript = scenario.transcript
                st.info(f"Loaded scenario: {scenario.name}")
                st.write(f"**Description:** {scenario.description}")
                st.write(f"**Expected Agents:** {', '.join(scenario.expected_agents)}")
                st.write(f"**Transcript:** {scenario.transcript}")
                
                # Provide a button to process
                if st.button("Process This Scenario", type="primary"):
                    result = process_transcript(scenario.transcript, demo_mode=True)
                    
                    if result:
                        routing = result.get("routing_decision", {})
                        processing_results = result.get("processing_results", {})
                        
                        st.success("✅ Scenario processed successfully!")
                        
                        # Show routing info
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Routed to", routing.get("primary_agent", "unknown"))
                        with col2:
                            st.metric("Confidence", f"{routing.get('confidence', 0):.2%}")
                        
                        # Show agent results
                        for agent_name, agent_result in processing_results.items():
                            display_agent_result(agent_name, agent_result)
    
    with tab3:
        st.header("📜 Processing History")
        
        if st.session_state.processing_history:
            # Display history in reverse chronological order
            for i, entry in enumerate(reversed(st.session_state.processing_history)):
                with st.expander(
                    f"🕐 {entry['timestamp']} - {entry['transcript']}", 
                    expanded=(i == 0)
                ):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Primary Agent:** {entry['routing_decision'].get('primary_agent')}")
                    with col2:
                        st.write(f"**Confidence:** {entry['routing_decision'].get('confidence', 0):.2%}")
                    with col3:
                        st.write(f"**Time:** {entry['processing_time']:.2f}s")
                    
                    st.write(f"**Agents Used:** {', '.join(entry['agents_used'])}")
                    
                    if st.button(f"Reprocess", key=f"reprocess_{i}"):
                        # Extract full transcript from history if available
                        st.info("Reprocessing functionality not implemented in demo")
        else:
            st.info("No processing history yet. Try processing a transcript!")
    
    with tab4:
        st.header("📚 Documentation")
        
        st.markdown("""
        ## How WhisperSync Works
        
        ### WHY VOICE-FIRST DESIGN
        
        Voice memos remove the friction of typing, allowing thoughts to flow naturally.
        Most insights come when we're away from keyboards - walking, driving, showering.
        This system captures those fleeting thoughts before they're lost.
        
        ### WHY THREE AGENTS (Not One)
        
        A single agent would need complex routing logic and become a maintenance nightmare.
        Specialized agents can evolve independently with domain-specific features.
        Clear separation makes the system predictable and debuggable.
        Users can mentally model "which folder" maps to "which outcome."
        
        WhisperSync is an intelligent voice memo processing system that uses AI agents 
        to automatically route and process your voice transcripts.
        
        ### 🤖 Available Agents
        
        1. **Work Journal Agent** 🏢
           - Processes work-related updates, meeting notes, and task completions
           - Maintains organized weekly logs with AI-powered summaries
           - Extracts key points and categorizes work activities
        
        2. **Memory Agent** 💭
           - Stores personal memories with emotional analysis
           - Identifies themes, people, and locations
           - Rates significance and finds related memories
        
        3. **GitHub Idea Agent** 💻
           - Transforms project ideas into fully-structured repositories
           - Generates comprehensive README files and initial code
           - Adds appropriate licenses and GitHub topics
        
        ### 🎯 Intelligent Routing
        
        The Orchestrator Agent analyzes each transcript to determine:
        - Which agent(s) should process the content
        - Confidence level in the routing decision
        - How to handle mixed-content transcripts
        
        ### 🔄 Processing Pipeline
        
        1. **Input**: Voice memo transcript
        2. **Analysis**: AI determines content type and intent
        3. **Routing**: Orchestrator sends to appropriate agent(s)
        4. **Processing**: Specialized agents take action
        5. **Output**: Structured results and stored artifacts
        
        ### 💡 Tips for Best Results
        
        - Be clear and specific in your voice memos
        - Separate different topics with pause words like "also" or "another thing"
        - For work updates, mention specific tasks and outcomes
        - For memories, include emotional context and details
        - For project ideas, describe the problem and potential solution
        """)


if __name__ == "__main__":
    main()