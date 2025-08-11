"""Data models for the Symbiont SDK."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentState(str, Enum):
    """Agent state enumeration."""
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"


class SecretBackendType(str, Enum):
    """Secret backend type enumeration."""
    VAULT = "vault"
    ENCRYPTED_FILE = "encrypted_file"
    OS_KEYCHAIN = "os_keychain"


class VaultAuthMethod(str, Enum):
    """Vault authentication method enumeration."""
    TOKEN = "token"  # nosec B105 - This is an enum value, not a password
    KUBERNETES = "kubernetes"
    AWS_IAM = "aws_iam"
    APPROLE = "approle"


class McpConnectionStatus(str, Enum):
    """MCP connection status enumeration."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    ERROR = "error"


class KnowledgeSourceType(str, Enum):
    """Knowledge source type enumeration."""
    DOCUMENT = "document"
    CODE = "code"
    API_REFERENCE = "api_reference"
    CONVERSATION = "conversation"


class ReviewStatus(str, Enum):
    """Review session status enumeration."""
    SUBMITTED = "submitted"
    PENDING_ANALYSIS = "pending_analysis"
    ANALYZING = "analyzing"
    PENDING_REVIEW = "pending_review"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SIGNED = "signed"


class FindingSeverity(str, Enum):
    """Security finding severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingCategory(str, Enum):
    """Security finding categories."""
    SCHEMA_INJECTION = "schema_injection"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXPOSURE = "data_exposure"
    MALICIOUS_CODE = "malicious_code"
    RESOURCE_ABUSE = "resource_abuse"


# =============================================================================
# Core Agent Models
# =============================================================================

class Agent(BaseModel):
    """Agent model for the Symbiont platform."""

    id: str
    name: str
    description: str
    system_prompt: str
    tools: List[str]
    model: str
    temperature: float
    top_p: float
    max_tokens: int


class ResourceUsage(BaseModel):
    """Resource usage information for agents."""
    memory_bytes: int = Field(..., description="Memory usage in bytes")
    cpu_percent: float = Field(..., description="CPU usage percentage")
    active_tasks: int = Field(..., description="Number of active tasks")


class AgentStatusResponse(BaseModel):
    """Response structure for agent status queries."""
    agent_id: str
    state: AgentState
    last_activity: datetime
    resource_usage: ResourceUsage


# =============================================================================
# Workflow Models
# =============================================================================

class WorkflowExecutionRequest(BaseModel):
    """Request structure for workflow execution."""
    workflow_id: str = Field(..., description="The workflow definition or identifier")
    parameters: Dict[str, Any] = Field(..., description="Parameters to pass to the workflow")
    agent_id: Optional[str] = Field(None, description="Optional agent ID to execute the workflow")


class WorkflowExecutionResponse(BaseModel):
    """Response structure for workflow execution."""
    execution_id: str
    status: str
    started_at: datetime
    result: Optional[Dict[str, Any]] = None


# =============================================================================
# Tool Review API Models
# =============================================================================

class ToolProvider(BaseModel):
    """Tool provider information."""
    name: str
    public_key_url: Optional[str] = None


class ToolSchema(BaseModel):
    """Tool schema definition."""
    type: str = "object"
    properties: Dict[str, Any]
    required: List[str] = []


class Tool(BaseModel):
    """Tool definition for review."""
    name: str
    description: str
    tool_schema: ToolSchema = Field(..., alias="schema")
    provider: ToolProvider


class SecurityFinding(BaseModel):
    """Security analysis finding."""
    finding_id: str
    severity: FindingSeverity
    category: FindingCategory
    title: str
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    recommendation: Optional[str] = None


class AnalysisResults(BaseModel):
    """Security analysis results."""
    analysis_id: str
    risk_score: int = Field(..., ge=0, le=100)
    findings: List[SecurityFinding]
    recommendations: List[str] = []
    completed_at: datetime


class ReviewSessionState(BaseModel):
    """Review session state information."""
    type: str
    analysis_id: Optional[str] = None
    analysis_completed_at: Optional[datetime] = None
    critical_findings: List[SecurityFinding] = []
    human_reviewer_id: Optional[str] = None
    review_started_at: Optional[datetime] = None


class ReviewSession(BaseModel):
    """Tool review session."""
    review_id: str
    tool: Tool
    status: ReviewStatus
    state: ReviewSessionState
    submitted_by: str
    submitted_at: datetime
    estimated_completion: Optional[datetime] = None
    priority: str = "normal"


class ReviewSessionCreate(BaseModel):
    """Request to create a new review session."""
    tool: Tool
    submitted_by: str
    priority: str = "normal"


class ReviewSessionResponse(BaseModel):
    """Response when creating a review session."""
    review_id: str
    status: ReviewStatus
    submitted_at: datetime
    estimated_completion: Optional[datetime] = None


class ReviewSessionList(BaseModel):
    """List of review sessions with pagination."""
    sessions: List[ReviewSession]
    pagination: Dict[str, Any]


class HumanReviewDecision(BaseModel):
    """Human reviewer decision."""
    decision: str  # "approve" or "reject"
    comments: Optional[str] = None
    reviewer_id: str


# =============================================================================
# System Models
# =============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    uptime_seconds: int
    timestamp: datetime
    version: str


class ErrorResponse(BaseModel):
    """Error response structure."""
    error: str
    code: str
    details: Optional[Dict[str, Any]] = None


class PaginationInfo(BaseModel):
    """Pagination information."""
    page: int
    limit: int
    total: int
    has_next: bool


# =============================================================================
# Signing Models
# =============================================================================

class SigningRequest(BaseModel):
    """Request to sign an approved tool."""
    review_id: str
    signing_key_id: str


class SigningResponse(BaseModel):
    """Response from signing operation."""
    signature: str
    signed_at: datetime
    signer_id: str
    signature_algorithm: str


class SignedTool(BaseModel):
    """Signed tool information."""
    tool: Tool
    signature: str
    signed_at: datetime
    signer_id: str
    signature_algorithm: str
    review_id: str


# =============================================================================
# Secrets Management Models
# =============================================================================

class VaultConfig(BaseModel):
    """HashiCorp Vault configuration."""
    url: str
    auth_method: VaultAuthMethod
    token: Optional[str] = None
    role_id: Optional[str] = None
    secret_id: Optional[str] = None
    kubernetes_role: Optional[str] = None
    aws_role: Optional[str] = None


class SecretBackendConfig(BaseModel):
    """Secret backend configuration."""
    backend_type: SecretBackendType
    vault_config: Optional[VaultConfig] = None
    file_path: Optional[str] = None
    encryption_key: Optional[str] = None


class SecretRequest(BaseModel):
    """Secret operation request."""
    agent_id: str
    secret_name: str
    secret_value: Optional[str] = None
    description: Optional[str] = None


class SecretResponse(BaseModel):
    """Secret operation response."""
    secret_name: str
    agent_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class SecretListResponse(BaseModel):
    """List secrets response."""
    secrets: List[str]
    agent_id: str


# =============================================================================
# MCP Management Models
# =============================================================================

class McpServerConfig(BaseModel):
    """MCP server configuration."""
    name: str
    command: List[str]
    env: Dict[str, str] = {}
    cwd: Optional[str] = None
    timeout_seconds: int = 30


class McpConnectionInfo(BaseModel):
    """MCP connection information."""
    server_name: str
    status: McpConnectionStatus
    pid: Optional[int] = None
    connected_at: Optional[datetime] = None
    last_error: Optional[str] = None
    tools_count: int = 0
    resources_count: int = 0


class McpToolInfo(BaseModel):
    """MCP tool information."""
    name: str
    description: str
    server_name: str
    tool_schema: Dict[str, Any] = Field(..., alias="schema")
    verified: bool = False
    verification_hash: Optional[str] = None


class McpResourceInfo(BaseModel):
    """MCP resource information."""
    uri: str
    name: Optional[str] = None
    description: Optional[str] = None
    mime_type: Optional[str] = None
    server_name: str


# =============================================================================
# Vector Database & RAG Models
# =============================================================================

class VectorMetadata(BaseModel):
    """Vector metadata for knowledge items."""
    source: str
    source_type: KnowledgeSourceType
    chunk_index: Optional[int] = None
    timestamp: datetime
    agent_id: Optional[str] = None


class KnowledgeItem(BaseModel):
    """Knowledge item for vector database."""
    id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: VectorMetadata


class VectorSearchRequest(BaseModel):
    """Vector similarity search request."""
    query: str
    agent_id: Optional[str] = None
    source_types: List[KnowledgeSourceType] = []
    limit: int = 10
    similarity_threshold: float = 0.7


class VectorSearchResult(BaseModel):
    """Vector search result."""
    item: KnowledgeItem
    similarity_score: float


class VectorSearchResponse(BaseModel):
    """Vector search response."""
    results: List[VectorSearchResult]
    query: str
    total_results: int


class ContextQuery(BaseModel):
    """Context query for RAG operations."""
    query: str
    agent_id: Optional[str] = None
    max_context_items: int = 5
    include_conversation_history: bool = True


class ContextResponse(BaseModel):
    """Context response from RAG system."""
    context_items: List[str]
    sources: List[str]
    query: str
    relevance_scores: List[float]


# =============================================================================
# Agent DSL Models
# =============================================================================

class DslCompileRequest(BaseModel):
    """DSL compilation request."""
    dsl_content: str
    agent_name: str
    validate_only: bool = False


class DslCompileResponse(BaseModel):
    """DSL compilation response."""
    success: bool
    agent_id: Optional[str] = None
    errors: List[str] = []
    warnings: List[str] = []
    compiled_at: datetime


class AgentDeployRequest(BaseModel):
    """Agent deployment request."""
    agent_id: str
    environment: str = "development"
    config_overrides: Dict[str, Any] = {}


class AgentDeployResponse(BaseModel):
    """Agent deployment response."""
    deployment_id: str
    agent_id: str
    status: str
    deployed_at: datetime
    endpoint_url: Optional[str] = None


# =============================================================================
# Enhanced Monitoring Models
# =============================================================================

class SystemMetrics(BaseModel):
    """Enhanced system metrics."""
    uptime_seconds: int
    memory_usage_bytes: int
    memory_usage_percent: float
    cpu_usage_percent: float
    disk_usage_bytes: int
    disk_usage_percent: float
    active_agents: int
    total_agents: int
    secrets_count: int
    mcp_connections: int
    vector_db_items: int


class AgentMetrics(BaseModel):
    """Agent-specific metrics."""
    agent_id: str
    tasks_completed: int
    tasks_failed: int
    average_response_time_ms: float
    memory_usage_bytes: int
    cpu_usage_percent: float
    last_activity: datetime
    uptime_seconds: int


# =============================================================================
# Configuration Models (Phase 1)
# =============================================================================

class ClientConfig(BaseModel):
    """Client configuration model."""
    api_key: Optional[str] = None
    base_url: str = "http://localhost:8080/api/v1"
    timeout: int = 30
    max_retries: int = 3
    enable_caching: bool = True
    enable_metrics: bool = True
    enable_debug: bool = False


class DatabaseConfig(BaseModel):
    """Database connection configuration."""
    host: str = "localhost"
    port: int = 5432
    database: str = "symbiont"
    username: Optional[str] = None
    password: Optional[str] = None
    ssl_mode: str = "prefer"
    connection_timeout: int = 30
    max_connections: int = 20


class AuthConfig(BaseModel):
    """Authentication configuration."""
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_seconds: int = 3600
    jwt_refresh_expiration_seconds: int = 86400
    api_key_header: str = "Authorization"
    enable_refresh_tokens: bool = True
    token_issuer: str = "symbiont"
    token_audience: str = "symbiont-api"


class VectorConfig(BaseModel):
    """Vector database configuration."""
    provider: str = "qdrant"
    host: str = "localhost"
    port: int = 6333
    collection_name: str = "symbiont_vectors"
    vector_size: int = 1536
    distance_metric: str = "cosine"
    enable_indexing: bool = True
    batch_size: int = 100


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    enable_console: bool = True
    enable_structured: bool = False
    max_file_size: str = "10MB"
    backup_count: int = 5


# =============================================================================
# Authentication Models (Phase 1)
# =============================================================================

class JWTToken(BaseModel):
    """JWT token model."""
    token: str
    token_type: str
    expires_at: datetime
    issued_at: datetime
    user_id: str
    roles: List[str] = []


class AuthResponse(BaseModel):
    """Authentication response."""
    user_id: str
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int
    roles: List[str] = []
    permissions: List[str] = []


class TokenRefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """Token refresh response."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class UserPermissions(BaseModel):
    """User permissions model."""
    user_id: str
    roles: List[str]
    permissions: List[str]
    is_active: bool = True


