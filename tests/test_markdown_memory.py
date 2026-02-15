"""Tests for the MarkdownMemoryStore module."""

import os
import time

import pytest

from symbiont.markdown_memory import (
    AgentMemoryContext,
    MarkdownMemoryStore,
    StorageStats,
)


@pytest.fixture
def store(tmp_path):
    """Create a MarkdownMemoryStore rooted in a temp directory."""
    return MarkdownMemoryStore(str(tmp_path), retention_days=30)


@pytest.fixture
def sample_context():
    """Return a sample AgentMemoryContext."""
    return AgentMemoryContext(
        agent_id="agent-1",
        facts=["The sky is blue", "Water is wet"],
        procedures=["Greet the user first", "Check permissions before acting"],
        learned_patterns=["Users prefer short answers"],
    )


class TestMarkdownMemoryStore:
    """Tests for MarkdownMemoryStore."""

    def test_roundtrip_save_load(self, store, sample_context):
        """Save and reload a context; all fields must match."""
        store.save_context("agent-1", sample_context)
        loaded = store.load_context("agent-1")

        assert loaded is not None
        assert loaded.agent_id == "agent-1"
        assert loaded.facts == sample_context.facts
        assert loaded.procedures == sample_context.procedures
        assert loaded.learned_patterns == sample_context.learned_patterns

    def test_load_missing_returns_none(self, store):
        """Loading a nonexistent agent returns None."""
        assert store.load_context("no-such-agent") is None

    def test_delete_context(self, store, sample_context):
        """Deleting removes the agent directory entirely."""
        store.save_context("agent-1", sample_context)
        store.delete_context("agent-1")
        assert store.load_context("agent-1") is None

    def test_list_agent_contexts(self, store, sample_context):
        """list_agent_contexts returns saved agent IDs sorted."""
        store.save_context("beta", sample_context)
        store.save_context("alpha", sample_context)
        assert store.list_agent_contexts() == ["alpha", "beta"]

    def test_daily_log_creation(self, store, sample_context):
        """Saving context creates a daily log file."""
        store.save_context("agent-1", sample_context)
        logs_dir = os.path.join(store._root_dir, "agent-1", "logs")
        log_files = os.listdir(logs_dir)
        assert len(log_files) == 1
        assert log_files[0].endswith(".md")

    def test_storage_stats(self, store, sample_context):
        """get_storage_stats returns correct context count and nonzero size."""
        store.save_context("a1", sample_context)
        store.save_context("a2", sample_context)
        stats = store.get_storage_stats()

        assert isinstance(stats, StorageStats)
        assert stats.total_contexts == 2
        assert stats.total_size_bytes > 0
        assert stats.storage_path == store._root_dir

    def test_markdown_format(self, store, sample_context):
        """The written file contains the expected markdown sections."""
        store.save_context("agent-1", sample_context)
        mem_path = os.path.join(store._root_dir, "agent-1", "memory.md")
        with open(mem_path) as f:
            text = f.read()

        assert "## Facts" in text
        assert "## Procedures" in text
        assert "## Learned Patterns" in text
        assert "- The sky is blue" in text

    def test_compact_removes_old_logs(self, store, sample_context, tmp_path):
        """compact() removes log files older than retention period."""
        store.save_context("agent-1", sample_context)
        logs_dir = os.path.join(store._root_dir, "agent-1", "logs")

        # Create an artificially old log
        old_log = os.path.join(logs_dir, "2020-01-01.md")
        with open(old_log, "w") as f:
            f.write("old log")
        # Set mtime far in the past
        old_time = time.time() - (365 * 86400)
        os.utime(old_log, (old_time, old_time))

        store.compact("agent-1")

        # The old log should be removed, the current day's log should remain
        remaining = os.listdir(logs_dir)
        assert "2020-01-01.md" not in remaining
        assert len(remaining) == 1  # today's log
