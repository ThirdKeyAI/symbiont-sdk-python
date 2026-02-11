# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-02-11

### Added

#### AgentPin Integration
- **AgentPinClient** — Client-side credential verification, discovery, and trust bundle support via `agentpin` PyPI package (v0.2.0)
  - `client.agentpin.verify_credential()` — Full 12-step online verification
  - `client.agentpin.verify_credential_offline()` — Offline verification with pre-fetched documents
  - `client.agentpin.verify_credential_with_bundle()` — Trust bundle-based verification (no network)
  - `client.agentpin.fetch_discovery_document()` — Fetch `.well-known/agent-identity.json`
  - `client.agentpin.issue_credential()` — Issue ES256 JWT credentials
  - `client.agentpin.generate_key_pair()` — P-256 key generation
  - Key pinning (TOFU) and JWK utilities
- **`Client.agentpin` property** — Lazy-loaded `AgentPinClient` accessible directly from the main `Client` instance
- **AgentPinClient export** in `symbiont` package

### Changed
- Aligned with Symbiont v1.0.1 release

### Fixed
- Fixed `setup.py` version drift (was stuck at 0.2.0, now matches `__version__`)

---

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
