# Symbiont Python SDK

A Python SDK for interacting with the Symbiont Agent Runtime System, providing a streamlined interface for building AI-powered applications with agent capabilities, tool review workflows, and security analysis.

## Overview

The Symbiont Python SDK enables developers to integrate with the Symbiont platform, which provides intelligent agent runtime capabilities and comprehensive tool review workflows. This SDK handles authentication, HTTP requests, error handling, and provides typed models for working with Symbiont agents, tool reviews, and related resources.

## Installation

### Install from PyPI

```bash
pip install symbiont-sdk
```

### Install from Repository (Development)

For development or to get the latest features:

```bash
git clone https://github.com/thirdkeyai/symbiont-sdk-python.git
cd symbiont-sdk-python
pip install -e .
```

## Configuration

The SDK can be configured using environment variables in a `.env` file. Copy the provided `.env.example` file to get started:

```bash
cp .env.example .env
```

### Supported Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SYMBIONT_API_KEY` | API key for authentication | None |
| `SYMBIONT_BASE_URL` | Base URL for the Symbiont API | `http://localhost:8080/api/v1` |
| `SYMBIONT_TIMEOUT` | Request timeout in seconds | `30` |
| `SYMBIONT_MAX_RETRIES` | Maximum retries for API calls | `3` |

### Example `.env` Configuration

```env
# API Configuration
SYMBIONT_API_KEY=your_api_key_here
SYMBIONT_BASE_URL=http://localhost:8080/api/v1

# Optional Settings
SYMBIONT_TIMEOUT=30
SYMBIONT_MAX_RETRIES=3
```

## Quick Start

### Basic Client Initialization

```python
from symbiont import Client

# Initialize with environment variables
client = Client()

# Or initialize with explicit parameters
client = Client(
    api_key="your_api_key",
    base_url="http://localhost:8080/api/v1"
)
```

### System Health Check

```python
from symbiont import Client

client = Client()

# Check system health
health = client.health_check()
print(f"Status: {health.status}")
print(f"Uptime: {health.uptime_seconds} seconds")
print(f"Version: {health.version}")
```

## API Reference

### Agent Management

#### List Agents

```python
# Get list of all agents
agents = client.list_agents()
print(f"Found {len(agents)} agents: {agents}")
```

#### Get Agent Status

```python
from symbiont import AgentState

# Get specific agent status
status = client.get_agent_status("agent-123")
print(f"Agent {status.agent_id} is {status.state}")
print(f"Memory usage: {status.resource_usage.memory_bytes} bytes")
print(f"CPU usage: {status.resource_usage.cpu_percent}%")
```

#### Create Agent

```python
from symbiont import Agent

# Create a new agent
agent_data = Agent(
    id="my-agent",
    name="My Assistant",
    description="A helpful AI assistant",
    system_prompt="You are a helpful assistant.",
    tools=["web_search", "calculator"],
    model="gpt-4",
    temperature=0.7,
    top_p=0.9,
    max_tokens=1000
)

result = client.create_agent(agent_data)
print(f"Created agent: {result}")
```

### Workflow Execution

```python
from symbiont import WorkflowExecutionRequest

# Execute a workflow
workflow_request = WorkflowExecutionRequest(
    workflow_id="data-analysis-workflow",
    parameters={
        "input_data": "path/to/data.csv",
        "analysis_type": "statistical"
    },
    agent_id="agent-123"  # Optional
)

result = client.execute_workflow(workflow_request)
print(f"Workflow result: {result}")
```

### Tool Review API

The Tool Review API provides comprehensive workflows for securely reviewing, analyzing, and signing MCP tools.

#### Submit Tool for Review

```python
from symbiont import (
    ReviewSessionCreate, Tool, ToolProvider, ToolSchema
)

# Define a tool for review
tool = Tool(
    name="example-calculator",
    description="A simple calculator tool",
    schema=ToolSchema(
        type="object",
        properties={
            "operation": {
                "type": "string",
                "enum": ["add", "subtract", "multiply", "divide"]
            },
            "a": {"type": "number"},
            "b": {"type": "number"}
        },
        required=["operation", "a", "b"]
    ),
    provider=ToolProvider(
        name="example-provider",
        public_key_url="https://example.com/pubkey.pem"
    )
)

# Submit for review
review_request = ReviewSessionCreate(
    tool=tool,
    submitted_by="developer@example.com",
    priority="normal"
)

session = client.submit_tool_for_review(review_request)
print(f"Review session {session.review_id} created with status: {session.status}")
```

#### Monitor Review Progress

