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
    AgentDeployRequest,
    AgentDeployResponse,
    AgentMetrics,
    AgentRoutingRule,
    AgentState,
    AgentStatusResponse,
    AnalysisResults,
    ContextQuery,
    ContextResponse,
    # Agent DSL Models
    DslCompileRequest,
    DslCompileResponse,
    ErrorResponse,
    FindingCategory,
    FindingSeverity,
    # System Models
    HealthResponse,
    HttpInputConfig,
    HttpInputCreateRequest,
    HttpInputServerInfo,
    HttpInputUpdateRequest,
    HttpResponseControlConfig,
    HumanReviewDecision,
    KnowledgeItem,
    # Vector Database & RAG Models
    KnowledgeSourceType,
    McpConnectionInfo,
    # MCP Management Models
    McpConnectionStatus,
    McpResourceInfo,
    McpServerConfig,
    McpToolInfo,
    PaginationInfo,
    ResourceUsage,
    ReviewSession,
    ReviewSessionCreate,
    ReviewSessionList,
    ReviewSessionResponse,
    ReviewSessionState,
    ReviewStatus,
    # HTTP Input Models
    RouteMatchType,
    SecretBackendConfig,
    # Secrets Management Models
    SecretBackendType,
    SecretListResponse,
    SecretRequest,
    SecretResponse,
    SecurityFinding,
    SignedTool,
    SigningRequest,
    SigningResponse,
    SystemMetrics,
    # Tool Review Models
    Tool,
    ToolProvider,
    ToolSchema,
    VaultAuthMethod,
    VaultConfig,
    VectorMetadata,
    VectorSearchRequest,
    VectorSearchResponse,
    VectorSearchResult,
    WebhookTriggerRequest,
    WebhookTriggerResponse,
    # Workflow Models
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
)

# Load environment variables from .env file
load_dotenv()

__version__ = "0.3.0"

__all__ = [
    # Client
    'Client',

    # Core Agent Models
    'Agent', 'AgentState', 'ResourceUsage', 'AgentStatusResponse', 'AgentMetrics',

    # Workflow Models
    'WorkflowExecutionRequest', 'WorkflowExecutionResponse',

    # Tool Review Models
    'Tool', 'ToolProvider', 'ToolSchema',
    'ReviewStatus', 'ReviewSession', 'ReviewSessionCreate', 'ReviewSessionResponse', 'ReviewSessionList',
    'SecurityFinding', 'FindingSeverity', 'FindingCategory', 'AnalysisResults',
    'ReviewSessionState', 'HumanReviewDecision',
    'SigningRequest', 'SigningResponse', 'SignedTool',

    # System Models
    'HealthResponse', 'ErrorResponse', 'PaginationInfo', 'SystemMetrics',

    # Secrets Management Models
    'SecretBackendType', 'SecretBackendConfig', 'SecretRequest', 'SecretResponse', 'SecretListResponse',
    'VaultAuthMethod', 'VaultConfig',

    # MCP Management Models
    'McpConnectionStatus', 'McpServerConfig', 'McpConnectionInfo', 'McpToolInfo', 'McpResourceInfo',

    # Vector Database & RAG Models
    'KnowledgeSourceType', 'VectorMetadata', 'KnowledgeItem',
    'VectorSearchRequest', 'VectorSearchResult', 'VectorSearchResponse',
    'ContextQuery', 'ContextResponse',

    # Agent DSL Models
    'DslCompileRequest', 'DslCompileResponse', 'AgentDeployRequest', 'AgentDeployResponse',

    # HTTP Input Models
    'RouteMatchType', 'AgentRoutingRule', 'HttpResponseControlConfig',
    'HttpInputConfig', 'HttpInputServerInfo', 'HttpInputCreateRequest', 'HttpInputUpdateRequest',
    'WebhookTriggerRequest', 'WebhookTriggerResponse',

    # Exceptions
    'SymbiontError',
    'APIError',
    'AuthenticationError',
    'NotFoundError',
    'RateLimitError',
]
