<img src="https://raw.githubusercontent.com/ThirdKeyAI/Symbiont/main/logo-hz.png" alt="Symbiont">

[![PyPI](https://img.shields.io/pypi/v/symbiont-sdk.svg)](https://pypi.org/project/symbiont-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/symbiont-sdk.svg)](https://pypi.org/project/symbiont-sdk/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-online-brightgreen)](https://docs.symbiont.dev)

---

**Official Python SDK for Symbiont, the policy-governed agent runtime.**
*Same agent. Secure runtime.*

This SDK is the integration surface for the [Symbiont runtime](https://github.com/thirdkeyai/symbiont). Use it from any Python application to manage agents, drive scheduled and channel-bound execution, run the ORGA reasoning loop, register ToolClad-governed tools, evaluate the Communication Policy Gate, verify webhooks, and integrate AgentPin identity — all against a runtime that enforces Cedar policy, SchemaPin tool verification, and tamper-evident audit logging.

The runtime decides what an agent may do. The SDK decides how your application talks to the runtime.

---

## Why Symbiont

AI agents are easy to demo and hard to trust. Once an agent can call tools, access files, send messages, or invoke external services, you need more than prompts and glue code. You need:

- **Policy enforcement** for what an agent may do — built-in DSL and [Cedar](https://www.cedarpolicy.com/) authorization
- **Tool verification** so execution is not blind trust — [SchemaPin](https://github.com/ThirdKeyAI/SchemaPin) cryptographic verification of MCP tools
- **Tool contracts** for how tools execute — [ToolClad](https://github.com/ThirdKeyAI/ToolClad) declarative input validation, scope enforcement, and injection prevention
- **Agent identity** so you know who is acting — [AgentPin](https://github.com/ThirdKeyAI/AgentPin) domain-anchored ES256 identity
- **Audit trails** for what happened and why — cryptographically tamper-evident logs
- **Approval gates** for sensitive actions — human review before execution when policy requires it

Symbiont is the runtime that enforces all of this. This SDK is the typed, ergonomic way to drive it from Python.

---

## Quick start

### Prerequisites

A running Symbiont runtime is required. The fastest way:

```bash
# Start the runtime (API on :8080, HTTP input on :8081)
docker run --rm -p 8080:8080 -p 8081:8081 ghcr.io/thirdkeyai/symbi:latest up
```

For Homebrew, install scripts, building from source, or production deployment, see the [getting-started guide](https://docs.symbiont.dev/getting-started).

### Install

```bash
pip install symbiont-sdk
```

Requires Python 3.8+.

### Hello, runtime

```python
from symbiont import Client

client = Client(
    api_key="...",                                # or SYMBIONT_API_KEY
    base_url="http://localhost:8080/api/v1",      # or SYMBIONT_BASE_URL
)

print(client.health_check())

# List agents and inspect status
for agent_id in client.list_agents():
    status = client.get_agent_status(agent_id)
    print(agent_id, status.state, status.resource_usage)
```

---

## Capabilities

The main `Client` exposes runtime functionality directly and through namespaced sub-clients.

| Surface | What it covers |
|---------|----------------|
| `Client` (agents, workflows) | Agent lifecycle (create, execute, re-execute, delete, list, status, history) and workflow execution |
| `client.reasoning` | ORGA loop control, journal, Cedar policies, circuit breakers, knowledge bridge, tool profiles, loop diagnostics |
| `client.toolclad` | ToolClad manifests — list, validate, test, execute, schema, hot reload |
| `client` (communication) | `list_communication_rules`, `add_communication_rule`, `remove_communication_rule`, `evaluate_communication` |
| `client.agentpin` | Client-side AgentPin keygen, credential issuance and verification, discovery, key pinning, trust bundles |
| `ScheduleClient` | Cron schedules with pause/resume/trigger and run history |
| `ChannelClient` | Slack / Teams / Mattermost adapters, mappings, audit |
| `client.metrics_client` (`MetricsClient`) + exporters | Snapshots, file export, OTLP, periodic background collection |
| `MarkdownMemoryStore` | File-based agent context that survives restarts |
| `SkillScanner` / `SkillLoader` | 10 built-in ClawHavoc rules; YAML frontmatter; SchemaPin signature status |
| `HmacVerifier` / `JwtVerifier` / `WebhookProvider` | Inbound webhook signature verification |

All response payloads are Pydantic models with full type coverage.

---

## Trust Stack integration

The SDK exposes the runtime features that enforce the Symbiont Trust Stack:

- **Cedar policies** via `client.reasoning.add_cedar_policy()` and `list_cedar_policies()` — fine-grained authorization for every agent action
- **AgentPin** via `client.agentpin.*` — domain-anchored ES256 credential issuance and verification, runs entirely client-side (no runtime required)
- **ToolClad** via `client.toolclad.*` — declarative tool manifests with argument validation, scope enforcement, and Cedar policy generation; supports `oneshot`, `session`, `browser`, `http`, and `mcp-proxy` backends as of Symbiont v1.10.0
- **Communication Policy Gate** via `client.evaluate_communication()` and rule management — Cedar-evaluated allow/deny rules for inter-agent messages
- **SchemaPin** — enforced server-side; tool signatures are verified before tool execution

Model output is never treated as execution authority. The runtime controls what actually happens.

---

## Examples

### Reasoning loop

Run an autonomous Observe-Reason-Gate-Act cycle with policy gates, circuit breakers, and journal replay:

```python
from symbiont import Client, RunReasoningLoopRequest, LoopConfig, CedarPolicy

client = Client()

response = client.reasoning.run_loop(
    "agent-1",
    RunReasoningLoopRequest(
        config=LoopConfig(max_iterations=10, timeout_ms=60000),
        initial_message="Analyze the latest sales data and create a report.",
    ),
)
print(response.result.output, response.result.iterations)

# Read journal entries for replay/audit
journal = client.reasoning.get_journal_entries("agent-1", limit=50)

# Add an action-level Cedar policy
client.reasoning.add_cedar_policy("agent-1", CedarPolicy(
    name="deny-file-write",
    source='forbid(principal, action == "tool_call", resource) when { resource.name == "write_file" };',
    active=True,
))

# Inspect circuit breakers and adaptive parameters
breakers = client.reasoning.get_circuit_breaker_status("agent-1")
profiles = client.reasoning.get_tool_profiles("agent-1")
```

### ToolClad — governed tool execution

Tools are declared in `.clad.toml` manifests with argument validation, scope enforcement, and Cedar policy generation. Drive them from the SDK:

```python
tools = client.toolclad.list_tools()
schema = client.toolclad.get_schema("nmap")

result = client.toolclad.execute_tool("nmap", {"target": "10.0.0.1"})
print(result["status"], result["scan_id"], result["exit_code"])

# Hot reload after editing a manifest on disk
client.toolclad.reload_tools()
```

### Communication Policy Gate

```python
client.add_communication_rule({
    "from_agent": "analyst",
    "to_agent": "reporter",
    "action": "allow",
    "priority": 10,
    "max_depth": 3,
})

decision = client.evaluate_communication(
    sender="analyst",
    recipient="reporter",
    action="send_message",
)
print(decision["allowed"], decision.get("rule"), decision.get("reason"))
```

### AgentPin — client-side identity

AgentPin operations run client-side; no Symbiont runtime is required.

```python
keys = client.agentpin.generate_key_pair()
kid = client.agentpin.generate_key_id(keys.public_key_pem)

jwt = client.agentpin.issue_credential(
    private_key_pem=keys.private_key_pem,
    kid=kid,
    issuer="example.com",
    agent_id="data-analyzer",
    capabilities=["read:data", "write:reports"],
    ttl_secs=3600,
)

# Online verification (12-step: discovery, key pinning, signature, claims, expiry)
result = client.agentpin.verify_credential(jwt)
print(result.valid, result.agent_id, result.capabilities)
```

### HTTP Input invocation (Symbiont v1.10.0)

The runtime's HTTP Input handler dispatches webhooks to a running agent on the communication bus, or falls back to an on-demand LLM ORGA loop against ToolClad manifests when the agent is not running. The SDK ships typed responses for both shapes:

```python
from symbiont import (
    WebhookInvocationRequest,
    WebhookInvocationResponse,
    WebhookCompletedResponse,
    WebhookExecutionStartedResponse,
    WebhookInvocationStatus,
)

# Build a request
req = WebhookInvocationRequest(prompt="scan target 10.0.0.1", target="10.0.0.1")

# Parse a response from your runtime's HTTP Input endpoint
def handle(payload: dict) -> None:
    if payload["status"] == WebhookInvocationStatus.EXECUTION_STARTED.value:
        resp = WebhookExecutionStartedResponse(**payload)
        print("dispatched", resp.message_id, "in", resp.latency_ms, "ms")
    else:
        resp = WebhookCompletedResponse(**payload)
        print("LLM completed via", resp.provider, resp.model)
        for run in resp.tool_runs:
            print(" -", run.tool, run.output_preview)
```

### Webhook signature verification

```python
from symbiont import WebhookProvider, HmacVerifier, JwtVerifier

# Provider preset (GitHub, Stripe, Slack, custom)
verifier = WebhookProvider.GITHUB.verifier(secret=b"your-secret")
verifier.verify(request.headers, request.body)

# Manual HMAC with prefix stripping
hmac = HmacVerifier(secret=b"your-secret", header_name="X-Hub-Signature-256", prefix="sha256=")
hmac.verify(headers, body)

# JWT-based verification
jwt_v = JwtVerifier(secret=b"your-secret", header_name="Authorization", required_issuer="expected-issuer")
jwt_v.verify(headers, body)
```

### Markdown memory persistence

```python
from symbiont import MarkdownMemoryStore, AgentMemoryContext

store = MarkdownMemoryStore("/data/memory", retention_days=30)
store.save_context("agent-1", AgentMemoryContext(
    agent_id="agent-1",
    facts=["User prefers dark mode"],
    procedures=["Always greet by name"],
    learned_patterns=["Responds better to bullet points"],
    metadata={"last_session": "2026-02-15"},
))
context = store.load_context("agent-1")
```

### Agent skills — ClawHavoc scanning

```python
from symbiont import SkillScanner, SkillLoader, SkillLoaderConfig

# 10 built-in ClawHavoc rules (pipe-to-shell, eval+fetch, base64-decode-exec, etc.)
scanner = SkillScanner()
findings = scanner.scan_content(content, "SKILL.md")

loader = SkillLoader(SkillLoaderConfig(
    load_paths=["/skills/verified", "/skills/community"],
    require_signed=False,
    scan_enabled=True,
))
skills = loader.load_all()
```

### Metrics export

```python
from symbiont import Client, MetricsCollector, FileMetricsExporter, CompositeExporter

client = Client()
snapshot = client.metrics_client.get_metrics_snapshot()

exporter = CompositeExporter([FileMetricsExporter("/var/log/symbiont/metrics.json")])
collector = MetricsCollector(client.metrics_client, exporter, interval_seconds=60)
collector.start()
```

---

## Configuration

### Environment

```bash
SYMBIONT_API_KEY=...                            # required
SYMBIONT_BASE_URL=http://localhost:8080/api/v1
SYMBIONT_VALIDATION_MODE=strict
```

### Programmatic

```python
from symbiont import Client

client = Client(
    api_key="...",
    base_url="http://localhost:8080/api/v1",
    timeout=30,
    validation_mode="strict",
)
```

The SDK uses `pydantic-settings`, so configuration may also be loaded from a `.env` file or a YAML config. See the [API reference](https://docs.symbiont.dev/api-reference) for the full surface.

---

## Docker

The SDK is published as a container image:

```bash
docker pull ghcr.io/thirdkeyai/symbiont-sdk-python:latest

# Interactive REPL
docker run -it --rm \
  -e SYMBIONT_API_KEY=... \
  -e SYMBIONT_BASE_URL=http://host.docker.internal:8080/api/v1 \
  ghcr.io/thirdkeyai/symbiont-sdk-python:latest

# Run a script from the host
docker run --rm -v "$(pwd):/workspace" -w /workspace \
  -e SYMBIONT_API_KEY=... \
  ghcr.io/thirdkeyai/symbiont-sdk-python:latest python your_script.py
```

---

## Documentation

- [Getting started](https://docs.symbiont.dev/getting-started)
- [Security model](https://docs.symbiont.dev/security-model)
- [Runtime architecture](https://docs.symbiont.dev/runtime-architecture)
- [Reasoning loop guide](https://docs.symbiont.dev/reasoning-loop)
- [DSL guide](https://docs.symbiont.dev/dsl-guide)
- [API reference](https://docs.symbiont.dev/api-reference)

The Symbiont runtime itself lives at [thirdkeyai/symbiont](https://github.com/thirdkeyai/symbiont).

---

## What's new

### v1.10.0 — HTTP Input LLM invocation
- `WebhookInvocationResponse` union covering both `WebhookExecutionStartedResponse` (runtime communication-bus dispatch) and `WebhookCompletedResponse` (on-demand LLM ORGA loop) shapes from the Symbiont v1.10.0 HTTP Input handler
- `WebhookToolRun`, `WebhookInvocationRequest`, `WebhookInvocationStatus` Pydantic models
- ToolClad v0.4.0 backend strings (`http`, `mcp`, `session`, `browser`) accepted on `ToolManifestInfo.backend`
- All packages aligned to Symbiont runtime v1.10.0

See [`CHANGELOG.md`](./CHANGELOG.md) for the full history.

---

## License

Apache 2.0. See [`LICENSE`](./LICENSE).

The SDK is part of the Symbiont project's Community Edition. For Enterprise licensing of the Symbiont runtime (advanced sandbox backends, compliance audit exports, AI-powered tool review, encrypted multi-agent collaboration, monitoring dashboards, dedicated support), contact [ThirdKey](https://thirdkey.ai).

---

<div align="right">
  <img src="https://raw.githubusercontent.com/ThirdKeyAI/Symbiont/main/symbi-trans.png" alt="Symbi" width="120">
</div>
