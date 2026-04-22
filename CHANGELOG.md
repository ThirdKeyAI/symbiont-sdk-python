# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.10.0] - 2026-04-22

### Added

#### HTTP Input LLM Invocation Models (Symbiont v1.10.0)
- **`WebhookInvocationRequest`** — Caller-supplied payload accepted by the
  HTTP Input endpoint: `prompt` or `message` (user text), optional
  `system_prompt` (capped at 4096 bytes by the runtime, truncated on a
  UTF-8 character boundary), plus pass-through of additional fields.
- **`WebhookToolRun`** — Per-tool ORGA execution preview (`tool`, `input`,
  `output_preview`). `output_preview` is UTF-8 safe and truncated to at
  most 500 bytes by the runtime.
- **`WebhookExecutionStartedResponse`** — Returned when the target agent is
  in the `Running` state and the request is dispatched on the communication
  bus (`status: "execution_started"` with `agent_id`, `message_id`,
  `latency_ms`, `timestamp`).
- **`WebhookCompletedResponse`** — Returned when the agent is not running
  and the request is served by the on-demand LLM invocation path, which
  runs an ORGA tool-calling loop against ToolClad manifests
  (`status: "completed"` with `response`, `tool_runs`, `model`, `provider`,
  `latency_ms`, `timestamp`).
- **`WebhookInvocationResponse`** — Discriminated union alias
  (`Union[WebhookExecutionStartedResponse, WebhookCompletedResponse]`).
- **`WebhookInvocationStatus`** — String enum with
  `EXECUTION_STARTED` and `COMPLETED`.

### Changed
- Version alignment with Symbiont runtime v1.10.0.
- Package version bumped to 1.10.0 in `setup.py` and
  `symbiont.__version__`.

### Notes
- Symbiont v1.9.0 and v1.9.1 introduced ToolClad v0.4.0 runtime features
  (session / browser execution modes, HTTP and MCP proxy backends, output
  parsers, custom types, secrets injection, W3C `traceparent` propagation,
  bounded channels, rate limiting, optional LanceDB feature flag). These
  changes are runtime-side; existing SDK models (`ToolManifestInfo`,
  `ToolExecutionResult`, etc.) remain backward compatible. The `backend`
  string on `ToolManifestInfo` now accepts `"http"`, `"mcp"`, `"session"`,
  and `"browser"` in addition to previously documented values.

---

## [1.8.1] - 2026-03-23

### Added

#### ToolClad Manifest Management
- **ToolCladClient** — Full client for ToolClad manifest operations via `client.toolclad`
  - `list_tools()` — List all discovered `.clad.toml` manifests
  - `validate_manifest()` — Validate a manifest file
  - `test_tool()` — Dry-run a tool (no execution)
  - `get_schema()` — Get MCP-compatible JSON schema for a tool
  - `execute_tool()` — Execute a tool with validated arguments, returns evidence envelope
  - `get_tool_info()` — Get detailed tool manifest information
  - `reload_tools()` — Trigger hot-reload of tool manifests
- **Pydantic models**: `ToolManifestInfo`, `ToolValidationResult`, `ToolTestResult`, `ToolExecutionResult`

#### Inter-Agent Communication Policy Gate
- `list_communication_rules()` — List all communication policy rules
- `add_communication_rule()` — Add a policy rule (allow/deny between agents)
- `remove_communication_rule()` — Remove a rule by ID
- `evaluate_communication()` — Evaluate whether a communication is allowed
- **Pydantic models**: `CommunicationRule`, `CommunicationEvaluation`

#### Agent Lifecycle
- `delete_agent()` — Delete an agent and its metadata
- `re_execute_agent()` — Re-execute an agent with optional new input (resets ORGA loop)

#### ORGA-Adaptive Features
- `reasoning.get_tool_profiles()` — Tool execution timing statistics and success rates
- `reasoning.get_loop_diagnostics()` — Stuck-loop detection, iteration history, adaptive parameters

### Changed
- Version alignment with Symbiont runtime v1.8.1

---

## [1.6.1] - 2026-02-28

### Added

#### Reasoning Loop APIs
- **ReasoningClient** — Full ORGA (Observe–Reason–Ground–Act) cycle client with 15 methods
- Cedar policy evaluation, journal system, circuit breakers, knowledge bridge
- Pydantic models with enums for all reasoning types

### Changed
- Version alignment with Symbiont runtime v1.6.1

---

## [0.6.0] - 2026-02-15

### Added

#### Markdown Memory Persistence
- **MarkdownMemoryStore** — File-based agent context persistence using markdown format
  - `save_context()` / `load_context()` — Atomic save with daily log files
  - `delete_context()` / `list_agent_contexts()` — Context lifecycle management
  - `compact()` — Remove log files older than retention period
  - `get_storage_stats()` — Storage statistics across all agents

