"""Unit tests for the Symbiont SDK ScheduleClient."""

from unittest.mock import Mock, patch

from symbiont import Client
from symbiont.config import ClientConfig
from symbiont.schedules import (
    CreateScheduleRequest,
    CreateScheduleResponse,
    DeleteScheduleResponse,
    NextRunsResponse,
    ScheduleActionResponse,
    ScheduleDetail,
    ScheduleHistoryResponse,
    SchedulerHealthResponse,
    ScheduleRunEntry,
    ScheduleSummary,
    UpdateScheduleRequest,
)


def _create_test_config():
    """Helper to create a valid test configuration."""
    config = ClientConfig()
    config.auth.jwt_secret_key = "test-secret-key-for-validation"
    config.auth.enable_refresh_tokens = False
    config.api_key = "test-api-key"
    return config


def _make_client():
    """Create a Client with mocked config."""
    return Client(config=_create_test_config())


class TestScheduleClientAccess:
    """Test that ScheduleClient is accessible from Client."""

    def test_schedules_property_returns_schedule_client(self):
        client = _make_client()
        assert client.schedules is not None

    def test_schedules_property_is_cached(self):
        client = _make_client()
        first = client.schedules
        second = client.schedules
        assert first is second


class TestListSchedules:
    """Test ScheduleClient.list_schedules()."""

    @patch("requests.request")
    def test_list_schedules_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "job_id": "job-1",
                "name": "Daily Report",
                "cron_expression": "0 9 * * *",
                "timezone": "UTC",
                "status": "active",
                "enabled": True,
                "next_run": "2024-01-02T09:00:00Z",
                "run_count": 10,
            }
        ]
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.schedules.list_schedules()

        assert len(result) == 1
        assert isinstance(result[0], ScheduleSummary)
        assert result[0].job_id == "job-1"
        assert result[0].name == "Daily Report"

    @patch("requests.request")
    def test_list_schedules_empty(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.schedules.list_schedules()

        assert result == []


class TestCreateSchedule:
    """Test ScheduleClient.create_schedule()."""

    @patch("requests.request")
    def test_create_schedule_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "job_id": "job-new",
            "next_run": "2024-01-02T09:00:00Z",
            "status": "active",
        }
        mock_request.return_value = mock_response

        client = _make_client()
        request = CreateScheduleRequest(
            name="Daily Report",
            cron_expression="0 9 * * *",
            agent_name="report-agent",
        )
        result = client.schedules.create_schedule(request)

        assert isinstance(result, CreateScheduleResponse)
        assert result.job_id == "job-new"
        assert result.status == "active"


class TestGetSchedule:
    """Test ScheduleClient.get_schedule()."""

    @patch("requests.request")
    def test_get_schedule_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "job_id": "job-1",
            "name": "Daily Report",
            "cron_expression": "0 9 * * *",
            "timezone": "UTC",
            "status": "active",
            "enabled": True,
            "one_shot": False,
            "next_run": "2024-01-02T09:00:00Z",
            "last_run": "2024-01-01T09:00:00Z",
            "run_count": 10,
            "failure_count": 1,
            "created_at": "2023-12-01T00:00:00Z",
            "updated_at": "2024-01-01T09:00:00Z",
        }
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.schedules.get_schedule("job-1")

        assert isinstance(result, ScheduleDetail)
        assert result.job_id == "job-1"
        assert result.one_shot is False
        assert result.failure_count == 1


class TestUpdateSchedule:
    """Test ScheduleClient.update_schedule()."""

    @patch("requests.request")
    def test_update_schedule_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "job_id": "job-1",
            "name": "Daily Report",
            "cron_expression": "0 10 * * *",
            "timezone": "America/New_York",
            "status": "active",
            "enabled": True,
            "one_shot": False,
            "next_run": "2024-01-02T10:00:00Z",
            "last_run": "2024-01-01T09:00:00Z",
            "run_count": 10,
            "failure_count": 1,
            "created_at": "2023-12-01T00:00:00Z",
            "updated_at": "2024-01-01T12:00:00Z",
        }
        mock_request.return_value = mock_response

        client = _make_client()
        request = UpdateScheduleRequest(
            cron_expression="0 10 * * *",
            timezone="America/New_York",
        )
        result = client.schedules.update_schedule("job-1", request)

        assert isinstance(result, ScheduleDetail)
        assert result.cron_expression == "0 10 * * *"

    @patch("requests.request")
    def test_update_schedule_only_sends_non_none_fields(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "job_id": "job-1",
            "name": "Daily Report",
            "cron_expression": "0 10 * * *",
            "timezone": "UTC",
            "status": "active",
            "enabled": True,
            "one_shot": False,
            "next_run": None,
            "last_run": None,
            "run_count": 0,
            "failure_count": 0,
            "created_at": "2023-12-01T00:00:00Z",
            "updated_at": "2024-01-01T12:00:00Z",
        }
        mock_request.return_value = mock_response

        client = _make_client()
        request = UpdateScheduleRequest(cron_expression="0 10 * * *")
        client.schedules.update_schedule("job-1", request)

        call_kwargs = mock_request.call_args[1]
        payload = call_kwargs["json"]
        assert "cron_expression" in payload
        assert "timezone" not in payload
        assert "policy_ids" not in payload
        assert "one_shot" not in payload


