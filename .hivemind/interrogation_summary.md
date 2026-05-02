# Requirements Summary: Archaeology Gap Remediation

## Executive Overview

This interrogation captured decisions to close 8 medium-severity archaeology gaps across architecture, security, process, and standards. The work consolidates disparate execution models (Flask dev server → gunicorn, APScheduler + Celery Beat → Celery-only), establishes security guardrails in CI (pip-audit, SAST, secret detection), enforces peer review on code changes, and cleanses binary files from version control. All changes are codebase and pipeline-scoped; operational issues (Jira permissions) are explicitly out-of-scope.

## Functional Requirements

- The system shall execute the Flask application using gunicorn with a single-worker configuration (`gunicorn -w 1 -b 0.0.0.0:5000 app:app`); docker-compose.yml shall invoke `bash start.sh` rather than `python app.py` directly.

- The system shall implement all scheduled job execution (email digests, ServiceNow polling, task retries, ctask assignment checks) through Celery, removing internal APScheduler use from the main Flask/gunicorn process.

- The system shall expose the same scheduler API (start, stop, get_status, force_check) backed by Celery; status queries shall use `celery.control.inspect` to query live worker state, and force-check operations shall dispatch `run_ctask_assignment.delay()` to the task queue.

- The system shall support deployment of multiple gunicorn workers without duplicate job execution for any background task.

- The system shall document every migration file (Alembic revisions, ad-hoc SQL scripts) in `migrations/README.md` with status (applied, superseded, or pending) and execution order; all future schema changes shall go through `flask db migrate`.

- The system shall enforce branch protection on the master/main branch requiring a minimum of 1 approved review before merge; this applies to all future merge requests.

- The system shall read all test credentials (superadmin password, admin password, user password) from environment variables (`TEST_SUPERADMIN_PASSWORD`, `TEST_ADMIN_PASSWORD`, `TEST_USER_PASSWORD`) in `tests/config.py`, with hardcoded localhost-only fallbacks.

- The system shall exclude binary document files (*.pdf, *.docx, *.doc, *.xlsx, *.pptx) from git version control via `.gitignore`.

- The system shall establish Confluence as the authoritative source of truth for all user and admin documentation.

## Constraints & Non-Functional Requirements

- **Volume & Performance**: Medium traffic volume (thousands of requests/day); standard caching and indexing are sufficient for this scale.

- **Concurrency Model**: Single-worker gunicorn is intentional and supported because background job execution is delegated entirely to Celery workers; Celery handles the async queue, not the Flask process.

- **Deployment Assumption**: Multiple gunicorn worker replicas are now safe and shall not cause duplicate job scheduling, as APScheduler has been removed from the primary process.

## Edge Cases & Error Handling

| Scenario | Expected Behaviour | Relates To |
|----------|-------------------|-----------|
| **Empty or null input** | System shall validate all user inputs and return clear, actionable error messages to the client; no silent failures or 500 errors. | Acceptance Criteria: User receives clear validation feedback |
| **Network timeout or third-party API unavailability** | For background/async operations (Celery tasks): max_retries=3 with 30-second countdown between attempts; transient failures self-heal without operator intervention. For startup/security failures (missing secrets, DB connectivity): abort immediately with a descriptive error message rather than starting in a degraded state. | Functional Requirement: Celery-backed scheduler |
| **User lacking required permissions** | System shall return a clear, permission-specific error message (e.g., "You do not have permission to approve this handover") rather than a generic 403. | Acceptance Criteria: User receives clear error feedback |
| **Redis/Celery outage** | Non-critical scheduler status checks (e.g., `get_status` querying worker health) shall not block the web tier if Redis is unavailable; web requests shall proceed independently of queue state. Audit-critical operations (handover submissions, audit-log writes) shall never silently fail; these shall either succeed end-to-end or return a clear error. | Functional Requirement: Scheduler status queries use inspect, not blocking I/O |
| **Partial async job failure** | Celery retry logic (3 attempts, 30-second intervals) handles transient failures in external calls (ServiceNow, email, database). If max_retries is exhausted, the task is logged and moved to the dead-letter queue; operations team is alerted by monitoring. | Functional Requirement: Celery task execution |

## Dependencies & Integrations

- **Celery Task Queue**: Message broker (Redis, RabbitMQ, or equivalent) is required for Celery worker communication; Redis outage tolerances are documented in edge cases.

- **External APIs**: Third-party REST/GraphQL services (ServiceNow polling, identity providers) are integrated as Celery tasks with built-in retry logic.

- **Authentication/SSO Provider**: OAuth or SAML provider (already integrated) continues to be used for user authentication; SSO token handling is audit-logged.

- **External Databases/Data Warehouses**: Integration points remain unchanged; Celery tasks may write to external systems as part of background job execution.

- **Jira Board 344407**: Requires HiveMind service account permissions to be resolved by Jira admin; no code change required (out-of-scope for this work).

- **Confluence**: Designated as documentation source of truth; no code dependency, but organizational discipline is required to keep it current.

- **GitLab CI/CD Pipeline**: Security scanning integrations (pip-audit for CVE scanning, Bandit-based SAST, GitLab Secret Detection template) are native to .gitlab-ci.yml.

## Scope Boundaries

### In-Scope
- **Codebase refactoring**: Gunicorn entrypoint, Celery scheduler API, migration documentation
- **CI/CD pipeline enhancements**: Security scanning layers (pip-audit, SAST, secret detection)
- **Version control hygiene**: Binary file removal, .gitignore updates
- **Documentation updates**: CLAUDE.md, CONTRIBUTING.md (credential examples, scheduler architecture), migrations/README.md
- **Branch protection policy**: Enforcement of minimum 1 review approval on master merges

