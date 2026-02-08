# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