class TestDeleteSchedule:
    """Test ScheduleClient.delete_schedule()."""

    @patch("requests.request")
    def test_delete_schedule_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"job_id": "job-1", "deleted": True}
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.schedules.delete_schedule("job-1")

        assert isinstance(result, DeleteScheduleResponse)
        assert result.deleted is True


class TestPauseResumeTriger:
    """Test pause, resume, and trigger actions."""

    @patch("requests.request")
    def test_pause_schedule(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "job_id": "job-1",
            "action": "pause",
            "status": "ok",
        }
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.schedules.pause_schedule("job-1")

        assert isinstance(result, ScheduleActionResponse)
        assert result.action == "pause"

    @patch("requests.request")
    def test_resume_schedule(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "job_id": "job-1",
            "action": "resume",
            "status": "ok",
        }
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.schedules.resume_schedule("job-1")

        assert isinstance(result, ScheduleActionResponse)
        assert result.action == "resume"

    @patch("requests.request")
    def test_trigger_schedule(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "job_id": "job-1",
            "action": "trigger",
            "status": "ok",
        }
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.schedules.trigger_schedule("job-1")

        assert isinstance(result, ScheduleActionResponse)
        assert result.action == "trigger"


class TestGetScheduleHistory:
    """Test ScheduleClient.get_schedule_history()."""

    @patch("requests.request")
    def test_get_schedule_history_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "job_id": "job-1",
            "history": [
                {
                    "run_id": "run-1",
                    "started_at": "2024-01-01T09:00:00Z",
                    "completed_at": "2024-01-01T09:01:30Z",
                    "status": "success",
                    "error": None,
                    "execution_time_ms": 90000,
                },
                {
                    "run_id": "run-2",
                    "started_at": "2023-12-31T09:00:00Z",
                    "completed_at": "2023-12-31T09:00:45Z",
                    "status": "success",
                    "error": None,
                    "execution_time_ms": 45000,
                },
            ],
        }
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.schedules.get_schedule_history("job-1")

        assert isinstance(result, ScheduleHistoryResponse)
        assert result.job_id == "job-1"
        assert len(result.history) == 2
        assert isinstance(result.history[0], ScheduleRunEntry)
        assert result.history[0].run_id == "run-1"

    @patch("requests.request")
    def test_get_schedule_history_custom_limit(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"job_id": "job-1", "history": []}
        mock_request.return_value = mock_response

        client = _make_client()
        client.schedules.get_schedule_history("job-1", limit=10)

        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["params"] == {"limit": 10}


class TestGetScheduleNextRuns:
    """Test ScheduleClient.get_schedule_next_runs()."""

    @patch("requests.request")
    def test_get_next_runs_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "job_id": "job-1",
            "next_runs": [
                "2024-01-02T09:00:00Z",
                "2024-01-03T09:00:00Z",
                "2024-01-04T09:00:00Z",
            ],
        }
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.schedules.get_schedule_next_runs("job-1")

        assert isinstance(result, NextRunsResponse)
        assert len(result.next_runs) == 3

    @patch("requests.request")
    def test_get_next_runs_custom_count(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"job_id": "job-1", "next_runs": []}
        mock_request.return_value = mock_response

        client = _make_client()
        client.schedules.get_schedule_next_runs("job-1", count=5)

        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["params"] == {"count": 5}


class TestGetSchedulerHealth:
    """Test ScheduleClient.get_scheduler_health()."""

    @patch("requests.request")
    def test_get_scheduler_health_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "is_running": True,
            "store_accessible": True,
            "jobs_total": 5,
            "jobs_active": 3,
            "jobs_paused": 1,
            "jobs_dead_letter": 1,
            "global_active_runs": 2,
            "max_concurrent": 10,
            "runs_total": 150,
            "runs_succeeded": 140,
            "runs_failed": 10,
            "average_execution_time_ms": 5000.0,
            "longest_run_ms": 30000.0,
        }
        mock_request.return_value = mock_response

        client = _make_client()
        result = client.schedules.get_scheduler_health()

        assert isinstance(result, SchedulerHealthResponse)
        assert result.is_running is True
        assert result.jobs_total == 5
        assert result.runs_succeeded == 140
        assert result.average_execution_time_ms == 5000.0
