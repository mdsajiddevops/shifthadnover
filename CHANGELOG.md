# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Security
- Removed TLS private key, certificates, and SQL dumps from git tracking
- Removed secrets/ directory from git tracking
- Replaced hardcoded passwords in docker-compose.prod.yml with Docker secrets
- Replaced hardcoded fallback credentials in start.sh with fail-fast Docker secret reads
- Added RBAC decorator utility (utils/auth.py) to centralise role enforcement

### Added
- Celery + Redis background task infrastructure (celery_app.py, tasks.py)
- Prometheus metrics endpoint (/metrics) via prometheus-flask-exporter
- Swagger/OpenAPI UI (/apidocs) via flasgger
- CONTRIBUTING.md for developer onboarding
- scripts/migrations/ directory for ad-hoc SQL scripts
- scripts/utils/ directory for utility scripts

### Changed
- Pinned all Python dependencies for reproducible builds
- SMTP server/port now configurable via MAIL_SERVER / MAIL_PORT env vars
- CI pipeline replaced with real Python 3.11 install/lint/test/build stages
- Lint stage now blocking (no --exit-zero) and includes ruff format check

### Removed
- Duplicate model/service files: servicenow_models(1).py, servicenow_service(1).py
- Debug/backup route files: auth_backup, auth_debug, dashboard_temp, debug_form, test_routes, team.py.disabled
- Utility scripts moved out of docs/ into scripts/utils/

## [2.0.0] - 2025-10-01

### Added
- ServiceNow CTask integration and auto-assignment scheduler
- Email digest notifications and retry scheduler
- Collaborative handover editing (DB-polling based)
- SSO authentication support
- Multi-team access and account hierarchy
- Problem Tickets (PTasks) management
- Excel upload for handover forms
- Shift rotation pattern improvements

## [1.0.0] - 2025-01-01

### Added
- Initial release: shift handover create/draft/submit workflow
- Incident and key point tracking
- Shift roster management
- Check-in/check-out
- Email notifications
- Basic reporting