```python
from symbiont import ReviewStatus

# Get review session details
session = client.get_review_session("review-123")
print(f"Review status: {session.status}")
print(f"Submitted by: {session.submitted_by}")

# Check if analysis is complete
if session.state.analysis_id:
    analysis = client.get_analysis_results(session.state.analysis_id)
    print(f"Risk score: {analysis.risk_score}/100")
    print(f"Found {len(analysis.findings)} security findings")
    
    for finding in analysis.findings:
        print(f"- {finding.severity.upper()}: {finding.title}")
```

#### List Review Sessions

```python
# List all review sessions with filtering
sessions = client.list_review_sessions(
    page=1,
    limit=10,
    status="pending_review",
    author="developer@example.com"
)

print(f"Found {len(sessions.sessions)} sessions")
for session in sessions.sessions:
    print(f"- {session.review_id}: {session.tool.name} ({session.status})")
```

#### Wait for Review Completion

```python
# Wait for review to complete (with timeout)
try:
    final_session = client.wait_for_review_completion("review-123", timeout=300)
    print(f"Review completed with status: {final_session.status}")
    
    if final_session.status == "approved":
        print("Tool approved for signing!")
    elif final_session.status == "rejected":
        print("Tool rejected. Check review comments.")
        
except TimeoutError:
    print("Review did not complete within timeout period")
```

#### Submit Human Review Decision

```python
from symbiont import HumanReviewDecision

# Submit reviewer decision
decision = HumanReviewDecision(
    decision="approve",
    comments="Tool looks safe after manual review",
    reviewer_id="reviewer@example.com"
)

result = client.submit_human_review_decision("review-123", decision)
print(f"Decision submitted: {result}")
```

#### Sign Approved Tool

```python
from symbiont import SigningRequest

# Sign an approved tool
signing_request = SigningRequest(
    review_id="review-123",
    signing_key_id="key-456"
)

signature = client.sign_approved_tool(signing_request)
print(f"Tool signed at {signature.signed_at}")
print(f"Signature: {signature.signature}")

# Get signed tool information
signed_tool = client.get_signed_tool("review-123")
print(f"Signed tool: {signed_tool.tool.name}")
print(f"Signature algorithm: {signed_tool.signature_algorithm}")
```

## Error Handling

The SDK provides specific exception classes for different types of errors:

```python
from symbiont import (
    Client, APIError, AuthenticationError, 
    NotFoundError, RateLimitError, SymbiontError
)

client = Client()

try:
    # Make an API request
    session = client.get_review_session("non-existent-review")
    
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    print("Please check your API key")
    
except NotFoundError as e:
    print(f"Resource not found: {e}")
    print(f"Response: {e.response_text}")
    
except RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
    print("Please wait before making more requests")
    
except APIError as e:
    print(f"API error (status {e.status_code}): {e}")
    print(f"Response: {e.response_text}")
    
except SymbiontError as e:
    print(f"SDK error: {e}")
    
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Exception Hierarchy

- `SymbiontError` - Base exception for all SDK errors
  - `APIError` - Generic API errors (4xx and 5xx status codes)
  - `AuthenticationError` - 401 Unauthorized responses
  - `NotFoundError` - 404 Not Found responses
  - `RateLimitError` - 429 Too Many Requests responses

## Advanced Usage

### Working with Models

All API responses are automatically converted to typed Pydantic models:

```python
from symbiont import ReviewSession, SecurityFinding, FindingSeverity

# Models provide type safety and validation
session = client.get_review_session("review-123")

# Access typed attributes
session_id: str = session.review_id
status: ReviewStatus = session.status
submitted_time: datetime = session.submitted_at

# Work with nested models
if session.state.critical_findings:
    for finding in session.state.critical_findings:
        finding_id: str = finding.finding_id
        severity: FindingSeverity = finding.severity
        confidence: float = finding.confidence
```

### Batch Operations

```python
# Submit multiple tools for review
tools_to_review = [tool1, tool2, tool3]
review_sessions = []

for tool in tools_to_review:
    request = ReviewSessionCreate(
        tool=tool,
        submitted_by="batch@example.com"
    )
    session = client.submit_tool_for_review(request)
    review_sessions.append(session)

print(f"Submitted {len(review_sessions)} tools for review")

# Monitor all sessions
for session in review_sessions:
    current_status = client.get_review_session(session.review_id)
    print(f"Tool {current_status.tool.name}: {current_status.status}")
```

## Testing

### Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=symbiont

# Run specific test file
pytest tests/test_client.py

# Run tests with verbose output
pytest -v
```

### Running Tests in Development

```bash
# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest
```

## Requirements

- Python 3.7+
- requests
- pydantic
- python-dotenv

## What's New in v0.2.0

- **Tool Review API**: Complete implementation of tool review workflows
- **Runtime API**: Agent management, workflow execution, and system metrics
- **Enhanced Models**: Comprehensive type definitions for all API responses  
- **Better Error Handling**: Specific exceptions for different error conditions
- **Improved Documentation**: Complete API reference with examples

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
