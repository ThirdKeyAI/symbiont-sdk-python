"""Symbiont Python SDK."""

from dotenv import load_dotenv

from .agentpin import AgentPinClient
from .client import Client
from .exceptions import (
    APIError,
    AuthenticationError,
    MetricsConfigError,
    MetricsExportError,
    NotFoundError,
    RateLimitError,
    SkillLoadError,
    SkillScanError,
    SymbiontError,
    WebhookVerificationError,
)
from .markdown_memory import AgentMemoryContext, MarkdownMemoryStore, StorageStats
from .metrics import (
    CompositeExporter,
    FileMetricsExporter,
    MetricsClient,
    MetricsCollector,
    MetricsSnapshot,
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
    # Communication Policy Models
    CommunicationEvaluation,
    CommunicationRule,
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
    # ToolClad Models
    ToolExecutionResult,
    ToolManifestInfo,
    ToolProvider,
    ToolSchema,
    ToolTestResult,
    ToolValidationResult,
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
from .reasoning import (
    CedarPolicy,
    CircuitBreakerConfig,
    CircuitBreakerStatus,
    CircuitState,
    FinishReason,
    InferenceOptions,
    InferenceResponse,
    JournalEntry,
    KnowledgeConfig,
    LoopConfig,
    LoopDecision,
    LoopDecisionType,
    LoopEvent,
    LoopEventType,
    LoopResult,
    LoopState,
    Observation,
    ProposedAction,
    ProposedActionType,
    RecoveryStrategy,
    RecoveryStrategyType,
    RunReasoningLoopRequest,
    RunReasoningLoopResponse,
    TerminationReason,
    TerminationReasonType,
    ToolCallRequest,
    ToolDefinition,
    Usage,
)
from .reasoning_client import ReasoningClient
from .schedules import (
    CreateScheduleRequest,
    CreateScheduleResponse,
    DeleteScheduleResponse,
    NextRunsResponse,
    ScheduleActionResponse,
    ScheduleClient,
    ScheduleDetail,
    ScheduleHistoryResponse,
    SchedulerHealthResponse,
    ScheduleRunEntry,
    ScheduleSummary,
    UpdateScheduleRequest,
)
from .skills import (
    LoadedSkill,
    ScanFinding,
    ScanResult,
    ScanSeverity,
    SignatureStatus,
    SkillLoader,
    SkillLoaderConfig,
    SkillMetadata,
    SkillScanner,
)
from .toolclad import ToolCladClient
from .webhooks import HmacVerifier, JwtVerifier, SignatureVerifier, WebhookProvider

# Load environment variables from .env file
load_dotenv()

__version__ = "1.8.1"

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

    # AgentPin
    'AgentPinClient',

    # Schedule Models
    'ScheduleClient',
    'CreateScheduleRequest', 'CreateScheduleResponse',
    'UpdateScheduleRequest',
    'ScheduleSummary', 'ScheduleDetail', 'ScheduleRunEntry',
    'ScheduleHistoryResponse', 'NextRunsResponse',
    'ScheduleActionResponse', 'DeleteScheduleResponse',
    'SchedulerHealthResponse',

    # Webhook Verification
    'WebhookProvider', 'HmacVerifier', 'JwtVerifier', 'SignatureVerifier',

    # Markdown Memory
    'MarkdownMemoryStore', 'AgentMemoryContext', 'StorageStats',

    # Skills
    'SkillLoader', 'SkillScanner', 'LoadedSkill', 'ScanResult', 'ScanFinding',
    'ScanSeverity', 'SignatureStatus', 'SkillLoaderConfig', 'SkillMetadata',

    # Metrics
    'MetricsClient', 'MetricsCollector', 'MetricsSnapshot',
    'FileMetricsExporter', 'CompositeExporter',

    # ToolClad
    'ToolCladClient',
    'ToolManifestInfo', 'ToolValidationResult', 'ToolTestResult', 'ToolExecutionResult',

    # Communication Policy
    'CommunicationRule', 'CommunicationEvaluation',

    # Reasoning Loop
    'ReasoningClient',
    'Usage', 'ToolDefinition', 'ToolCallRequest',
    'FinishReason', 'InferenceOptions', 'InferenceResponse',
    'Observation', 'ProposedAction', 'ProposedActionType',
    'LoopDecision', 'LoopDecisionType',
    'RecoveryStrategy', 'RecoveryStrategyType',
    'TerminationReason', 'TerminationReasonType',
    'LoopConfig', 'LoopState', 'LoopResult',
    'LoopEvent', 'LoopEventType', 'JournalEntry',
    'CedarPolicy', 'KnowledgeConfig',
    'CircuitState', 'CircuitBreakerConfig', 'CircuitBreakerStatus',
    'RunReasoningLoopRequest', 'RunReasoningLoopResponse',

    # Exceptions
    'SymbiontError',
    'APIError',
    'AuthenticationError',
    'NotFoundError',
    'RateLimitError',
    'WebhookVerificationError',
    'SkillLoadError',
    'SkillScanError',
    'MetricsExportError',
    'MetricsConfigError',
]
