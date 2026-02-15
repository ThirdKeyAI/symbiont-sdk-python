"""Metrics collection and export for the Symbiont SDK.

Provides local file-based and OTLP metrics export, ported from
the Rust runtime's metrics module.
"""

import json
import logging
import os
import tempfile
import threading
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .exceptions import MetricsConfigError, MetricsExportError

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class SchedulerMetrics:
    """Scheduler metrics snapshot."""

    jobs_total: int = 0
    jobs_active: int = 0
    jobs_paused: int = 0
    runs_total: int = 0
    runs_succeeded: int = 0
    runs_failed: int = 0


@dataclass
class TaskManagerMetrics:
    """Task manager metrics snapshot."""

    tasks_active: int = 0
    tasks_queued: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0


@dataclass
class LoadBalancerMetrics:
    """Load balancer metrics snapshot."""

    total_requests: int = 0
    active_connections: int = 0
    backends_healthy: int = 0
    backends_total: int = 0


@dataclass
class SystemResourceMetrics:
    """System resource metrics snapshot."""

    cpu_usage_percent: float = 0.0
    memory_usage_bytes: int = 0
    memory_usage_percent: float = 0.0
    disk_usage_bytes: int = 0
    disk_usage_percent: float = 0.0


@dataclass
class MetricsSnapshot:
    """Complete metrics snapshot at a point in time."""

    timestamp: str
    scheduler: Optional[SchedulerMetrics] = None
    task_manager: Optional[TaskManagerMetrics] = None
    load_balancer: Optional[LoadBalancerMetrics] = None
    system: Optional[SystemResourceMetrics] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dictionary."""
        result: Dict[str, Any] = {"timestamp": self.timestamp}
        if self.scheduler is not None:
            result["scheduler"] = asdict(self.scheduler)
        if self.task_manager is not None:
            result["task_manager"] = asdict(self.task_manager)
        if self.load_balancer is not None:
            result["load_balancer"] = asdict(self.load_balancer)
        if self.system is not None:
            result["system"] = asdict(self.system)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MetricsSnapshot":
        """Deserialize from a plain dictionary."""
        snapshot = cls(timestamp=data["timestamp"])
        if "scheduler" in data:
            snapshot.scheduler = SchedulerMetrics(**data["scheduler"])
        if "task_manager" in data:
            snapshot.task_manager = TaskManagerMetrics(**data["task_manager"])
        if "load_balancer" in data:
            snapshot.load_balancer = LoadBalancerMetrics(**data["load_balancer"])
        if "system" in data:
            snapshot.system = SystemResourceMetrics(**data["system"])
        return snapshot


# =============================================================================
# Config Data Classes
# =============================================================================


class OtlpProtocol(Enum):
    """OTLP transport protocol."""

    GRPC = "grpc"
    HTTP = "http"


@dataclass
class OtlpExporterConfig:
    """OTLP exporter configuration."""

    endpoint: str = "http://localhost:4317"
    protocol: OtlpProtocol = OtlpProtocol.GRPC
    headers: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 10


@dataclass
class FileExporterConfig:
    """File-based metrics exporter configuration."""

    path: str = "metrics.json"
    compact: bool = True


@dataclass
class MetricsExporterConfig:
    """Top-level metrics exporter configuration."""

    enabled: bool = True
    export_interval_seconds: int = 60
    otlp: Optional[OtlpExporterConfig] = None
    file: Optional[FileExporterConfig] = None


# =============================================================================
# Exporters
# =============================================================================


class MetricsExporter(ABC):
    """Abstract base class for metrics exporters."""

    @abstractmethod
    def export(self, snapshot: MetricsSnapshot) -> None:
        """Export a metrics snapshot."""

    @abstractmethod
    def shutdown(self) -> None:
        """Shut down the exporter and release resources."""


class FileMetricsExporter(MetricsExporter):
    """Writes metrics snapshots to a JSON file atomically."""

    def __init__(self, config: FileExporterConfig) -> None:
        self._path = config.path
        self._compact = config.compact

    def export(self, snapshot: MetricsSnapshot) -> None:
        parent_dir = os.path.dirname(self._path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        try:
            data = snapshot.to_dict()
            if self._compact:
                json_str = json.dumps(data, separators=(",", ":"))
            else:
                json_str = json.dumps(data, indent=2)

            fd, tmp_path = tempfile.mkstemp(
                dir=parent_dir or ".",
                prefix=".metrics_",
                suffix=".json",
            )
            try:
                os.write(fd, json_str.encode("utf-8"))
            finally:
                os.close(fd)
            os.replace(tmp_path, self._path)
        except OSError as exc:
            raise MetricsExportError(
                f"Failed to write metrics file: {exc}",
                backend="file",
            ) from exc

    def shutdown(self) -> None:
        pass


class OtlpExporter(MetricsExporter):
    """OTLP metrics exporter (requires opentelemetry-api)."""

    def __init__(self, config: OtlpExporterConfig) -> None:
        try:
            import opentelemetry  # noqa: F401
        except ImportError as exc:
            raise MetricsConfigError(
                "opentelemetry-api is required for OTLP export. "
                "Install with: pip install 'symbiont-sdk[metrics]'",
                config_field="otlp",
            ) from exc
        self._config = config

    def export(self, snapshot: MetricsSnapshot) -> None:
        raise MetricsConfigError(
            "OTLP export is a stub — full implementation requires opentelemetry SDK",
            config_field="otlp",
        )

    def shutdown(self) -> None:
        pass


class CompositeExporter(MetricsExporter):
    """Fan-out exporter that delegates to multiple backends."""

    def __init__(self, exporters: List[MetricsExporter]) -> None:
        self._exporters = list(exporters)

    def export(self, snapshot: MetricsSnapshot) -> None:
        errors: List[str] = []
        for exporter in self._exporters:
            try:
                exporter.export(snapshot)
            except Exception as exc:
                logger.warning("Exporter %s failed: %s", type(exporter).__name__, exc)
                errors.append(str(exc))
        if errors and len(errors) == len(self._exporters):
            raise MetricsExportError(
                f"All exporters failed: {'; '.join(errors)}",
                backend="composite",
            )

    def shutdown(self) -> None:
        for exporter in self._exporters:
            try:
                exporter.shutdown()
            except Exception as exc:
                logger.warning("Exporter shutdown failed: %s", exc)


# =============================================================================
# Metrics Collector
# =============================================================================


class MetricsCollector:
    """Background thread that periodically exports metrics snapshots."""

    def __init__(
        self,
        exporter: MetricsExporter,
        interval_seconds: int = 60,
    ) -> None:
        self._exporter = exporter
        self._interval = interval_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            snapshot = MetricsSnapshot(
                timestamp=datetime.now(timezone.utc).isoformat(),
                system=SystemResourceMetrics(),
            )
            try:
                self._exporter.export(snapshot)
            except Exception as exc:
                logger.warning("Metrics export failed: %s", exc)
            self._stop_event.wait(self._interval)

    def start(self) -> None:
        """Start the background collection thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the background collection thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        self._exporter.shutdown()


# =============================================================================
# Metrics Client (sub-client for runtime API)
# =============================================================================


class MetricsClient:
    """Client for querying runtime metrics via the Symbiont Runtime API.

    Accessed through the main ``Client`` instance::

        from symbiont import Client
        client = Client()
        snapshot = client.metrics.get_metrics_snapshot()
    """

    def __init__(self, parent_client: Any) -> None:
        self._client = parent_client

    def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        response = self._client._request(method, path, json=json, params=params)
        return response.json()

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """Get the current metrics snapshot. ``GET /metrics/snapshot``"""
        return self._request("GET", "/metrics/snapshot")

    def get_scheduler_metrics(self) -> Dict[str, Any]:
        """Get scheduler-specific metrics. ``GET /metrics/scheduler``"""
        return self._request("GET", "/metrics/scheduler")

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system resource metrics. ``GET /metrics/system``"""
        return self._request("GET", "/metrics/system")

    def export_metrics(self) -> Dict[str, Any]:
        """Trigger a metrics export. ``POST /metrics/export``"""
        return self._request("POST", "/metrics/export")