#### Webhook Verification
- **HmacVerifier** — HMAC-SHA256 webhook signature verification with prefix stripping
- **JwtVerifier** — JWT-based webhook verification with optional issuer validation
- **WebhookProvider** — Pre-configured providers (GitHub, Stripe, Slack, Custom) with factory method
- **SignatureVerifier** ABC for custom verifier implementations

#### Agent Skills (ClawHavoc Scanning + Loading)
- **SkillScanner** — Security scanning with 10 built-in ClawHavoc rules and custom rule support
  - Detects pipe-to-shell, wget-pipe-to-shell, env file references, SOUL.md/memory.md tampering, eval+fetch, base64-decode-exec, rm-rf, chmod-777
- **SkillLoader** — Skill discovery and loading from configured paths
  - YAML frontmatter parsing for skill metadata
  - Optional SchemaPin signature verification (soft dependency)
  - Configurable scan-on-load behavior

#### Metrics Collection & Export
- **MetricsClient** — Sub-client for runtime metrics API (`GET /metrics/snapshot`, etc.)
- **FileMetricsExporter** — Atomic JSON file export with compact mode
- **OtlpExporter** — OTLP export stub (requires `opentelemetry-api`)
- **CompositeExporter** — Fan-out to multiple export backends
- **MetricsCollector** — Background thread for periodic metrics export
- **MetricsSnapshot** — Serializable snapshot with scheduler, task manager, load balancer, and system metrics

#### New Exceptions
- `WebhookVerificationError`, `SkillLoadError`, `SkillScanError`, `MetricsExportError`, `MetricsConfigError`

#### New Pydantic Models
- Webhook: `WebhookProviderType`, `WebhookVerificationConfig`
- Skills: `SignatureStatusType`, `ScanSeverityType`, `ScanFindingModel`, `ScanResultModel`, `SkillMetadataModel`, `LoadedSkillModel`, `SkillsConfig`
- Metrics: `OtlpProtocol`, `OtlpConfig`, `FileMetricsConfig`, `MetricsConfig`, `SchedulerMetricsSnapshot`, `TaskManagerMetricsSnapshot`, `LoadBalancerMetricsSnapshot`, `SystemResourceMetricsSnapshot`, `MetricsSnapshot`

#### Optional Dependencies
- `skills` extra: `schemapin>=0.2.0`
- `metrics` extra: `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`

### Changed
- Aligned with Symbiont Runtime v1.4.0
- `Client.metrics_client` property — Lazy-loaded `MetricsClient` sub-client
- All new types exported from `symbiont` package

---

## [0.5.0] - 2026-02-11

### Added

#### AgentPin Integration
- **AgentPinClient** — Client-side credential verification, discovery, and trust bundle support via `agentpin` PyPI package (v0.2.0)
  - `client.agentpin.verify_credential()` — Full 12-step online verification
  - `client.agentpin.verify_credential_offline()` — Offline verification with pre-fetched documents
  - `client.agentpin.verify_credential_with_bundle()` — Trust bundle-based verification (no network)
  - `client.agentpin.fetch_discovery_document()` — Fetch `.well-known/agent-identity.json`
  - `client.agentpin.issue_credential()` — Issue ES256 JWT credentials
  - `client.agentpin.generate_key_pair()` — P-256 key generation
  - Key pinning (TOFU) and JWK utilities
- **`Client.agentpin` property** — Lazy-loaded `AgentPinClient` accessible directly from the main `Client` instance
- **AgentPinClient export** in `symbiont` package

### Changed
- Aligned with Symbiont v1.0.1 release

### Fixed
- Fixed `setup.py` version drift (was stuck at 0.2.0, now matches `__version__`)

---

## [0.4.0] - 2026-02-07

### Added

#### Scheduling Parity & API Alignment
- **SchedulerHealthResponse** — New dataclass for the 13-field `GET /health/scheduler` endpoint
- **`get_scheduler_health()`** — New method on `ScheduleClient` to query scheduler health
- **`Client.schedules` property** — Lazy-loaded `ScheduleClient` accessible directly from the main `Client` instance
- **Schedule type exports** — All schedule dataclasses now exported from `symbiont` package (`CreateScheduleRequest`, `ScheduleSummary`, `ScheduleDetail`, `SchedulerHealthResponse`, etc.)

#### Test Coverage
- **ScheduleClient tests** — 18 test cases covering all 11 methods (list, create, get, update, delete, pause, resume, trigger, history, next-runs, scheduler-health) plus edge cases

---

## [0.3.1] - 2025-01-16

### Added
- ScheduleClient for cron schedule management API
- Test compatibility fixes for enhanced Client class

## [0.3.0] and earlier

See previous releases for historical changes.
