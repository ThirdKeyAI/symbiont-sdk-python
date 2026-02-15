"""Markdown-based memory persistence for the Symbiont SDK.

Provides file-based context persistence using markdown files, ported from
the Rust runtime's ContextPersistence trait (markdown_memory.rs).
"""

import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from .exceptions import MemoryStorageError


@dataclass
class StorageStats:
    """Statistics about the markdown memory store."""

    total_contexts: int
    total_size_bytes: int
    last_cleanup: Optional[str]
    storage_path: str


@dataclass
class AgentMemoryContext:
    """Memory context for a single agent."""

    agent_id: str
    facts: List[str] = field(default_factory=list)
    procedures: List[str] = field(default_factory=list)
    learned_patterns: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)


class MarkdownMemoryStore:
    """File-based memory store using markdown format.

    Layout::

        {root_dir}/{agent_id}/memory.md       — current context
        {root_dir}/{agent_id}/logs/YYYY-MM-DD.md — daily interaction logs

    The markdown format uses ``## Section`` headers with ``- item`` lists.
    """

    def __init__(self, root_dir: str, retention_days: int = 30) -> None:
        self._root_dir = root_dir
        self._retention_days = retention_days
        os.makedirs(root_dir, exist_ok=True)

    def _agent_dir(self, agent_id: str) -> str:
        return os.path.join(self._root_dir, agent_id)

    def _memory_path(self, agent_id: str) -> str:
        return os.path.join(self._agent_dir(agent_id), "memory.md")

    def _logs_dir(self, agent_id: str) -> str:
        return os.path.join(self._agent_dir(agent_id), "logs")

    @staticmethod
    def _render_markdown(context: AgentMemoryContext) -> str:
        lines: List[str] = [f"# Agent Memory: {context.agent_id}", ""]

        lines.append("## Facts")
        for item in context.facts:
            lines.append(f"- {item}")
        lines.append("")

        lines.append("## Procedures")
        for item in context.procedures:
            lines.append(f"- {item}")
        lines.append("")

        lines.append("## Learned Patterns")
        for item in context.learned_patterns:
            lines.append(f"- {item}")
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _parse_markdown(text: str, agent_id: str) -> AgentMemoryContext:
        ctx = AgentMemoryContext(agent_id=agent_id)
        current_section: Optional[str] = None

        section_map = {
            "facts": "facts",
            "procedures": "procedures",
            "learned patterns": "learned_patterns",
        }

        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("## "):
                header = stripped[3:].strip().lower()
                current_section = section_map.get(header)
            elif stripped.startswith("- ") and current_section:
                getattr(ctx, current_section).append(stripped[2:])

        return ctx

    def save_context(self, agent_id: str, context: AgentMemoryContext) -> None:
        """Save agent context atomically and append a daily log entry."""
        agent_dir = self._agent_dir(agent_id)
        os.makedirs(agent_dir, exist_ok=True)

        md_content = self._render_markdown(context)

        # Atomic write via tempfile + os.replace
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=agent_dir, prefix=".memory_", suffix=".md"
            )
            try:
                os.write(fd, md_content.encode("utf-8"))
            finally:
                os.close(fd)
            os.replace(tmp_path, self._memory_path(agent_id))
        except OSError as exc:
            raise MemoryStorageError(
                f"Failed to save context for agent {agent_id}: {exc}",
                storage_type="markdown",
            ) from exc

        # Append daily log
        self._append_daily_log(agent_id, context)

    def _append_daily_log(self, agent_id: str, context: AgentMemoryContext) -> None:
        logs_dir = self._logs_dir(agent_id)
        os.makedirs(logs_dir, exist_ok=True)

        today = datetime.now().strftime("%Y-%m-%d")
        log_path = os.path.join(logs_dir, f"{today}.md")

        timestamp = datetime.now().strftime("%H:%M:%S")
        entry_lines = [
            f"### Update at {timestamp}",
            f"- Facts: {len(context.facts)}",
            f"- Procedures: {len(context.procedures)}",
            f"- Learned Patterns: {len(context.learned_patterns)}",
            "",
        ]

        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(entry_lines))

    def load_context(self, agent_id: str) -> Optional[AgentMemoryContext]:
        """Load agent context from markdown file. Returns None if not found."""
        mem_path = self._memory_path(agent_id)
        if not os.path.isfile(mem_path):
            return None

        try:
            with open(mem_path, encoding="utf-8") as fh:
                text = fh.read()
            return self._parse_markdown(text, agent_id)
        except OSError as exc:
            raise MemoryStorageError(
                f"Failed to load context for agent {agent_id}: {exc}",
                storage_type="markdown",
            ) from exc

    def delete_context(self, agent_id: str) -> None:
        """Delete all stored data for an agent."""
        agent_dir = self._agent_dir(agent_id)
        if os.path.isdir(agent_dir):
            shutil.rmtree(agent_dir)

    def list_agent_contexts(self) -> List[str]:
        """List agent IDs that have stored contexts."""
        if not os.path.isdir(self._root_dir):
            return []

        return sorted(
            entry
            for entry in os.listdir(self._root_dir)
            if os.path.isdir(os.path.join(self._root_dir, entry))
        )

    def compact(self, agent_id: str) -> None:
        """Remove log files older than the retention period."""
        logs_dir = self._logs_dir(agent_id)
        if not os.path.isdir(logs_dir):
            return

        cutoff = time.time() - (self._retention_days * 86400)
        for filename in os.listdir(logs_dir):
            filepath = os.path.join(logs_dir, filename)
            if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff:
                os.remove(filepath)

    def get_storage_stats(self) -> StorageStats:
        """Get storage statistics across all agents."""
        total_size = 0
        contexts = self.list_agent_contexts()

        for root, _dirs, files in os.walk(self._root_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    total_size += os.path.getsize(fpath)
                except OSError:
                    pass

        return StorageStats(
            total_contexts=len(contexts),
            total_size_bytes=total_size,
            last_cleanup=None,
            storage_path=self._root_dir,
        )
