# Symbiont SDK for Python — Skills Guide

**Purpose**: This guide helps AI assistants quickly build applications using the Symbiont Python SDK.

**For Full Documentation**: See the [README](README.md).

## What This SDK Does

The Symbiont Python SDK (`symbiont-sdk`) provides a client for interacting with the Symbiont agent runtime. It covers agent lifecycle management, workflow execution, memory systems, vector search, scheduling, channel adapters, AgentPin credential verification, and more.

**Part of the ThirdKey trust stack**: SchemaPin (tool integrity) → AgentPin (agent identity) → Symbiont (runtime)

---

## Quick Start

```bash
pip install symbiont-sdk
```

```python
from symbiont_sdk import Client

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
from symbiont_sdk.types import WorkflowExecutionRequest

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

### Memory System

Hierarchical memory with short-term, long-term, episodic, and semantic levels:

```python
from symbiont_sdk.types import MemoryStoreRequest, MemorySearchRequest

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
from symbiont_sdk.types import (
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
```

### Channel Adapters (`client.channels`)

Manage Slack, Teams, and Mattermost integrations:

```python
channels = client.channels.list()
```

---

## Configuration

```python
# Direct configuration
client = Client(api_key="key", base_url="http://localhost:8080/api/v1")

# From config file (YAML or JSON)
from symbiont_sdk.config import ConfigManager

config = ConfigManager.load("config.yaml")
client = Client(config=config)

# From environment variables
# SYMBIONT_API_KEY, SYMBIONT_BASE_URL
client = Client()
```

---

## Authentication

```python
from symbiont_sdk.auth import AuthManager

auth = AuthManager(client)
# JWT/RBAC authentication built in
```

---

## Sub-Clients

| Client | Access | Purpose |
|--------|--------|---------|
| `client.agentpin` | Lazy-loaded | AgentPin credential management |
| `client.schedules` | Lazy-loaded | Cron scheduling |
| `client.channels` | Lazy-loaded | Chat channel adapters |

---

## Pro Tips for AI Assistants

1. **Lazy-loaded sub-clients** — `client.agentpin`, `client.schedules`, `client.channels` are initialized on first access
2. **AgentPin is ES256 only** — credentials use ECDSA P-256, no other algorithms accepted
3. **Short-lived credentials** — prefer TTLs of hours, not days
4. **Trust bundles** for offline/air-gapped environments — bundle discovery + revocation docs
5. **Memory hierarchy** — use `fact` for persistent knowledge, `conversation` for chat context, `experience` for episodic
6. **Vector search** with Qdrant — use for semantic similarity over agent knowledge bases
7. **Config from files** — `ConfigManager.load()` supports YAML and JSON for deployment flexibility
8. **Secrets via backends** — Vault, Redis, or PostgreSQL backends available; never hardcode secrets
