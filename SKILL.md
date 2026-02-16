---
name: symbiont-sdk-python
title: Symbiont SDK for Python
description: Python SDK for the Symbiont agent runtime — agent lifecycle, webhook verification, AgentPin identity, memory systems, skill scanning, metrics, scheduling, and vector search
version: 0.6.0
---

# Symbiont SDK for Python — Skills Guide

**Purpose**: This guide helps AI assistants quickly build applications using the Symbiont Python SDK.

**For Full Documentation**: See the [README](https://github.com/ThirdKeyAI/symbiont-sdk-python/blob/main/README.md).

## What This SDK Does

The Symbiont Python SDK (`symbiont-sdk`) provides a client for interacting with the Symbiont agent runtime. It covers agent lifecycle management, workflow execution, memory systems, vector search, scheduling, channel adapters, AgentPin credential verification, webhook signature verification, agent skill scanning, and metrics collection/export.

**Part of the ThirdKey trust stack**: SchemaPin (tool integrity) → AgentPin (agent identity) → Symbiont (runtime)

---

## Quick Start

```bash
pip install symbiont-sdk
```

```python
from symbiont import Client

client = Client(
    api_key="your-api-key",
    base_url="http://localhost:8080/api/v1",
)
```

---

## Core APIs

### Agent Management

```python
# List agents
agents = client.list_agents()

# Create an agent
agent = client.create_agent({
    "id": "my-agent",
    "name": "My Agent",
    "tools": ["search", "summarize"],
})

# Check status
status = client.get_agent_status("my-agent")

# Get metrics
metrics = client.get_agent_metrics("my-agent")

# Execute a workflow
from symbiont.models import WorkflowExecutionRequest

result = client.execute_workflow(WorkflowExecutionRequest(
    workflow_id="wf-id",
    parameters={"input": "process this"},
))
```

### AgentPin Integration (`client.agentpin`)

Cryptographic agent identity verification:

```python
# Generate P-256 keypair
keys = client.agentpin.generate_key_pair()

# Issue a JWT credential
jwt = client.agentpin.issue_credential(
    private_key_pem=keys.private_key_pem,
    kid="key-1",
    issuer="https://example.com",
    agent_id="my-agent",
    capabilities=["read", "write"],
    ttl_secs=3600,
)

# Verify credential (online)
result = client.agentpin.verify_credential(jwt)

# Verify credential (offline with local discovery)
result = client.agentpin.verify_credential_offline(jwt, discovery_doc)

# Verify with trust bundle
result = client.agentpin.verify_credential_with_bundle(jwt, bundle)

# Fetch discovery document
doc = client.agentpin.fetch_discovery_document("example.com")

# Trust management
bundle = client.agentpin.create_trust_bundle()
client.agentpin.save_trust_bundle(bundle, "bundle.json")
bundle = client.agentpin.load_trust_bundle("bundle.json")
```

### Webhook Verification

Verify inbound webhook signatures from GitHub, Stripe, Slack, or custom providers:

```python
from symbiont import WebhookProvider, HmacVerifier, JwtVerifier

# Use a provider preset (GitHub, Stripe, Slack, Custom)
verifier = WebhookProvider.GITHUB.verifier(secret=b"your-secret")
verifier.verify(request.headers, request.body)

# Manual HMAC verifier with prefix stripping
hmac = HmacVerifier(
    secret=b"your-secret",
    header_name="X-Hub-Signature-256",
    prefix="sha256=",
)
hmac.verify(headers, body)

# JWT-based webhook verification
jwt_v = JwtVerifier(
    secret=b"your-secret",
    header_name="Authorization",
    required_issuer="expected-issuer",
)
jwt_v.verify(headers, body)
```

### Markdown Memory Persistence

File-based agent context persistence using markdown format:

```python
from symbiont import MarkdownMemoryStore, AgentMemoryContext

store = MarkdownMemoryStore("/data/memory", retention_days=30)

# Save agent context
store.save_context("agent-1", AgentMemoryContext(
    agent_id="agent-1",
    facts=["User prefers dark mode", "Timezone is UTC-5"],
    procedures=["Always greet by name"],
    learned_patterns=["Responds better to bullet points"],
    metadata={"last_session": "2026-02-15"},
))

# Load context
context = store.load_context("agent-1")

# List all agents with stored contexts
agents = store.list_agent_contexts()

# Compact old daily logs
store.compact("agent-1")

# Storage statistics
stats = store.get_storage_stats()
```

### Agent Skills (ClawHavoc Scanning + Loading)

Scan and load agent skill definitions with security scanning:

```python
from symbiont import SkillScanner, SkillLoader, SkillLoaderConfig

# Scan content for security issues (10 built-in ClawHavoc rules)
scanner = SkillScanner()
findings = scanner.scan_content(skill_content, "SKILL.md")
# Detects: pipe-to-shell, wget-pipe-to-shell, env file references,
#   SOUL.md/memory.md tampering, eval+fetch, base64-decode-exec, rm-rf, chmod-777

# Scan an entire skill directory
result = scanner.scan_skill("/path/to/skill")

# Load skills from configured paths
loader = SkillLoader(SkillLoaderConfig(
    load_paths=["/skills/verified", "/skills/community"],
    require_signed=False,
    scan_enabled=True,
))
skills = loader.load_all()

# Load a single skill (reads SKILL.md, parses frontmatter, scans)
skill = loader.load_skill("/path/to/skill")
print(skill.name, skill.signature_status, skill.scan_result)
```

### Metrics Collection & Export (`client.metrics_client`)

Runtime metrics retrieval and local export:

```python
from symbiont import (
    MetricsClient, FileMetricsExporter, CompositeExporter, MetricsCollector,
)

# Fetch metrics from runtime API (via client)
snapshot = client.metrics_client.get_metrics_snapshot()
scheduler = client.metrics_client.get_scheduler_metrics()
system = client.metrics_client.get_system_metrics()
client.metrics_client.export_metrics({"format": "json"})

# Export metrics to file (atomic JSON write)
file_exporter = FileMetricsExporter(file_path="/tmp/metrics.json")
file_exporter.export(snapshot)

# Fan-out to multiple backends
composite = CompositeExporter([file_exporter, other_exporter])
composite.export(snapshot)

# Periodic background collection
collector = MetricsCollector(composite, interval_seconds=60)
collector.start(fetch_snapshot_fn)
collector.stop()
```

### Memory System

Hierarchical memory with short-term, long-term, episodic, and semantic levels:

```python
from symbiont.models import MemoryStoreRequest, MemorySearchRequest

# Store a memory
client.add_memory(MemoryStoreRequest(
    agent_id="my-agent",
    content="Important fact",
    memory_type="fact",
    level="long-term",
))

# Search memories
results = client.search_memory(MemorySearchRequest(
    agent_id="my-agent",
    query="important",
    limit=10,
))

# Get conversation context
context = client.get_conversation_context("conv-123", "my-agent")

# Consolidate memory
client.consolidate_memory("my-agent")
```

### Vector Database (Qdrant)

```python
from symbiont.models import (
    CollectionCreateRequest, VectorUpsertRequest, VectorSearchRequest,
)

# Create a collection
client.create_vector_collection(CollectionCreateRequest(
    name="knowledge",
    dimension=384,
))

# Add vectors
client.add_vectors(VectorUpsertRequest(
    collection="knowledge",
    vectors=[{"id": "1", "values": [...], "metadata": {"text": "content"}}],
))

# Semantic search
results = client.search_vectors(VectorSearchRequest(
    collection="knowledge",
    query_vector=[...],
    top_k=5,
))
```

### Scheduling (`client.schedules`)

```python
# Create a scheduled task
schedule = client.schedules.create({
    "agent_id": "my-agent",
    "cron": "0 */6 * * *",  # Every 6 hours
    "parameters": {"task": "cleanup"},
})

# List schedules
schedules = client.schedules.list()

# Scheduler health
health = client.schedules.get_scheduler_health()
```

### Channel Adapters (`client.channels`)

Manage Slack, Teams, and Mattermost integrations:

```python
channels = client.channels.list()
```

---

## Sub-Clients

| Client | Access | Purpose |
|--------|--------|---------|
| `client.agentpin` | Lazy-loaded | AgentPin credential management |
| `client.schedules` | Lazy-loaded | Cron scheduling |
| `client.channels` | Lazy-loaded | Chat channel adapters |
| `client.metrics_client` | Lazy-loaded | Runtime metrics API |

**Standalone modules** (not sub-clients — import directly):
- `MarkdownMemoryStore` — file-based context persistence
- `HmacVerifier` / `JwtVerifier` / `WebhookProvider` — webhook verification
- `SkillScanner` / `SkillLoader` — skill scanning and loading
- `FileMetricsExporter` / `CompositeExporter` / `MetricsCollector` — local metrics export

---

## Configuration

```python
# Direct configuration
client = Client(api_key="key", base_url="http://localhost:8080/api/v1")

# From config file (YAML or JSON)
from symbiont.config import ConfigManager

config = ConfigManager.load("config.yaml")
client = Client(config=config)

# From environment variables
# SYMBIONT_API_KEY, SYMBIONT_BASE_URL
client = Client()
```

---

## Authentication

```python
from symbiont.auth import AuthManager

auth = AuthManager(client)
# JWT/RBAC authentication built in
```

---

## Optional Dependencies

```bash
# For SchemaPin skill signature verification
pip install symbiont-sdk[skills]

# For OpenTelemetry metrics export
pip install symbiont-sdk[metrics]
```

---

## Pro Tips for AI Assistants

1. **Lazy-loaded sub-clients** — `client.agentpin`, `client.schedules`, `client.channels`, `client.metrics_client` are initialized on first access
2. **AgentPin is ES256 only** — credentials use ECDSA P-256, no other algorithms accepted
3. **Short-lived credentials** — prefer TTLs of hours, not days
4. **Trust bundles** for offline/air-gapped environments — bundle discovery + revocation docs
5. **Memory hierarchy** — use `fact` for persistent knowledge, `conversation` for chat context, `experience` for episodic
6. **Markdown memory** — use `MarkdownMemoryStore` for file-based agent context that survives restarts
7. **Webhook verification** — use `WebhookProvider.GITHUB.verifier()` for known providers; HMAC uses `hmac.compare_digest()` for constant-time comparison
8. **Skill scanning** — always scan untrusted skills before loading; 10 built-in ClawHavoc rules catch common attacks
9. **Metrics export** — `FileMetricsExporter` uses atomic writes; `CompositeExporter` tolerates partial backend failures
10. **Vector search** with Qdrant — use for semantic similarity over agent knowledge bases
11. **Config from files** — `ConfigManager.load()` supports YAML and JSON for deployment flexibility
12. **Secrets via backends** — Vault, Redis, or PostgreSQL backends available; never hardcode secrets
