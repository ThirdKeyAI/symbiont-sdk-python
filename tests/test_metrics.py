"""Tests for the metrics collection and export module."""

import json
import os
import time

import pytest

from symbiont.exceptions import MetricsExportError
from symbiont.metrics import (
    CompositeExporter,
    FileExporterConfig,
    FileMetricsExporter,
    MetricsCollector,
    MetricsExporter,
    MetricsExporterConfig,
    MetricsSnapshot,
    SchedulerMetrics,
    SystemResourceMetrics,
)


def _make_snapshot(**kwargs) -> MetricsSnapshot:
    """Create a simple snapshot for testing."""
    return MetricsSnapshot(
        timestamp="2026-02-15T12:00:00Z",
        scheduler=SchedulerMetrics(jobs_total=5, jobs_active=2),
        system=SystemResourceMetrics(cpu_usage_percent=42.5, memory_usage_bytes=1024),
        **kwargs,
    )


class TestMetricsExporterConfig:
    """Tests for config defaults."""

    def test_defaults(self):
        cfg = MetricsExporterConfig()
        assert cfg.enabled is True
        assert cfg.export_interval_seconds == 60
        assert cfg.otlp is None
        assert cfg.file is None


class TestMetricsSnapshot:
    """Tests for MetricsSnapshot serialization."""

    def test_roundtrip(self):
        """to_dict -> from_dict preserves all fields."""
        snapshot = _make_snapshot()
        data = snapshot.to_dict()
        restored = MetricsSnapshot.from_dict(data)

        assert restored.timestamp == snapshot.timestamp
        assert restored.scheduler.jobs_total == 5
        assert restored.scheduler.jobs_active == 2
        assert restored.system.cpu_usage_percent == 42.5
        assert restored.system.memory_usage_bytes == 1024


class TestFileMetricsExporter:
    """Tests for FileMetricsExporter."""

    def test_write_and_read(self, tmp_path):
        """Exporter writes valid JSON that can be read back."""
        out_path = str(tmp_path / "metrics.json")
        exporter = FileMetricsExporter(FileExporterConfig(path=out_path))
        snapshot = _make_snapshot()
        exporter.export(snapshot)

        with open(out_path) as f:
            data = json.load(f)
        assert data["timestamp"] == "2026-02-15T12:00:00Z"
        assert data["scheduler"]["jobs_total"] == 5

    def test_parent_dir_creation(self, tmp_path):
        """Exporter creates parent directories if they don't exist."""
        out_path = str(tmp_path / "sub" / "dir" / "metrics.json")
        exporter = FileMetricsExporter(FileExporterConfig(path=out_path))
        exporter.export(_make_snapshot())
        assert os.path.isfile(out_path)

    def test_compact_json(self, tmp_path):
        """Compact mode produces JSON without extra whitespace."""
        out_path = str(tmp_path / "compact.json")
        exporter = FileMetricsExporter(FileExporterConfig(path=out_path, compact=True))
        exporter.export(_make_snapshot())

        with open(out_path) as f:
            text = f.read()
        assert "  " not in text  # no indentation

    def test_shutdown(self, tmp_path):
        """shutdown() is a no-op but doesn't raise."""
        exporter = FileMetricsExporter(FileExporterConfig(path=str(tmp_path / "x.json")))
        exporter.shutdown()

    def test_overwrite(self, tmp_path):
        """Exporting twice overwrites the previous file."""
        out_path = str(tmp_path / "metrics.json")
        exporter = FileMetricsExporter(FileExporterConfig(path=out_path))

        snap1 = MetricsSnapshot(
            timestamp="2026-01-01T00:00:00Z",
            scheduler=SchedulerMetrics(jobs_total=1),
        )
        snap2 = MetricsSnapshot(
            timestamp="2026-02-01T00:00:00Z",
            scheduler=SchedulerMetrics(jobs_total=99),
        )

        exporter.export(snap1)
        exporter.export(snap2)

        with open(out_path) as f:
            data = json.load(f)
        assert data["scheduler"]["jobs_total"] == 99


class TestCompositeExporter:
    """Tests for CompositeExporter."""

    def test_lifecycle(self, tmp_path):
        """Composite delegates to multiple exporters."""
        p1 = str(tmp_path / "a.json")
        p2 = str(tmp_path / "b.json")
        exp1 = FileMetricsExporter(FileExporterConfig(path=p1))
        exp2 = FileMetricsExporter(FileExporterConfig(path=p2))

        composite = CompositeExporter([exp1, exp2])
        composite.export(_make_snapshot())
        composite.shutdown()

        assert os.path.isfile(p1)
        assert os.path.isfile(p2)

    def test_error_propagation(self):
        """If all exporters fail, CompositeExporter raises."""

        class FailExporter(MetricsExporter):
            def export(self, snapshot):
                raise MetricsExportError("boom", backend="fail")

            def shutdown(self):
                pass

        composite = CompositeExporter([FailExporter(), FailExporter()])
        with pytest.raises(MetricsExportError, match="All exporters failed"):
            composite.export(_make_snapshot())


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_start_stop(self, tmp_path):
        """Collector starts a background thread, exports, then stops cleanly."""
        out_path = str(tmp_path / "collector.json")
        exporter = FileMetricsExporter(FileExporterConfig(path=out_path))
        collector = MetricsCollector(exporter, interval_seconds=1)

        collector.start()
        time.sleep(2)  # Let at least one export cycle run
        collector.stop()

        assert os.path.isfile(out_path)


class TestMetricsClient:
    """Tests for MetricsClient mock."""

    def test_client_mock(self):
        """MetricsClient can be constructed with a mock parent."""
        from unittest.mock import MagicMock

        from symbiont.metrics import MetricsClient

        mock_response = MagicMock()
        mock_response.json.return_value = {"timestamp": "2026-02-15T12:00:00Z"}

        mock_parent = MagicMock()
        mock_parent._request.return_value = mock_response

        client = MetricsClient(mock_parent)
        result = client.get_metrics_snapshot()
        assert result["timestamp"] == "2026-02-15T12:00:00Z"
        mock_parent._request.assert_called_once_with(
            "GET", "/metrics/snapshot", json=None, params=None
        )