### Out-of-Scope (Non-Goals)
- **Jira configuration**: HiveMind service account permissions and board access are operational admin tasks, not code changes.
- **Confluence content migration**: Existing documentation in Confluence is already authoritative; no content backport required from removed binary files.
- **Multi-environment Jira synchronization**: Currently broken (406/permission errors); will be handled separately after Jira admin resolution.
- **Gunicorn worker count tuning**: Initial deployment uses 1 worker; auto-scaling policies are not defined in this iteration.

## Acceptance Criteria

1. **Given** the application is deployed with start.sh, **when** the container starts, **then** gunicorn executes with 1 worker on port 5000 and docker-compose.yml calls `bash start.sh`.

2. **Given** a Celery worker is running, **when** a scheduled job (email digest, ServiceNow poll, task retry) is triggered, **then** it executes via Celery and completes without duplicating if multiple gunicorn workers are active.

3. **Given** services/ctask_scheduler.py is imported, **when** `get_status()` is called, **then** it returns live Celery worker state via `celery.control.inspect()` without blocking the web tier.

4. **Given** a schema change is required, **when** the developer runs `flask db migrate`, **then** a timestamped Alembic revision is created and documented in migrations/README.md.

5. **Given** a git push to a feature branch, **when** a merge request is opened to master, **then** GitLab enforces at least 1 approval from a reviewer before merge is permitted.

6. **Given** test credentials are needed, **when** tests/config.py is imported, **then** credentials are read from environment variables (TEST_SUPERADMIN_PASSWORD, etc.) with localhost-only hardcoded fallbacks.

7. **Given** the CI pipeline runs, **when** the security stage executes, **then** pip-audit scans requirements.txt for CVEs, Bandit SAST scans Python code, and secret detection scans git history; pipeline fails if known CVEs are found.

8. **Given** the git repository is cloned, **when** a user attempts to add a PDF, DOCX, or XLSX file, **then** it is rejected by .gitignore and a note directs them to Confluence.

9. **Given** a user provides empty or null input to any form, **when** they submit, **then** the system returns a specific, actionable validation error message.

10. **Given** ServiceNow returns a timeout error, **when** a Celery task is invoked, **then** it automatically retries up to 3 times with 30-second intervals before failing.

## Assumptions & Risks

| Assumption | Confidence | Risk If Wrong | Mitigation |
|-----------|-----------|-----------|-----------|
| Single-worker gunicorn + Celery is sufficient for thousands of requests/day | HIGH | Low — async workload is already distributed to Celery workers; CPU-bound work in gunicorn is minimal. | Monitor request latency; add workers if p95 latency exceeds threshold. |
| Celery workers are deployed and always running in all environments (dev, staging, prod) | MEDIUM | **Medium** — if workers are not running, all background jobs silently fail (no immediate error). | Deployment docs must explicitly cover worker startup; monitoring/alerting for worker health is required before production. |
| Redis is available and configured for Celery state management | MEDIUM | **Medium** — Redis outage blocks job enqueueing and execution; web tier is isolated per design but job pipeline halts. | Deploy Redis with replication; establish clear runbook for Redis recovery. |
| Jira admin will resolve HiveMind service account permissions on board 344407 | LOW | **Medium** — if unresolved, sprint tracking and issue correlation remain broken. | Assign ticket to Jira admin with explicit scope; confirm ETA before go-live. |
| Confluence is maintained as the single source of truth going forward | MEDIUM | **Medium** — if documentation drifts from code, users follow stale guidance. | Require documentation updates as part of PR review process; establish doc review cadence. |
| APScheduler was the only internal scheduler; no other process is triggering background jobs outside Celery | HIGH | Low — code review during refactoring surfaced all job submission points. | Code search for APScheduler imports confirms removal; static analysis validates. |
| Binary files were only 4 (2 PDFs, 2 DOCXs) and .gitignore patterns will catch future submissions | MEDIUM | Low — if future binary files slip through, they are easily caught in PR review. | Add pre-commit hook to block binary files (optional but recommended). |

## Contradictions

**None detected.** All answers are internally consistent and complementary. The decisions form a coherent strategy: (1) use gunicorn for HTTP serving, (2) delegate scheduling to Celery for scalability, (3) secure the CI/CD pipeline, (4) enforce code review, and (5) clean up version control and documentation structure.

## Open Items

- **Jira Configuration** (External): Confirm with Jira admin that HiveMind service account has been granted necessary permissions on board 344407; clarify expected resolution date.

- **Celery Worker Deployment**: Confirm that docker-compose (and all production deployment manifests) explicitly start Celery workers; document worker count configuration for different environments.

- **Monitoring & Alerting**: Define monitoring for Celery worker health (e.g., alert if no workers are alive for >5 minutes) and task failure rates (e.g., alert if task retries exceed 10% of total).

- **Pre-Commit Hooks** (Optional): Consider implementing a client-side git hook to reject binary file additions before they reach the CI pipeline.

- **Documentation Review**: Confirm CLAUDE.md and CONTRIBUTING.md have been updated to reflect the Celery scheduler architecture and environment variable credential patterns; schedule documentation review with team before merging.

- **Backwards Compatibility**: Confirm no external consumers are relying on APScheduler internal APIs; any deprecated endpoints should be marked clearly in release notes.