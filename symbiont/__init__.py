"""Symbiont Python SDK."""

from dotenv import load_dotenv

from .client import Client
from .exceptions import (
    APIError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    SymbiontError,
)
from .models import (
    # Core Agent Models
    Agent,
    AgentState,
    AgentStatusResponse,
    AnalysisResults,
    ErrorResponse,
    FindingCategory,
    FindingSeverity,
    # System Models
    HealthResponse,
    HumanReviewDecision,
    PaginationInfo,
    ResourceUsage,
    ReviewSession,
    ReviewSessionCreate,
    ReviewSessionList,
    ReviewSessionResponse,
    ReviewSessionState,
    ReviewStatus,
    SecurityFinding,
    SignedTool,
    SigningRequest,
    SigningResponse,
    # Tool Review Models
    Tool,
    ToolProvider,
    ToolSchema,
    # Workflow Models
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
)

# Load environment variables from .env file
load_dotenv()

__version__ = "0.2.0"

__all__ = [
    # Client
    'Client',

    # Core Agent Models
    'Agent', 'AgentState', 'ResourceUsage', 'AgentStatusResponse',

    # Workflow Models
    'WorkflowExecutionRequest', 'WorkflowExecutionResponse',

    # Tool Review Models
    'Tool', 'ToolProvider', 'ToolSchema',
    'ReviewStatus', 'ReviewSession', 'ReviewSessionCreate', 'ReviewSessionResponse', 'ReviewSessionList',
    'SecurityFinding', 'FindingSeverity', 'FindingCategory', 'AnalysisResults',
    'ReviewSessionState', 'HumanReviewDecision',
    'SigningRequest', 'SigningResponse', 'SignedTool',

    # System Models
    'HealthResponse', 'ErrorResponse', 'PaginationInfo',

    # Exceptions
    'SymbiontError',
    'APIError',
    'AuthenticationError',
    'NotFoundError',
    'RateLimitError',
]
