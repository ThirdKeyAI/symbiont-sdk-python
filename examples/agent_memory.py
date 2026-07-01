"""Persistent agent memory — a self-contained example (no runtime required).

MarkdownMemoryStore gives an agent file-based context that survives restarts,
stored as human-readable markdown. This example writes a context, reads it
back, and prints storage stats — it talks to the local filesystem only, so it
runs without a Symbiont runtime.

Run:
  pip install symbiont-sdk
  python examples/agent_memory.py
"""

import tempfile

from symbiont import AgentMemoryContext, MarkdownMemoryStore


def main() -> None:
    root = tempfile.mkdtemp(prefix="symbi-memory-")
    store = MarkdownMemoryStore(root_dir=root)

    store.save_context(
        "agent-1",
        AgentMemoryContext(
            agent_id="agent-1",
            facts=["The user prefers concise answers."],
            procedures=["Validate input before acting."],
            learned_patterns=["Batch related tool calls."],
            metadata={"team": "research"},
        ),
    )

    context = store.load_context("agent-1")
    print("loaded facts:", context.facts)
    print("known agents:", store.list_agent_contexts())

    stats = store.get_storage_stats()
    print("contexts:", stats.total_contexts, "bytes:", stats.total_size_bytes)
    print("stored under:", root)


if __name__ == "__main__":
    main()