class RoleDefinition(BaseModel):
    """Role definition model."""
    name: str
    permissions: List[str]
    description: Optional[str] = None
    expires_at: Optional[datetime] = None


# =============================================================================
# HTTP Input Models
# =============================================================================

class RouteMatchType(str, Enum):
    """Route matching condition types."""
    PATH_PREFIX = "path_prefix"
    HEADER_EQUALS = "header_equals"
    JSON_FIELD_EQUALS = "json_field_equals"


class AgentRoutingRule(BaseModel):
    """Rule to route HTTP requests to specific agents."""
    condition_type: RouteMatchType
    condition_value: str
    condition_target: Optional[str] = None  # For header/field name
    agent_id: str


class HttpResponseControlConfig(BaseModel):
    """HTTP response control configuration."""
    default_status: int = 200
    agent_output_to_json: bool = True
    error_status: int = 500
    echo_input_on_error: bool = False


class HttpInputConfig(BaseModel):
    """HTTP input server configuration."""
    bind_address: str = "0.0.0.0"  # nosec B104 - This is a configuration default, not actual binding
    port: int = 8081
    path: str = "/webhook"
    agent_id: str
    auth_header: Optional[str] = None
    jwt_public_key_path: Optional[str] = None
    max_body_bytes: int = 65536
    concurrency: int = 10
    routing_rules: Optional[List[AgentRoutingRule]] = None
    response_control: Optional[HttpResponseControlConfig] = None
    forward_headers: List[str] = []
    cors_enabled: bool = False
    audit_enabled: bool = True


