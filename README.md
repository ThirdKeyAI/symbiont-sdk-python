# Symbiont Python SDK

A Python SDK for interacting with the Symbiont Agent Runtime System, providing a streamlined interface for building AI-powered applications with agent capabilities.

## Overview

The Symbiont Python SDK enables developers to integrate with the Symbiont platform, which provides intelligent agent runtime capabilities. This SDK handles authentication, HTTP requests, error handling, and provides typed models for working with Symbiont agents and related resources.

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
| `SYMBIONT_API_BASE_URL` | Alternative API base URL for OpenAI-compatible APIs | `https://api.openai.com/v1` |
| `SYMBIONT_DEFAULT_MODEL` | Default model to use | `gpt-3.5-turbo` |
| `SYMBIONT_ORG_ID` | Organization ID (optional, for OpenAI) | None |
| `SYMBIONT_TIMEOUT` | Request timeout in seconds | `30` |
| `SYMBIONT_MAX_RETRIES` | Maximum retries for API calls | `3` |

### Example `.env` Configuration

```env
# API Configuration
SYMBIONT_API_KEY=your_api_key_here
SYMBIONT_BASE_URL=http://localhost:8080/api/v1

# Optional Settings
SYMBIONT_DEFAULT_MODEL=gpt-3.5-turbo
SYMBIONT_TIMEOUT=30
SYMBIONT_MAX_RETRIES=3
```

## Usage

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

### Making API Requests

Here's a basic example of how to use the client (using a hypothetical `get_agent` method):

```python
from symbiont import Client
from symbiont.models import Agent

# Initialize the client
client = Client()

# Example: Get an agent by ID
try:
    response = client._request("GET", "agents/agent-123")
    agent_data = response.json()
    
    # Create an Agent model from the response
    agent = Agent(**agent_data)
    print(f"Agent: {agent.name}")
    print(f"Description: {agent.description}")
    print(f"Model: {agent.model}")
    
except Exception as e:
    print(f"Error: {e}")
```

### Working with Models

The SDK provides typed models for structured data:

```python
from symbiont.models import Agent

# Create an agent instance
agent = Agent(
    id="agent-123",
    name="My Assistant",
    description="A helpful AI assistant",
    system_prompt="You are a helpful assistant.",
    tools=["web_search", "calculator"],
    model="gpt-3.5-turbo",
    temperature=0.7,
    top_p=0.9,
    max_tokens=1000
)

print(agent.name)  # "My Assistant"
print(agent.tools)  # ["web_search", "calculator"]
```

## Error Handling

The SDK provides specific exception classes for different types of errors:

```python
from symbiont import Client
from symbiont.exceptions import (
    APIError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    SymbiontError
)

client = Client()

try:
    # Make an API request
    response = client._request("GET", "agents/non-existent-agent")
    
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

The test suite includes unit tests for the client, models, and exception handling. Make sure to set up your environment properly before running tests:

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

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