class HttpInputServerInfo(BaseModel):
    """HTTP input server status information."""
    server_id: str
    config: HttpInputConfig
    status: str  # "running", "stopped", "error"
    uptime_seconds: Optional[int] = None
    requests_processed: int = 0
    active_connections: int = 0
    last_error: Optional[str] = None


class HttpInputCreateRequest(BaseModel):
    """Request to create/start HTTP input server."""
    config: HttpInputConfig


class HttpInputUpdateRequest(BaseModel):
    """Request to update HTTP input server configuration."""
    server_id: str
    config: HttpInputConfig


class WebhookTriggerRequest(BaseModel):
    """Request to manually trigger webhook for testing."""
    server_id: str
    payload: Dict[str, Any]
    headers: Dict[str, str] = {}


class WebhookTriggerResponse(BaseModel):
    """Response from webhook trigger."""
    status: str
    response_code: int
    response_body: Dict[str, Any]
    processing_time_ms: float
    agent_id: str


# =============================================================================
# Phase 2 Memory System Models
# =============================================================================

class MemoryNode(BaseModel):
    """Individual memory item with metadata and content."""
    id: str = Field(..., description="Unique memory identifier")
    content: Dict[str, Any] = Field(..., description="Memory content")
    memory_type: str = Field(..., description="Type of memory (conversation, fact, experience, context, metadata)")
    memory_level: str = Field(..., description="Memory hierarchy level (short_term, long_term, episodic, semantic)")
    timestamp: datetime = Field(..., description="Memory creation timestamp")
    agent_id: str = Field(..., description="Agent that owns this memory")
    conversation_id: Optional[str] = Field(None, description="Associated conversation ID")
    parent_id: Optional[str] = Field(None, description="Parent memory ID")
    children_ids: List[str] = Field(default_factory=list, description="Child memory IDs")
    importance_score: float = Field(0.0, description="Memory importance score (0.0-1.0)")
    access_count: int = Field(0, description="Number of times memory was accessed")
    last_accessed: Optional[datetime] = Field(None, description="Last access timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class MemoryStoreRequest(BaseModel):
    """Request to store a memory."""
    content: Dict[str, Any] = Field(..., description="Memory content")
    memory_type: str = Field(..., description="Type of memory")
    memory_level: str = Field(..., description="Memory hierarchy level")
    agent_id: str = Field(..., description="Agent ID")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    importance_score: float = Field(0.0, description="Memory importance score")
    parent_id: Optional[str] = Field(None, description="Parent memory ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class MemoryResponse(BaseModel):
    """Response containing memory information."""
    memory: MemoryNode = Field(..., description="Memory node")
    success: bool = Field(True, description="Operation success status")
    message: Optional[str] = Field(None, description="Response message")


class MemoryQuery(BaseModel):
    """Query for retrieving specific memories."""
    memory_id: Optional[str] = Field(None, description="Specific memory ID")
    agent_id: str = Field(..., description="Agent ID")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    memory_type: Optional[str] = Field(None, description="Memory type filter")
    memory_level: Optional[str] = Field(None, description="Memory level filter")
    parent_id: Optional[str] = Field(None, description="Parent memory ID")
    limit: int = Field(50, description="Maximum number of results")


class MemorySearchRequest(BaseModel):
    """Request for searching memories."""
    agent_id: str = Field(..., description="Agent ID")
    query: Optional[Dict[str, Any]] = Field(None, description="Search query parameters")
    memory_levels: Optional[List[str]] = Field(None, description="Memory levels to search")
    content_contains: Optional[str] = Field(None, description="Content search string")
    importance_threshold: Optional[float] = Field(None, description="Minimum importance score")
    time_range: Optional[Dict[str, datetime]] = Field(None, description="Time range filter")
    limit: int = Field(50, description="Maximum number of results")


class MemorySearchResponse(BaseModel):
    """Response containing search results."""
    memories: List[MemoryNode] = Field(..., description="Found memories")
    total_count: int = Field(..., description="Total number of matches")
    search_time_ms: float = Field(..., description="Search execution time in milliseconds")
    success: bool = Field(True, description="Search success status")
    message: Optional[str] = Field(None, description="Response message")


class ConversationContext(BaseModel):
    """Conversation-specific memory context."""
    conversation_id: str = Field(..., description="Conversation identifier")
    agent_id: str = Field(..., description="Agent identifier")
    memories: List[MemoryNode] = Field(..., description="Conversation memories")
    context_summary: Optional[str] = Field(None, description="Context summary")
    created_at: datetime = Field(default_factory=datetime.now, description="Context creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context metadata")


class ConsolidationResponse(BaseModel):
    """Response from memory consolidation process."""
    agent_id: str = Field(..., description="Agent ID")
    promoted_count: int = Field(0, description="Number of memories promoted")
    pruned_count: int = Field(0, description="Number of memories pruned")
    consolidated_count: int = Field(0, description="Number of memories consolidated")
    execution_time_ms: float = Field(..., description="Consolidation execution time")
    success: bool = Field(True, description="Consolidation success status")
    message: Optional[str] = Field(None, description="Response message")


class MemorySearchResult(BaseModel):
    """Individual memory search result with relevance scoring."""
    memory: MemoryNode = Field(..., description="Memory node")
    relevance_score: float = Field(..., description="Relevance score for the search query")
    match_reason: str = Field(..., description="Reason for the match")
    highlighted_content: Optional[Dict[str, Any]] = Field(None, description="Content with search highlights")
