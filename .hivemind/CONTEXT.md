# HiveMind Development Context
**Ticket:** CTCOAMSHM-6

Phase 0 and Phase 2 artifacts injected by HiveMind InfraAgent.
Run `start-dev` to launch Claude Code with this context pre-loaded.


---
## Problem Specification (Phase 0)

# Functional Specification: ShiftOps — Archaeology Gap Remediation

---

## Meta

| Field | Value |
|---|---|
| **Ticket ID** | CTCOAMSHM-6 |
| **Project** | Shifthandover (ShiftOps / shifthandover_v3) |
| **Creation Date** | 2026-05-02 |
| **Status** | Draft — Pending Review |
| **Author** | Technical Specification Agent |

---

## Problem Statement

### Summary
Remediate 8 medium-severity architecture, security, process, and hygiene gaps in ShiftOps to establish production-grade operational standards across the application, pipeline, and repository.

### User Problem
Developers, operators, and security reviewers cannot confidently deploy, extend, or audit ShiftOps: the application server entrypoint is inconsistent, background jobs may execute redundantly across worker processes, the CI pipeline provides no security feedback, test credentials are partially hardcoded in source files, binary artefacts pollute version history, and schema change history is untracked. These gaps collectively block safe scaling, create security exposure, and impede code review and onboarding.

### Business Value
Closing these gaps reduces deployment risk before the system scales beyond a single worker, enforces security hygiene ahead of CVE accumulation, ensures audit trails for regulated operations (handover submissions) are never silently lost, and introduces peer review enforcement — directly protecting the organisation from security incidents, data integrity failures, and compliance risk associated with an untested, un-audited change pipeline.

---

## Requirements

| ID | Type | Priority | Description | Depends On |
|---|---|---|---|---|
| REQ-001 | Technical | P0 | The application shall define its startup sequence in a dedicated, version-controlled startup script; the container orchestration configuration shall invoke that script rather than the application module directly. | — |
| REQ-002 | Functional | P0 | The application shall be served by a production-grade WSGI-compliant server process; the default worker count at initial deployment shall be one. | REQ-001 |
| REQ-003 | Functional | P0 | All scheduled background job execution — including email digest delivery, external service polling, task retry handling, and assignment checks — shall be delegated exclusively to a distributed task queue. No scheduled job execution shall occur within the HTTP-serving worker process. | — |
| REQ-004 | Functional | P0 | The scheduler management interface shall expose four operations — start, stop, get\_status, and force\_check — and shall source all execution state and dispatch exclusively from the distributed task queue backing REQ-003. | REQ-003 |
| REQ-005 | Non-Functional | P0 | When two or more HTTP server worker processes are active concurrently, each scheduled background job shall execute exactly once per trigger interval. Duplicate execution of any background job is not permitted regardless of worker count. | REQ-003 |
| REQ-006 | Functional | P0 | Background tasks that fail due to transient external-service errors shall be retried automatically; the system shall attempt a minimum of 3 retries with a minimum 30-second interval between each attempt. Tasks that exhaust all retry attempts shall be moved to a dead-letter queue and shall trigger an alert to the operations team. | REQ-003 |
| REQ-007 | Technical | P0 | All test credential values (superadmin password, admin password, user password) used in the test configuration file shall be sourced from named environment variables. The test configuration file shall contain no credential values that are valid or usable outside a localhost-bound context. | — |
| REQ-008 | Technical | P0 | The CI/CD pipeline shall include a dedicated security stage that executes three checks: (a) a dependency vulnerability scan against declared package requirements, (b) static application security analysis of Python source code, and (c) a scan of the full repository git history for committed secrets. The pipeline shall fail and block merges if any known CVEs are detected in declared dependencies. | — |
| REQ-009 | Technical | P0 | The repository's version control ignore configuration shall exclude binary document files of the following types from tracking: PDF, Word document (.doc, .docx), Excel spreadsheet (.xlsx), and PowerPoint presentation (.pptx). No binary document files of these types shall remain present in the repository at any commit reachable from the primary integration branch. | — |
| REQ-010 | Technical | P1 | Every database migration artefact — including all automated revision files and all ad-hoc SQL scripts — shall be catalogued in a dedicated migration registry file. Each entry shall record: the artefact's identifier, its application status (applied, pending, or superseded), and its required execution order relative to other artefacts. | — |
| REQ-011 | Technical | P1 | All future database schema changes shall be introduced exclusively through the automated schema migration toolchain; no schema modification shall be applied to any environment without a corresponding tracked migration artefact registered per REQ-010. | REQ-010 |
| REQ-012 | Technical | P1 | The version control platform shall enforce a branch protection policy on the primary integration branch (master/main) requiring a minimum of one approved peer review from a designated reviewer before any merge is permitted. | — |
| REQ-013 | Non-Functional | P1 | The `get_status` operation of the scheduler management interface shall complete without blocking in-flight HTTP requests when the task queue broker is unavailable; web-tier request handling shall proceed independently of task queue reachability. Response time for `get_status` under broker-unavailable conditions shall not exceed 5 seconds. | REQ-004 |
| REQ-014 | Functional | P1 | The application shall abort its startup sequence and emit a descriptive, human-readable error message if any of the following conditions are detected at launch: required secrets are absent, required secrets fail decryption, or the primary database is unreachable. The application shall not enter a running state under any of these conditions. | — |
| REQ-015 | Functional | P0 | Audit-critical operations — defined as handover submissions and audit-log writes — shall never silently fail. Each such operation shall either complete successfully end-to-end or return a clear, specific error to the caller; partial state commits without corresponding audit records are not permitted. | — |
| REQ-016 | Functional | P1 | On any form submission, the system shall validate all user-supplied input fields. If one or more fields are invalid (including empty, null, or out-of-range values), the system shall return a specific, field-level, actionable error message for each invalid field. No form submission shall produce a silent failure or an unhandled server error. | — |
| REQ-017 | Functional | P1 | When a user attempts an operation they are not authorised to perform, the system shall return an error message that identifies the specific missing privilege or role required. Generic authorisation error responses that do not identify the permission context are not acceptable. | — |
| REQ-018 | Non-Functional | P2 | All end-user and administrator documentation shall be maintained in a single authoritative location. Documentation shall remain current with the deployed version of the application at all times. | — |

---

## Acceptance Criteria

> **Notation:** P0 requirements carry both a happy-path (✅) and an error/unhappy-path (❌) AC. P1 and P2 requirements carry at minimum one testable AC.

---

**REQ-001 — Startup Script Entrypoint**

- **AC-001a** ✅ (REQ-001): Given the application is deployed via container orchestration, when the container starts, then the orchestration configuration invokes the startup script (`start.sh`) rather than the application module directly, and the WSGI server process is confirmed running.
- **AC-001b** ❌ (REQ-001): Given the startup script is absent or contains a syntax error, when the container starts, then the container exits with a non-zero exit code and emits a descriptive error message within 10 seconds; no server process is left in a partially initialised state.

**REQ-002 — Production WSGI Server**

- **AC-002a** ✅ (REQ-002): Given `start.sh` is invoked, when the server starts, then a WSGI-compliant server process binds to port 5000, reports 1 active worker, and begins accepting HTTP requests within 30 seconds.
- **AC-002b** ❌ (REQ-002): Given port 5000 is already bound by another process, when the server starts, then the WSGI server exits with a non-zero code and logs an address-in-use error; no silent hang occurs.

**REQ-003 — Distributed Task Queue for Background Jobs**

- **AC-003a** ✅ (REQ-003): Given a task queue worker process is running, when a scheduled trigger fires for any of the four job types (email digest, external service poll, task retry, assignment check), then the job executes via the task queue worker and no execution occurs within the HTTP server process.
- **AC-003b** ❌ (REQ-003): Given the task queue broker is unavailable, when a scheduled job trigger fires, then the job is not silently discarded; a structured log entry recording the failure to enqueue is produced, and the HTTP server process continues serving requests uninterrupted.
- **AC-003c** ❌ (REQ-003): Given the application source code is inspected, when a static search for APScheduler imports is performed across all modules, then zero matches are found.

**REQ-004 — Scheduler Management Interface**

- **AC-004a** ✅ (REQ-004): Given a task queue worker is active, when `get_status()` is invoked, then the response reflects the live worker state sourced from the task queue and is returned within 3 seconds.
- **AC-004b** ✅ (REQ-004): Given a task queue worker is active, when `force_check()` is invoked, then a job is dispatched to the task queue within 1 second and a confirmation is returned to the caller.
- **AC-004c** ❌ (REQ-004): Given the task queue broker is unavailable, when `get_status()` is invoked, then it returns a degraded-state indicator (not a 500 error) and does not block for longer than 5 seconds.

**REQ-005 — No Duplicate Job Execution**

- **AC-005a** ✅ (REQ-005): Given two HTTP server worker processes are running concurrently, when a scheduled trigger fires for the email digest job, then exactly one execution is logged by the task queue; no duplicate execution record appears.
- **AC-005b** ❌ (REQ-005): Given one of two concurrently running HTTP workers is terminated mid-cycle, when the next trigger fires, then the surviving worker (or task queue) executes the job exactly once and no duplicate or missed execution occurs.

**REQ-006 — Background Task Retry and Dead-Letter Queue**

- **AC-006a** ✅ (REQ-006): Given a ServiceNow polling task fails on attempt 1 with a timeout error, when the retry scheduler runs, then the task is retried at attempt 2 no sooner than 30 seconds after attempt 1; on success at attempt 2, no further retries are scheduled.
- **AC-006b** ❌ (REQ-006): Given a background task fails on all 3 retry attempts, when the final retry is exhausted, then the task is moved to the dead-letter queue, a structured log entry is written, and the operations team receives an alert; no silent discard occurs.

**REQ-007 — Environment-Variable Test Credentials**

- **AC-007a** ✅ (REQ-007): Given `TEST_SUPERADMIN_PASSWORD`, `TEST_ADMIN_PASSWORD`, and `TEST_USER_PASSWORD` environment variables are set, when `tests/config.py` is imported, then the credential values used in tests match those environment variable values exactly.
- **AC-007b** ❌ (REQ-007): Given the three environment variables are unset and the test suite is executed against a non-localhost target, then the test suite fails with a configuration error before any credential is transmitted; no production-valid credential is exposed.
- **AC-007c** ❌ (REQ-007): Given the `tests/config.py` source file is inspected, when a search for hardcoded non-localhost credential strings is performed, then zero matches are found.

**REQ-008 — CI Security Stage**

- **AC-008a** ✅ (REQ-008): Given a CI pipeline run on a branch with clean dependencies and no committed secrets, when the security stage executes, then all three checks (dependency CVE scan, SAST, secret history scan) complete without findings and the pipeline proceeds to subsequent stages.
- **AC-008b** ❌ (REQ-008): Given a dependency with a known CVE is present in the declared package requirements file, when the dependency vulnerability scan runs, then the pipeline fails, the CVE identifier and affected package are reported in the pipeline log, and the merge is blocked.
- **AC-008c** ❌ (REQ-008): Given a secret string is committed in the repository's git history, when the secret detection scan runs, then the pipeline fails and the offending commit reference is reported.

**REQ-009 — Binary File Exclusion**

- **AC-009a** ✅ (REQ-009): Given the version control ignore configuration is in place, when a developer executes `git add` on a file matching any of the excluded extensions (pdf, doc, docx, xlsx, pptx), then git reports the file as ignored and does not stage it.
- **AC-009b** ❌ (REQ-009): Given the primary integration branch history is inspected, when a search for tracked binary document files (pdf, doc, docx, xlsx, pptx) is performed across all commits, then zero such files are found at any reachable commit.

**REQ-010 — Migration Registry**

- **AC-010** (REQ-010): Given the `migrations/README.md` file is present, when it is reviewed, then every Alembic revision file and every ad-hoc SQL script in the `migrations/` directory has a corresponding entry recording its identifier, status (applied / pending / superseded), and execution order.

**REQ-011 — Schema Changes via Migration Toolchain**

- **AC-011** (REQ-011): Given a developer introduces a schema change via the migration toolchain, when the toolchain generates the migration artefact, then a new timestamped revision file is created and an entry is added to the registry in `migrations/README.md`; no schema change is accepted in a merge request without both artefacts present.

**REQ-012 — Branch Protection Policy**

- **AC-012a** (REQ-012): Given a merge request to the primary integration branch with zero approvals, when a merge is attempted, then the version control platform blocks the merge and displays a message requiring at least one approval.
- **AC-012b** (REQ-012): Given a merge request to the primary integration branch with one or more approvals, when a merge is attempted, then the merge is permitted by the branch protection policy.

**REQ-013 — Non-Blocking Scheduler Status**

- **AC-013** (REQ-013): Given the task queue broker is unavailable, when `get_status()` is invoked on the scheduler interface, then the response is returned within 5 seconds with a degraded-state indicator; no HTTP request processing thread is blocked during this call.

**REQ-014 — Fail-Fast Startup**

- **AC-014a** (REQ-014): Given a required application secret is absent from the secrets store at launch, when the application starts, then it exits within 10 seconds and logs a specific error identifying the missing secret by name; no server port is bound.
- **AC-014b** (REQ-014): Given the primary database is unreachable at launch, when the application starts, then it exits within 10 seconds and logs a connectivity error identifying the target; no server port is bound.

**REQ-015 — Audit-Critical Operations Never Silently Fail**

- **AC-015a** ✅ (REQ-015): Given a user submits a handover, when both the handover record and the audit log entry are successfully persisted, then the user receives a success confirmation and the audit log contains a timestamped record of the submission.
- **AC-015b** ❌ (REQ-015): Given the audit log write fails during a handover submission, when the operation is attempted, then the entire operation is rolled back, the handover record is not persisted, and the user receives a clear error message; no partial state is written.

**REQ-016 — Input Validation with Actionable Errors**

- **AC-016a** (REQ-016): Given a user submits a form with one or more required fields left empty, when the submission is received, then the system returns a response identifying each empty field by name with an actionable correction message; no 500 error is returned.
- **AC-016b** (REQ-016): Given a user submits a form with a field containing an out-of-range value, when the submission is received, then the system returns a field-level error message specifying the valid range; the submission is not silently accepted or discarded.

**REQ-017 — Permission-Specific Error Messages**

- **AC-017** (REQ-017): Given a `user`-role account attempts to approve a handover (a `team_admin` privilege), when the attempt is made, then the system returns an error message specifically identifying the required role or privilege (e.g., "team_admin access is required to approve handovers") rather than a generic 403 response.

**REQ-018 — Single Authoritative Documentation Source**

- **AC-018** (REQ-018): Given an end-user or administrator seeks guidance on any documented feature, when they access the designated documentation platform, then they find documentation current with the deployed application version; no conflicting documentation exists in the repository as binary file artefacts.

---

## Constraints

### Performance
- The application is deployed at medium traffic volume (thousands of HTTP requests per day). Standard database indexing and response caching are the expected performance controls at this scale.
- Scheduler `get_status` operations shall complete within **5 seconds** under broker-unavailable conditions (REQ-013).
- The WSGI server shall begin accepting HTTP requests within **30 seconds** of container start (REQ-002).
- Application startup failure detection (missing secrets, DB unreachable) shall produce a terminal exit within **10 seconds** (REQ-014).
- Background task retry intervals shall not be less than **30 seconds** between attempts (REQ-006).

### Security
- Test credential values must not be valid outside a localhost-bound context. Hardcoded fallback values are permitted only for `localhost` targets (REQ-007).
- The CI security stage must execute dependency CVE scanning, static application security analysis, and committed-secret detection on every pipeline run. Any detected CVE in declared dependencies is a pipeline-blocking failure (REQ-008).
- The task queue broker connection must be authenticated; broker credentials shall not appear in source code or version-controlled configuration files.
- Session token validation runs on every HTTP request (existing control; must be preserved through all refactoring).
- SSO OAuth client credentials (client ID, client secret, tenant ID) are stored encrypted via the existing secrets manager; this mechanism shall not be altered by this work.
- RBAC enforcement remains inline per route (existing pattern); no RBAC logic shall be removed or weakened during scheduler or entrypoint refactoring.

### Compatibility
- The external interface of the scheduler management operations (start, stop, get_status, force_check) shall remain unchanged from the caller's perspective; only the internal execution backing changes (REQ-004).
- All existing Flask Blueprint route URLs, HTTP methods, and response content types shall remain unchanged; this work does not modify any user-facing endpoint contract.
- All existing session and authentication mechanisms (SSO and local login) shall continue to function without modification.

### Accessibility
Not applicable to this scope — no new user-interface surfaces are introduced.

---

## Non-Goals

| Non-Goal | Rationale |
|---|---|
| **Jira configuration and HiveMind service account permissions** | This is an operational admin task with no code dependency. Jira board 344407 permission errors (406) require Jira admin action; no code change is required or in-scope. |
| **Confluence content migration from removed binary files** | Confluence is already the designated authoritative documentation source. No content backport from removed repository binary files is required. |
| **Gunicorn worker count auto-scaling policy** | Initial deployment is intentionally single-worker. Scaling policy definition (thresholds, triggers, upper bounds) is deferred to a subsequent iteration after production baseline metrics are established. |
| **Multi-environment Jira issue synchronisation** | Currently broken due to the permission issue noted above; repair is explicitly deferred pending Jira admin resolution. |
| **New feature development or user-facing capability changes** | This specification addresses only gap remediation — infrastructure, pipeline, hygiene, and process — not new product functionality. |
| **Pre-commit client-side git hooks** | Optional enhancement noted in open items; enforcement is handled at CI pipeline level in this iteration. Client-side hooks are not a deliverable. |

---

## Assumptions

| # | Assumption | Risk If Wrong | Risk Level | Validation Required Before Implementation |
|---|---|---|---|---|
| A-001 | A single WSGI worker process combined with distributed task queue workers is sufficient to handle thousands of HTTP requests per day at acceptable latency. | CPU-bound work in the HTTP process could cause latency spikes under concurrent load if the assumption is wrong; however, async workloads are already delegated to the task queue. | **Low** | Monitor p95 request latency post-deployment; add workers if latency exceeds agreed threshold. |
| A-002 | Task queue workers are deployed and running in all environments (development, staging, production) as part of the standard container orchestration setup. | If workers are not started, all background jobs silently fail with no immediate HTTP-tier indication. | **Medium** | Confirm docker-compose and all production deployment manifests explicitly start worker processes before merging this work. |
| A-003 | The message broker (required for the task queue) is deployed with sufficient availability and the web tier can tolerate broker unavailability for non-blocking status queries. | A broker outage halts the entire background job pipeline; job enqueueing fails until the broker recovers. | **Medium** | Confirm broker replication/HA configuration is in place; document recovery runbook before production deployment. |
| A-004 | APScheduler is the only internal scheduler in the codebase; no other mechanism is triggering background jobs outside the task queue. | If additional scheduler instances exist and are not migrated, background jobs will continue to execute in the HTTP process, violating REQ-003 and REQ-005. | **Low** | Static code search for all scheduler-related imports (APScheduler, `threading.Timer`, `sched` module, etc.) shall be performed as part of the migration PR review. |
| A-005 | Only 4 binary document files exist in the repository (2 PDFs, 2 DOCXs); `.gitignore` patterns are sufficient to prevent future additions. | If additional binary files are present or are added without detection, repository bloat continues and audit artefacts remain version-controlled. | **Low** | Full repository audit via `git log --all -- '*.pdf' '*.docx' '*.doc' '*.xlsx' '*.pptx'` shall be run before the cleanup commit is merged. |
| A-006 | Jira admin will resolve HiveMind service account permissions on board 344407 within the project timeline. | Sprint tracking and issue correlation remain broken for the duration if unresolved; team velocity reporting is unreliable. | **Medium** | Assign explicit ticket to Jira admin with a documented ETA before project go-live. |
| A-007 | Confluence is maintained as the single source of truth going forward through organisational discipline and process, not automated enforcement. | Documentation will drift from code unless reviews explicitly include documentation sign-off. | **Medium** | Add documentation update as a mandatory checklist item in the merge request template before enforcing REQ-018. |

---

## Edge Cases

| # | Scenario | Expected Behaviour | Related Requirement |
|---|---|---|---|
| EC-001 | A form field receives a null or empty string submission | The system validates the field, returns a specific field-level error message naming the field and the correction needed, and does not proceed with partial data. No 500 error is emitted. | REQ-016 |
| EC-002 | The task queue broker becomes unavailable while a background task is mid-execution | The in-flight task continues to execute if already dequeued by a worker. New enqueue operations fail and are logged. The web tier continues serving HTTP requests without blocking. Retry-eligible tasks are queued for re-attempt when the broker recovers. | REQ-003, REQ-013 |
| EC-003 | A background task exhausts all 3 retry attempts | The task is moved to the dead-letter queue with full context (task type, input arguments, error trace, timestamp). An operations alert is dispatched. The task is not silently dropped and is recoverable by an operator. | REQ-006 |
| EC-004 | A developer attempts to commit a `.pdf` file to the repository after `.gitignore` is updated | The file is rejected at staging time; git reports the file as ignored. A comment or note in `.gitignore` directs the developer to the authoritative documentation platform. | REQ-009 |
| EC-005 | A handover submission succeeds at the database level but the audit log write fails | The entire operation is rolled back atomically. Neither the handover record nor a partial audit entry is persisted. The user receives an explicit error message indicating the submission failed and should be retried. | REQ-015 |
| EC-006 | Two WSGI workers simultaneously attempt to enqueue the same scheduled job | Exactly one job execution record appears in the task queue. The distributed task queue's deduplication or lock mechanism prevents the second enqueue from producing a duplicate execution. | REQ-005 |
| EC-007 | The application is started with a valid secrets store but the primary database is unreachable | The application detects the connectivity failure during startup health checks, logs a specific error identifying the database target, and exits with a non-zero code. No HTTP port is bound; no server enters a degraded running state. | REQ-014 |
| EC-008 | `get_status()` is called while the task queue broker connection is timing out | The scheduler interface returns a degraded-state indicator within 5 seconds without waiting for the full broker connection timeout. No HTTP worker thread is blocked; other HTTP requests continue to be processed normally during this period. | REQ-004, REQ-013 |
| EC-009 | A `user`-role account submits a request to approve a handover | The system returns a specific permission error identifying that `team_admin` (or higher) access is required for approval. The operation is not performed. The response is not a generic HTTP 403. | REQ-017 |

---

## Backward Compatibility

**Scheduler Management Interface:** The external operation signatures (start, stop, get_status, force_check) are preserved. Internal execution backing is replaced; callers observe no change in interface shape or response structure. No breaking change.

**HTTP Endpoint Contracts:** No Flask Blueprint route URLs, HTTP methods, query parameters, or response content types are modified by this work. All ~45–50 endpoint contracts in the existing `routes/` modules remain unchanged. No breaking change.

**Authentication and Session Behaviour:** SSO and local login flows, session token lifecycle, and per-request `validate_session()` behaviour are unchanged. No breaking change.

**APScheduler Internal API:** APScheduler is removed from the application. If any code outside the primary application codebase (e.g., integration scripts, external tooling) directly invokes APScheduler's internal API, those callers will break. The interrogation confirms a code-search review shall be performed to validate no such external dependency exists before the removal is merged. **Risk: Low — no external callers identified.** If callers are found, they shall be documented in the release notes as a breaking change with a migration path to the equivalent task queue dispatch call.

**Migration Artefacts:** The `migrations/README.md` registry is a new file; no existing file is modified or removed. All existing Alembic revision files are retained. No breaking change to schema history.

**Test Configuration:** The `tests/config.py` file changes from hardcoded credentials to environment variable reads with localhost-only fallbacks. Any CI pipeline job that runs the test suite without the three environment variables set will fail until those variables are configured in the CI environment. **This is an intentional, documented change requiring pipeline configuration updates before deployment.**

---

## Dependencies

| Dependency | Type | Role | Availability Risk |
|---|---|---|---|
| **Distributed Task Queue (Celery + Broker)** | Infrastructure | Background job execution, scheduler state, retry logic (REQ-003, REQ-004, REQ-006) | Medium — broker (Redis or equivalent) must be deployed and healthy in all environments |
| **Message Broker (Redis or equivalent)** | Infrastructure | Task queue transport layer; required for worker communication | Medium — single point of failure if not replicated; recovery runbook required |
| **GitLab CI/CD Pipeline** | Platform | Hosts and executes the security stage (dependency scan, SAST, secret detection) for REQ-008 | Low — existing infrastructure; security stage is a configuration addition |
| **Dependency Vulnerability Scanner (pip-audit)** | CI Tooling | Scans `requirements.txt` for known CVEs as part of the security stage | Low — open-source tool; version pinned in CI config |
| **Static Application Security Testing Tool (Bandit)** | CI Tooling | Performs Python SAST on application source as part of the security stage | Low — open-source tool; version pinned in CI config |
| **GitLab Secret Detection Template** | CI Tooling | Scans git history for committed secrets as part of the security stage | Low — native GitLab CI template; no external dependency |
| **EPAM Microsoft Identity Provider (SSO)** | External Service | OAuth 2.0 / SAML authentication; unchanged by this work | Low — existing integration; no modification in scope |
| **ServiceNow** | External API | Target of polling tasks subject to retry logic (REQ-006) | Medium — external service availability is the primary driver of retry exhaustion scenarios |
| **Confluence** | Documentation Platform | Authoritative source of truth for all user and administrator documentation (REQ-018) | Low — organisational process dependency; no code dependency |
| **Alembic (via Flask-Migrate)** | Tooling | Automated schema migration generation and tracking (REQ-011) | Low — already integrated; registry documentation is additive |

---

## Glossary

| Term | Definition |
|---|---|
| **Alembic** | Database schema migration framework used by Flask-Migrate to generate versioned migration scripts. |
| **APScheduler** | Advanced Python Scheduler — a Python library previously used to schedule in-process background jobs within the Flask application. Removed by this work. |
| **Archaeology Gap** | A discrepancy between the intended or documented architecture and the actual current state of the codebase, discovered during technical review. |
| **Branch Protection** | A version control platform policy that enforces conditions (e.g., peer approval count) before a merge to a protected branch is permitted. |
| **CVE** | Common Vulnerabilities and Exposures — a publicly catalogued software security vulnerability with a unique identifier (e.g., CVE-2024-XXXXX). |
| **Dead-Letter Queue (DLQ)** | A queue that holds messages (tasks) that have failed all retry attempts, making them available for manual operator inspection and recovery. |
| **Distributed Task Queue** | A system that decouples job submission from execution by routing tasks to worker processes via a message broker. In this project, Celery over Redis. |
| **Flask Blueprint** | Flask's module system for organising route handlers; ShiftOps has approximately 45–50 Blueprints, each scoped to a domain area. |
| **Fernet** | A symmetric authenticated encryption scheme used by the ShiftOps secrets manager to encrypt credentials at rest. |
| **Gunicorn** | Green Unicorn — a production-grade WSGI-compliant HTTP server for Python applications. Replaces the Flask development server in this work. |
| **Migration Registry** | The `migrations/README.md` file cataloguing all database migration artefacts with their status and execution order. |
| **RBAC** | Role-Based Access Control — the authorisation model used in ShiftOps (`super_admin` → `account_admin` → `team_admin` → `user`). |
| **SAST** | Static Application Security Testing — automated analysis of source code for security vulnerabilities without executing the program. In this project, performed by Bandit. |
| **SSO** | Single Sign-On — the primary authentication mechanism for ShiftOps, implemented via OAuth 2.0 / SAML against the EPAM Microsoft identity provider. |
| **WSGI** | Web Server Gateway Interface — the Python standard interface between web servers and application frameworks. |
| **Celery** | An open-source distributed task queue used to execute background jobs asynchronously in worker processes separate from the HTTP tier. |
| **pip-audit** | A Python CLI tool that audits declared package dependencies against known CVE databases. |
| **Bandit** | A Python-specific SAST tool that analyses source code for common security issues. |
| **start.sh** | The dedicated startup script that encapsulates the application server launch command; invoked by the container orchestration configuration. |


---
## Technical Design Specification (Phase 2)

# Architecture Design Specification: ShiftOps — Archaeology Gap Remediation

---

## Meta

| Field | Value |
|---|---|
| **Ticket ID** | CTCOAMSHM-6 |
| **Project** | Shifthandover (ShiftOps / shifthandover_v3) |
| **Creation Date** | 2026-05-02 |
| **Spec Reference** | Functional Specification: ShiftOps — Archaeology Gap Remediation (Draft) |
| **Design Status** | Ready for Engineering Review |
| **Author** | Architecture Design Agent |

---

## Problem Spec Reference

The approved specification (CTCOAMSHM-6) identifies 18 requirements across 8 medium-severity gaps: an inconsistent application entrypoint (REQ-001/002), in-process background job scheduling that creates duplicate-execution risk under multi-worker deployment (REQ-003–006), hardcoded test credentials (REQ-007), an absent CI security stage (REQ-008), binary artefacts tracked in version control (REQ-009), untracked schema migration history (REQ-010/011), no peer-review enforcement on the primary branch (REQ-012), blocking scheduler status queries (REQ-013), no fail-fast startup validation (REQ-014), silently-failable audit operations (REQ-015), absent field-level form validation (REQ-016), and generic RBAC error responses (REQ-017/018). Full requirements, acceptance criteria, and constraints are documented in the approved specification. This document does not duplicate them.

---

## Current Architecture

### Existing Components Relevant to This Work

**Application Server:** The Flask application is started via `python app.py`, which uses Flask's built-in development server. This is the entrypoint targeted by `docker-compose.yml`. The development server is not suitable for production and does not support multi-worker operation.

**Background Job Scheduler:** APScheduler runs embedded within the Flask process. When `docker-compose.yml` starts two or more `web` service replicas, each replica spawns its own APScheduler instance, resulting in each scheduled job (email digest, ServiceNow poll, task retry handler, ctask assignment check) executing once per active process per trigger interval — a direct duplicate-execution risk.

**Celery Infrastructure:** Celery is already present in the codebase as a dependency, used for ad-hoc async task dispatch. A Celery worker process and Redis broker are referenced in configuration but are not the canonical execution path for the four scheduled job types. Celery Beat is not deployed.

**Scheduler Management Service:** `services/ctask_scheduler.py` exposes `start()`, `stop()`, `get_status()`, and `force_check()` operations. The current implementation calls APScheduler's internal API for state management. `routes/scheduler.py` maps these to HTTP endpoints.

**Authentication and Session Management:** `auth.py` and `routes/auth.py` handle local login. `routes/sso_auth.py` handles OAuth 2.0 / SAML via EPAM Microsoft identity provider. `validate_session()` middleware runs on every request, validating the `session_token` against the database. These mechanisms are not modified by this work.

**RBAC:** Authorization is enforced inline within each of the ~45–50 Blueprint route handler functions. There is no shared decorator or centralized policy object. No RBAC logic is removed or weakened by this work; the inline pattern is preserved.

**Test Configuration:** `tests/config.py` contains test credential values that include valid (non-localhost) credential strings mixed with configuration data. Three credential fields require extraction to environment variables.

**CI/CD Pipeline:** A `.gitlab-ci.yml` exists for the project. It does not currently include a security stage. No dependency CVE scan, SAST, or committed-secret detection job is defined.

**Version Control:** `.gitignore` does not currently exclude binary document formats (`.pdf`, `.doc`, `.docx`, `.xlsx`, `.pptx`). At least 4 binary document files are tracked in the repository history.

**Database Migrations:** `migrations/` contains Alembic revision files. An `ad-hoc SQL scripts` directory may also exist. No registry file (`README.md`) catalogs these artefacts with status and execution order.

### Patterns in Use

- **Server-Side Rendering:** All user-facing routes return rendered HTML via Jinja2 templates. Limited JSON endpoints exist for in-page operations.
- **Blueprint Modularisation:** Each domain area (handover, incidents, scheduler, etc.) is a separate Flask Blueprint registered in `app.py`.
- **Inline Authorization:** RBAC checks are written directly inside route handler functions with no decorator abstraction.
- **Fernet Encryption for Secrets:** OAuth credentials and sensitive config are stored encrypted in the database, loaded via `Config.init_from_database()` at startup.
- **Session-Token Database Validation:** Every request passes through `validate_session()`, which reads the `session_tokens` table.

### What is Modified vs. What is New

| File / Component | Status |
|---|---|
| `services/ctask_scheduler.py` | **Modified** — internal execution backing replaced with Celery |
| `routes/scheduler.py` | **Modified** — response format preservation; no URL changes |
| `docker-compose.yml` | **Modified** — CMD updated; worker and beat services added |
| `tests/config.py` | **Modified** — credentials sourced from env vars |
| `.gitlab-ci.yml` | **Modified** — security stage added |
| `.gitignore` | **Modified** — binary extensions added |
| `start.sh` | **New** |
| `gunicorn.conf.py` | **New** |
| `startup_checks.py` | **New** |
| `celery_app.py` | **New** |
| `celeryconfig.py` | **New** |
| `tasks/` package | **New** |
| `services/audit_service.py` | **New** |
| `utils/validators.py` | **New** |
| `utils/rbac_errors.py` | **New** |
| `migrations/README.md` | **New** |

---

## Architecture

### Pattern

**Layered Monolith with Separated Async Execution Tier.** The existing Flask monolith is retained as the HTTP-serving layer (no decomposition into microservices). A discrete Celery execution tier is formalized as the exclusive path for all background job execution. The two tiers communicate only through the Redis message broker and share no in-process scheduler state. This pattern is chosen because: (a) it closes REQ-003/005 without requiring application restructuring, (b) Celery Beat's single-process design provides native deduplication for scheduled jobs, eliminating the multi-worker duplicate-execution problem at the architectural level, and (c) it preserves all existing Blueprint contracts, session mechanics, and RBAC patterns.

---

### Components

| ID | Name | Type | Responsibility | Dependencies | File Path |
|---|---|---|---|---|---|
| **COMP-001** | Startup Script | Shell Script | Runs startup health checks and, on success, launches the Gunicorn process; serves as the sole container entrypoint. | COMP-002, COMP-004 | `start.sh` |
| **COMP-002** | Gunicorn Process Configuration | Configuration | Declares all Gunicorn server parameters (worker count, bind address, timeout, log level, access log format) in a version-controlled file. | — | `gunicorn.conf.py` |
| **COMP-003** | Container Orchestration Configuration | Configuration | Defines all service processes (web, worker, beat, redis) and their startup commands; the `web` service CMD is updated to invoke COMP-001. | COMP-001 | `docker-compose.yml` |
| **COMP-004** | Startup Health Checker | Utility Script | Validates that all required application secrets are present and decryptable and that the primary database is reachable; exits non-zero with a descriptive message on any failure. | — | `startup_checks.py` |
| **COMP-005** | Celery Application Factory | Service Module | Creates and configures the single shared Celery application instance, sourcing broker URL and result backend URL exclusively from environment variables. | COMP-006 | `celery_app.py` |
| **COMP-006** | Celery Periodic Schedule Configuration | Configuration Module | Declares the Celery Beat schedule: maps each of the four periodic job types to their task function reference and trigger interval. | COMP-007, COMP-008, COMP-009, COMP-010 | `celeryconfig.py` |
| **COMP-007** | Email Digest Task | Celery Task | Defines and executes the periodic email digest delivery job as a Celery task with retry policy and failure routing to COMP-011. | COMP-005, COMP-011 | `tasks/email_tasks.py` |
| **COMP-008** | ServiceNow Polling Task | Celery Task | Defines and executes the periodic external ServiceNow API polling job as a Celery task with retry policy and failure routing to COMP-011. | COMP-005, COMP-011 | `tasks/servicenow_tasks.py` |
| **COMP-009** | Task Retry Sweep Task | Celery Task | Defines and executes the periodic task retry handling sweep as a Celery task with retry policy and failure routing to COMP-011. | COMP-005, COMP-011 | `tasks/retry_tasks.py` |
| **COMP-010** | CTask Assignment Check Task | Celery Task | Defines and executes the periodic ctask assignment verification job as a Celery task with retry policy and failure routing to COMP-011. | COMP-005, COMP-011 | `tasks/ctask_tasks.py` |
| **COMP-011** | Dead-Letter Queue Handler | Celery Task / Service | Receives exhausted tasks (those that have consumed all retries), persists a record to the `failed_tasks` table, and dispatches an alert to the operations team. | COMP-005 | `tasks/dlq_handler.py` |
| **COMP-012** | Scheduler Management Service | Service | Exposes `start()`, `stop()`, `get_status()`, and `force_check()` operations backed exclusively by Celery; `get_status()` uses a bounded-timeout inspect call to remain non-blocking. | COMP-005, COMP-010 | `services/ctask_scheduler.py` |
| **COMP-013** | Scheduler HTTP Route Handler | Flask Blueprint | Maps HTTP requests to COMP-012 operations and formats responses; preserves all existing route paths, HTTP methods, and response shapes. | COMP-012 | `routes/scheduler.py` |
| **COMP-014** | Audit Transaction Service | Service | Executes handover record persistence and audit log writes within a single atomic database transaction; rolls back both operations if either fails and surfaces a specific error to the caller. | — | `services/audit_service.py` |
| **COMP-015** | Form Field Validator | Utility | Accepts a map of field names to submitted values and a validation rule set; returns a map of field names to actionable error messages for each invalid field, or an empty map if all fields are valid. | — | `utils/validators.py` |
| **COMP-016** | RBAC Error Message Resolver | Utility | Accepts the user's current role and the required role/privilege for a given operation; returns a specific, human-readable error message identifying the exact missing permission context. | — | `utils/rbac_errors.py` |
| **COMP-017** | CI/CD Pipeline Configuration | CI Configuration | Adds a `security` stage to the pipeline containing three jobs: dependency CVE scan (pip-audit), Python SAST (Bandit), and git history secret detection (GitLab template); the CVE scan job is configured as a blocking gate. | — | `.gitlab-ci.yml` |
| **COMP-018** | Version Control Ignore Rules | Configuration | Adds binary document extension patterns (`*.pdf`, `*.doc`, `*.docx`, `*.xlsx`, `*.pptx`) to prevent future tracking; includes a comment directing developers to the Confluence documentation source. | — | `.gitignore` |
| **COMP-019** | Test Credential Configuration | Test Configuration | Sources all three test credential values from named environment variables; falls back to localhost-only sentinel values when env vars are absent; includes a guard that aborts test execution if credentials are the sentinel values and the target is not localhost. | — | `tests/config.py` |
| **COMP-020** | Migration Registry | Documentation File | Catalogues every Alembic revision file and every ad-hoc SQL script in `migrations/` with its identifier, application status (applied / pending / superseded), and required execution order. | — | `migrations/README.md` |

---

### Data Flow

#### DF-01: Container Startup (REQ-001, REQ-002, REQ-014)

```
Container orchestration (docker-compose.yml / COMP-003)
  → invokes: start.sh (COMP-001)
      → invokes: startup_checks.py (COMP-004)
          → reads: required secrets from secrets store
          → attempts: primary database connectivity probe
          ← exits 1 + descriptive message if any check fails → Container exits; no port bound
          ← exits 0 if all checks pass
      → invokes: gunicorn with gunicorn.conf.py (COMP-002)
          → binds port 5000
          → starts 1 HTTP worker process
          ← serving HTTP requests
```

#### DF-02: Scheduled Background Job Execution (REQ-003, REQ-005, REQ-006)

```
Celery Beat process (configured via COMP-006)
  → at trigger interval: enqueues task message to Redis broker
      → Celery worker process dequeues message
          → executes task function (COMP-007 / COMP-008 / COMP-009 / COMP-010)
              → on success: task completes; result written to result backend
              → on transient failure (attempt ≤ 3):
                  → task re-enqueued with 30-second countdown delay
              → on final failure (attempt 3 exhausted):
                  → COMP-011 (DLQ handler) invoked
                      → writes record to failed_tasks table
                      → dispatches operations alert
```

> **Deduplication note:** Celery Beat is a single process separate from gunicorn workers. It enqueues each job exactly once per interval regardless of how many gunicorn HTTP workers are running, eliminating the duplicate-execution problem at the architectural level (REQ-005/EC-006).

#### DF-03: Scheduler Status Query (REQ-004, REQ-013)

```
HTTP client
  → GET /scheduler/status
      → routes/scheduler.py (COMP-013)
          → services/ctask_scheduler.get_status() (COMP-012)
              → celery.control.inspect(timeout=2.0)
                  → on broker available: returns live worker state
                  → on broker unavailable (timeout):
                      → returns degraded-state indicator object within ≤5s
          ← formats response (preserving existing response shape)
      ← HTTP 200 (nominal or degraded indicator)
```

#### DF-04: Scheduler Force Check (REQ-004)

```
HTTP client
  → POST /scheduler/force_check
      → routes/scheduler.py (COMP-013)
          → services/ctask_scheduler.force_check() (COMP-012)
              → ctask_tasks.run_ctask_assignment.delay() (COMP-010)
                  → task enqueued to Redis broker within ≤1s
          ← returns dispatch confirmation
      ← HTTP 200 with confirmation
```

#### DF-05: Handover Submission with Atomic Audit (REQ-015, REQ-016)

```
HTTP client (authenticated user)
  → POST /handover/submit (existing route, UNCHANGED path)
      → inline RBAC check (existing inline pattern)
          → on insufficient role: COMP-016 resolves specific error message ← HTTP 403 with role context
      → COMP-015 (Form Field Validator) validates all input fields
          → on validation failure: returns field-level error map ← HTTP 400 with field errors
      → COMP-014 (Audit Transaction Service)
          → opens database transaction
          → writes handover record
          → writes audit log entry
          → on both writes succeed: commits transaction ← HTTP 200 success
          → on either write fails: rolls back entire transaction ← HTTP 500 with specific error
```

#### DF-06: CI Security Gate (REQ-008)

```
Developer pushes to branch
  → GitLab CI pipeline triggered (.gitlab-ci.yml / COMP-017)
      → security stage (runs before merge is permitted):
          → job: dependency-scan
              → pip-audit scans requirements.txt
              → on CVE found: job fails, CVE ID + package reported; pipeline blocked
              → on clean: job passes
          → job: sast
              → Bandit scans Python source under src/
              → on HIGH severity finding: job fails
              → on clean or LOW/MEDIUM (configurable): job passes
          → job: secret-detection
              → GitLab Secret Detection template scans full git history
              → on secret found: job fails, commit reference reported
              → on clean: job passes
      → all three jobs must pass before merge to master is permitted
```

---

## API Contracts

> All scheduler endpoint paths, HTTP methods, and response content types are **unchanged** from the existing interface. Only the internal execution backing changes. Route handlers in COMP-013 translate between HTTP and COMP-012's service interface.

---

### ENDPOINT-001: Get Scheduler Status

| Field | Value |
|---|---|
| **HTTP Method** | `GET` |
| **Path** | `/scheduler/status` (existing, unchanged) |
| **Description** | Returns the current state of the Celery task queue workers and whether scheduled jobs are active. Must return within 5 seconds regardless of broker availability. |
| **Auth** | Session required; `team_admin` role minimum (existing RBAC check preserved). |

**Request:** No body. No query parameters.

**Success Response (200):**
```
{
  "status": "ok",                       // string enum: "ok" | "degraded"
  "workers_active": integer,            // count of live Celery workers; 0 if none
  "scheduled_jobs": [                   // array of job status objects
    {
      "name": string,                   // job identifier (e.g. "email_digest")
      "last_run": string | null,        // ISO-8601 datetime or null
      "next_run": string | null,        // ISO-8601 datetime or null
      "state": string                   // "active" | "idle" | "unknown"
    }
  ],
  "broker_reachable": boolean
}
```

**Degraded Response (200 — broker unavailable):**
```
{
  "status": "degraded",
  "workers_active": 0,
  "scheduled_jobs": [],
  "broker_reachable": false,
  "message": "Task queue broker unreachable; scheduler status unavailable"
}
```

**Error Responses:**

| Condition | HTTP Status | Body |
|---|---|---|
| Session invalid or absent | 401 | Existing session error (unchanged) |
| Insufficient role | 403 | `{"error": "team_admin access is required to view scheduler status"}` |
| Inspect call times out | 200 | Degraded response (not 500) — see above |

---

### ENDPOINT-002: Start Scheduler

| Field | Value |
|---|---|
| **HTTP Method** | `POST` |
| **Path** | `/scheduler/start` (existing, unchanged) |
| **Description** | Signals Celery Beat to begin processing its configured periodic schedule. |
| **Auth** | Session required; `account_admin` role minimum. |

**Request:** No body required.

**Success Response (200):**
```
{
  "status": "ok",
  "message": "Scheduler started"
}
```

**Error Responses:**

| Condition | HTTP Status | Body |
|---|---|---|
| Session invalid | 401 | Existing session error |
| Insufficient role | 403 | `{"error": "account_admin access is required to start the scheduler"}` |
| Broker unavailable | 503 | `{"error": "Scheduler unavailable: task queue broker is unreachable"}` |

---

### ENDPOINT-003: Stop Scheduler

| Field | Value |
|---|---|
| **HTTP Method** | `POST` |
| **Path** | `/scheduler/stop` (existing, unchanged) |
| **Description** | Signals Celery Beat to pause its periodic schedule. In-flight tasks are not cancelled. |
| **Auth** | Session required; `account_admin` role minimum. |

**Request:** No body required.

**Success Response (200):**
```
{
  "status": "ok",
  "message": "Scheduler stopped"
}
```

**Error Responses:** Same shape as ENDPOINT-002.

---

### ENDPOINT-004: Force Check (Immediate CTask Assignment Dispatch)

| Field | Value |
|---|---|
| **HTTP Method** | `POST` |
| **Path** | `/scheduler/force_check` (existing, unchanged) |
| **Description** | Immediately enqueues a single ctask assignment check job to the Celery task queue, bypassing the periodic schedule. Responds within 1 second. |
| **Auth** | Session required; `team_admin` role minimum. |

**Request:** No body required.

**Success Response (200):**
```
{
  "status": "ok",
  "message": "Assignment check dispatched",
  "task_id": string   // Celery task UUID for tracking
}
```

**Error Responses:**

| Condition | HTTP Status | Body |
|---|---|---|
| Session invalid | 401 | Existing session error |
| Insufficient role | 403 | `{"error": "team_admin access is required to force a scheduler check"}` |
| Broker unavailable | 503 | `{"error": "Force check failed: task queue broker is unreachable"}` |

---

### ENDPOINT-005: Handover Submission (Modified Behavior)

> **Path and method are unchanged.** Only the internal execution model changes to enforce atomic audit writes (REQ-015) and field-level validation (REQ-016).

| Field | Value |
|---|---|
| **HTTP Method** | `POST` |
| **Path** | `/handover/submit` (existing, unchanged) |
| **Description** | Submits a completed handover. Validates all fields, checks RBAC, then atomically writes the handover record and audit log entry. |
| **Auth** | Session required; `user` role minimum. |

**Request Body:** Existing form fields (unchanged). All fields are now explicitly validated by COMP-015 before processing.

**Success Response:** Existing success response (unchanged — rendered HTML redirect or JSON confirmation per existing content type).

**Error Responses:**

| Condition | HTTP Status | Body |
|---|---|---|
| Field validation failure | 400 | `{"errors": {"field_name": "actionable message", ...}}` |
| Insufficient role | 403 | `{"error": "user access is required to submit a handover; approval requires team_admin"}` |
| Audit log write failure (triggers rollback) | 500 | `{"error": "Handover submission failed: audit record could not be written. No data was saved. Please retry."}` |
| Database connectivity failure | 500 | `{"error": "Handover submission failed: database unavailable. Please retry."}` |

---

## Data Models

### New Table: `failed_tasks`

Stores records of Celery tasks that have exhausted all retry attempts, enabling operator inspection and recovery. Written exclusively by COMP-011.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY, AUTO INCREMENT | Surrogate key |
| `celery_task_id` | VARCHAR(255) | NOT NULL, UNIQUE | Celery-assigned task UUID |
| `task_name` | VARCHAR(255) | NOT NULL | Fully qualified task function name (e.g., `tasks.email_tasks.send_digest`) |
| `task_args` | JSON | NOT NULL | Positional arguments passed to the task at dispatch |
| `task_kwargs` | JSON | NOT NULL | Keyword arguments passed to the task at dispatch |
| `error_message` | TEXT | NOT NULL | Exception message from the final failure |
| `error_trace` | TEXT | NOT NULL | Full traceback from the final failure |
| `failure_count` | INTEGER | NOT NULL, DEFAULT 3 | Number of attempts made before DLQ routing |
| `failed_at` | DATETIME | NOT NULL | Timestamp of the final failure (UTC) |
| `alerted_at` | DATETIME | NULLABLE | Timestamp when the operations alert was dispatched |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'failed' | Enum: `failed` \| `alerted` \| `resolved` |
| `resolved_at` | DATETIME | NULLABLE | Timestamp when an operator marked the task resolved |
| `resolved_by` | VARCHAR(255) | NULLABLE | User identifier of the resolving operator |

**Relationships:** No foreign keys. Standalone audit table.

**Indexes:** `idx_failed_tasks_status` on `(status)` for operator queue views; `idx_failed_tasks_task_name` on `(task_name)` for per-job DLQ queries.

**Migration Notes:** This is a new table requiring a new Alembic migration. The migration file must be created via `flask db migrate -m "add_failed_tasks_table"` and registered in `migrations/README.md` (COMP-020) before merging.

---

### Existing Table: `audit_log` (Behavioral Contract Change — No Schema Change)

No schema modification. The behavioral contract changes: all writes to `audit_log` that accompany a handover submission are now executed within the same SQLAlchemy transaction as the handover record write (enforced by COMP-014). If the audit log write raises any exception, the transaction is rolled back and neither record is persisted. The table structure, column definitions, and existing indexes are preserved exactly.

---

### Celery Result Backend State (Redis — No Application DB Table)

Celery task results (for non-exhausted tasks) are stored in Redis using Celery's built-in result backend. This is not managed by the application's Alembic migrations. Key schema elements:

- **Key pattern:** `celery-task-meta-{task_uuid}` (Redis string)
- **Value:** JSON object with fields: `task_id`, `status` (`PENDING` \| `STARTED` \| `SUCCESS` \| `FAILURE` \| `RETRY`), `result`, `traceback`, `date_done`
- **TTL:** Configurable via `CELERY_RESULT_EXPIRES` (recommended: 86400 seconds / 24 hours)

Application code must not read from the Celery result backend directly. COMP-012's `get_status()` uses `celery.control.inspect()`, not result backend reads.

---

## Decisions (ADRs)

### ADR-001: Overall Architecture Pattern — Monolith + Discrete Async Execution Tier

**Context:** ShiftOps is a Flask monolith. Background jobs currently execute within the HTTP-serving process via APScheduler. With multi-worker deployment, each worker spawns its own APScheduler instance, causing every job to execute once per worker per interval. The system needs a reliable scheduling mechanism that works correctly regardless of HTTP worker count.

**Decision:** Retain the Flask monolith as the HTTP-serving layer. Establish Celery (backed by Redis) as the exclusive execution tier for all background jobs. Celery Beat runs as a separate, single process and enqueues tasks; Celery workers dequeue and execute them. The HTTP workers have no scheduler. This eliminates duplicate execution at the architectural level: only one Beat process exists, so each job is enqueued exactly once per interval regardless of HTTP worker count.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|---|---|---|
| **A1: Keep APScheduler, configure master-process election** | No new infrastructure dependency; avoids Celery rollout | Fragile — leader election in APScheduler requires external lock (Redis anyway); adds complexity without eliminating the dependency; does not satisfy REQ-003 (jobs still in HTTP process) |
| **A2: Full microservice decomposition** | Clean separation of concerns; independent scaling per service | Requires extensive refactoring of all ~45–50 Blueprints; weeks of work; explicitly out of scope; introduces network latency and distributed transaction complexity |
| **A3: Do nothing — disable APScheduler in workers via `--preload` flag** | Zero code change | Requires Gunicorn `--preload` which only works with fork-based workers; fragile; does not work in all deployment configurations; does not satisfy REQ-003 |
| **A4 (Chosen): Flask monolith + Celery execution tier** | Celery Beat single-process design guarantees deduplication; minimal refactoring of HTTP tier; established Python pattern; clear operational model | Adds Redis as a required infrastructure dependency; Celery Beat is a new process to operate; worker health monitoring required |

**Consequences:**
- ✅ Duplicate job execution impossible by design (REQ-005)
- ✅ HTTP tier fully isolated from task queue availability for non-critical operations (REQ-013)
- ✅ Retry and DLQ mechanics are Celery-native, not custom-built (REQ-006)
- ⚠️ Redis and Celery worker availability become operational dependencies; addressed by assumption A-002/A-003 and monitoring open items

---

### ADR-002: Message Broker and Result Backend — Redis

**Context:** Celery requires a message broker for task transport and (optionally) a result backend for task state storage. The choice of broker affects operational complexity, HA requirements, and existing infrastructure.

**Decision:** Redis serves as both the message broker and the result backend. The broker URL and result backend URL are sourced exclusively from environment variables (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`); they do not appear in source code or version-controlled configuration files.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|---|---|---|
| **A1: RabbitMQ as broker, Redis as backend** | RabbitMQ has stronger message durability guarantees; native dead-letter exchange support | Adds a second infrastructure component; higher operational complexity; no existing deployment; Celery supports Redis broker fully for this workload |
| **A2: Redis for broker + SQLAlchemy for result backend** | Result state visible in application DB without extra tooling | Adds DB load for every task state update; slower; not recommended for high-throughput Celery usage |
| **A3 (Chosen): Redis for both broker and result backend** | Single infrastructure component; already referenced in project configuration; fast; widely supported by Celery; simpler operational model | Redis is a single point of failure if not replicated; result TTL must be managed to prevent memory growth |

**Consequences:**
- ✅ Single broker service to deploy and monitor
- ✅ Broker URL never appears in source code (security constraint satisfied)
- ⚠️ Redis HA (replication/sentinel) is required for production reliability; deployment manifests must specify this

---

### ADR-003: WSGI Server — Gunicorn

**Context:** Flask's built-in development server is not suitable for production. A production-grade WSGI server is required. The application is synchronous and CPU-light (background work is delegated to Celery).

**Decision:** Gunicorn is the WSGI server. Initial configuration: 1 worker, bound to `0.0.0.0:5000`, with server parameters declared in `gunicorn.conf.py`. The worker count is explicitly set to 1 at initial deployment; scaling policy is deferred (non-goal).

**Alternatives Considered:**

| Alternative | Pros | Cons |
|---|---|---|
| **A1: uWSGI** | Feature-rich; native process management; supports Emperor mode for multi-app | Complex configuration syntax; heavier operational footprint; unnecessary for a single synchronous Flask app |
| **A2: Uvicorn / ASGI** | Async-native; high throughput for I/O-bound workloads | Requires rewriting Flask app in async style (or wrapping); substantial code change; out of scope |
| **A3 (Chosen): Gunicorn** | Official Flask/Django recommendation; simple configuration; well-documented; supports pre-fork multi-worker if scaling is needed later | Not async-native (not needed for this workload); requires explicit worker count decision |

**Consequences:**
- ✅ Production-safe server process with proper signal handling (REQ-002)
- ✅ Configuration in `gunicorn.conf.py` is version-controlled and auditable
- ✅ Worker count scaling possible without code changes (add `-w N` to config file)

---

### ADR-004: APScheduler Removal Strategy — Complete Removal

**Context:** APScheduler is embedded in the Flask process. The system needs all scheduled job execution removed from the HTTP tier. Two approaches exist: complete removal or hybrid disabling.

**Decision:** APScheduler is removed entirely from the application. All four job types are re-implemented as Celery tasks. The Celery Beat schedule in `celeryconfig.py` replaces all APScheduler job registrations. No APScheduler import shall remain in any module (verified by static code search, per AC-003c).

**Alternatives Considered:**

| Alternative | Pros | Cons |
|---|---|---|
| **A1: Keep APScheduler for local dev, Celery Beat for production** | Simpler local development without Redis | Two scheduler code paths to maintain; risk of production-like bugs not caught in dev; violates REQ-003 (no execution in HTTP process) |
| **A2: Keep APScheduler but configure it to run only in Gunicorn master process** | Avoids Celery Beat setup | Fragile; depends on Gunicorn worker model internals; breaks with `--preload` changes; still violates REQ-003 |
| **A3 (Chosen): Complete removal** | Clean; verifiable via static search (AC-003c); single execution model in all environments | Requires local development to run Redis + Celery worker; addressed by docker-compose dev configuration |

**Consequences:**
- ✅ Zero risk of in-process scheduled execution in any environment (REQ-003)
- ✅ Statically verifiable: `grep -r "APScheduler\|apscheduler" .` must return zero matches
- ⚠️ Local development requires Redis and a Celery worker; `docker-compose.yml` must include both in the dev profile

---

### ADR-005: Dead-Letter Queue Storage — Hybrid (Celery Mechanics + Application DB Record)

**Context:** REQ-006 requires exhausted tasks to be "moved to a dead-letter queue" and trigger an operations alert. The mechanism must make failed tasks recoverable by an operator.

**Decision:** Celery handles retry mechanics natively (max_retries=3, countdown=30). When a task exhausts retries, Celery invokes the task's `on_failure` callback, which calls COMP-011 (DLQ handler). COMP-011 writes a record to the application database `failed_tasks` table (full context: task name, args, error trace, timestamps) and dispatches an operations alert. The application DB table is the operator-visible DLQ; it is separate from Celery's internal result backend.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|---|---|---|
| **A1: Celery result backend only (Redis)** | Zero additional schema; uses Celery's built-in failure state | Operator must use Celery monitoring tooling (Flower) to inspect; results expire per TTL; no structured alerting hook |
| **A2: Dedicated Celery "dead_letter" queue** | Native Celery mechanism; no custom code | Queue contents expire with Redis; no structured record for compliance/audit; alerting requires separate Celery signal wiring anyway |
| **A3 (Chosen): Hybrid (Celery retries + DB DLQ record on exhaustion)** | Operator-visible in existing application DB; structured record with full context; natural alerting hook; recoverable without Celery tooling | Requires one new DB table + migration; COMP-011 is a new component |

**Consequences:**
- ✅ Operators can inspect and resolve failed tasks via existing DB tooling (REQ-006)
- ✅ Full context (args, trace, timestamps) preserved for forensic analysis (EC-003)
- ⚠️ `failed_tasks` table adds a new migration; must be registered in COMP-020

---

### ADR-006: Startup Health Check Integration — Pre-Start Script

**Context:** REQ-014 requires the application to abort startup and emit a descriptive error if secrets are absent/undecryptable or the database is unreachable. The check must execute before any HTTP port is bound.

**Decision:** A dedicated `startup_checks.py` module (COMP-004) is invoked by `start.sh` (COMP-001) before Gunicorn is launched. If `startup_checks.py` exits with a non-zero code, `start.sh` propagates the non-zero exit and does not invoke Gunicorn. This executes once per container start, not per Gunicorn worker.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|---|---|---|
| **A1: Inline in Flask `app.py` factory** | No new file; runs at app import time | Runs once per Gunicorn worker fork; harder to distinguish startup failure from runtime error; port may be partially bound before all workers fail |
| **A2: Kubernetes liveness/readiness probe** | Standard cloud-native pattern | Out of scope for this iteration; does not address the "abort before port binding" requirement; requires K8s environment |
| **A3 (Chosen): Dedicated pre-start script** | Runs exactly once before port binding; clean separation; non-zero exit prevents Gunicorn start; easily testable in isolation | One extra file to maintain; Gunicorn must not be launched until `startup_checks.py` exits 0 |

**Consequences:**
- ✅ Container exits with non-zero code and descriptive message within 10 seconds on any startup failure (REQ-014, AC-014a/b)
- ✅ No partially initialised server state
- ⚠️ `startup_checks.py` must import the application's secrets manager and DB layer without starting the full Flask app; import isolation must be verified

---

### ADR-007: CI Security Tooling Selection

**Context:** REQ-008 requires three security checks in CI: dependency CVE scan, Python SAST, and committed-secret detection. The tools must integrate with GitLab CI/CD.

**Decision:** 
- **Dependency CVE scan:** `pip-audit` — scans `requirements.txt` against PyPI Advisory Database and OSV. Pipeline-blocking on any CVE finding.
- **Python SAST:** `Bandit` — scans Python source code for common security issues. Configurable severity threshold (HIGH-level findings are blocking).
- **Secret detection:** GitLab's native `Secret Detection.gitlab-ci.yml` template — scans full git history for committed secrets using GitLab's built-in ruleset. Pipeline-blocking on any finding.

All three tools are version-pinned in `.gitlab-ci.yml` to prevent unexpected behaviour on tool updates.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|---|---|---|
| **A1: Safety + Semgrep + git-secrets** | Semgrep has broader language support; Safety is widely used | Safety requires paid tier for full CVE database; Semgrep rules require configuration for Python; `git-secrets` requires separate installation |
| **A2: Snyk** | Comprehensive; developer-friendly dashboard; PR comments | Commercial licensing cost; external data transmission of dependency list; over-engineered for this scope |
| **A3 (Chosen): pip-audit + Bandit + GitLab template** | All open-source or GitLab-native; zero licensing cost; pip-audit covers PyPI Advisory Database; GitLab template is maintained by GitLab; Bandit is the Python SAST standard | pip-audit requires network access to advisory DB during CI run; Bandit produces false positives that require suppression configuration |

**Consequences:**
- ✅ Zero additional licensing cost
- ✅ GitLab secret detection template is maintained and updated by GitLab (REQ-008)
- ⚠️ Bandit false-positive suppression (`# nosec` annotations) must be governed by code review to prevent abuse; reviewer checklist must include validation of any `# nosec` addition

---

## Implementation Guidelines

### File Structure

All files to be created or modified, with purpose and owning component:

| File | Action | Component | Purpose |
|---|---|---|---|
| `start.sh` | Create | COMP-001 | Container entrypoint; calls startup checks then launches Gunicorn |
| `gunicorn.conf.py` | Create | COMP-002 | Gunicorn server parameters (workers=1, bind, timeout, log format) |
| `docker-compose.yml` | Modify | COMP-003 | Update `web` CMD; add `worker`, `beat`, `redis` services |
| `startup_checks.py` | Create | COMP-004 | Validates secrets decryptability and DB reachability before port binding |
| `celery_app.py` | Create | COMP-005 | Celery application instance factory; reads broker/backend from env vars |
| `celeryconfig.py` | Create | COMP-006 | Celery Beat schedule; maps job names to task references and intervals |
| `tasks/__init__.py` | Create | — | Package init; enables Celery autodiscovery |
| `tasks/email_tasks.py` | Create | COMP-007 | Email digest Celery task; retry policy; DLQ routing |
| `tasks/servicenow_tasks.py` | Create | COMP-008 | ServiceNow polling Celery task; retry policy; DLQ routing |
| `tasks/retry_tasks.py` | Create | COMP-009 | Task retry sweep Celery task; retry policy; DLQ routing |
| `tasks/ctask_tasks.py` | Create | COMP-010 | CTask assignment check Celery task; retry policy; DLQ routing |
| `tasks/dlq_handler.py` | Create | COMP-011 | DLQ record write + operations alert dispatch |
| `services/ctask_scheduler.py` | Modify | COMP-012 | Replace APScheduler backing with Celery inspect + task dispatch |
| `routes/scheduler.py` | Modify | COMP-013 | Preserve routes; update to call modified service; preserve response shapes |
| `services/audit_service.py` | Create | COMP-014 | Atomic handover + audit log transaction manager |
| `utils/validators.py` | Create | COMP-015 | Field-level form validation utility; returns structured error map |
| `utils/rbac_errors.py` | Create | COMP-016 | Permission-specific error message generator |
| `.gitlab-ci.yml` | Modify | COMP-017 | Add `security` stage with three jobs |
| `.gitignore` | Modify | COMP-018 | Add binary document extension patterns |
| `tests/config.py` | Modify | COMP-019 | Replace hardcoded credentials with env var reads + sentinel fallbacks |
| `migrations/README.md` | Create | COMP-020 | Migration catalogue with status and execution order |
| `migrations/versions/XXXXXX_add_failed_tasks.py` | Create | — | Alembic migration for `failed_tasks` table; registered in COMP-020 |

### Naming Conventions

- **Task functions:** Snake-case verb-noun format — `send_email_digest`, `poll_servicenow`, `check_ctask_assignments`. Matches existing route handler naming style.
- **Service methods:** Snake-case — `get_status()`, `force_check()` (preserve existing names exactly for backward compatibility).
- **Validator functions:** Named `validate_{form_name}_fields(data: dict) -> dict` — e.g., `validate_handover_fields`.
- **RBAC error resolver:** Named `resolve_rbac_error(user_role: str, required_role: str, action: str) -> str`.
- **Component IDs:** Prefix `COMP-` followed by three-digit zero-padded integer, as defined in this document.
- **Environment variables:** `SCREAMING_SNAKE_CASE` — `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `TEST_SUPERADMIN_PASSWORD`, `TEST_ADMIN_PASSWORD`, `TEST_USER_PASSWORD`.

### Patterns to Use

- **Celery `bind=True` tasks:** All four task functions must use `self` reference for retry calls (`self.retry(exc=..., countdown=30)`). This is the standard Celery retry pattern.
- **SQLAlchemy session as context manager:** COMP-014 must use `db.session` as an explicit transaction context. The session must not be auto-committed; commit must be the final operation, and exceptions must trigger explicit rollback before re-raising.
- **Result-typed service returns:** COMP-012 service methods must return a structured dict (not raise exceptions) for non-fatal broker failures, to support the degraded-state response contract of ENDPOINT-001.
- **Blueprint `errorhandler` for 400/403:** COMP-013 and all routes that call COMP-015/016 must register local `errorhandler` decorators for `400` and `403` to ensure the structured error format is returned consistently.
- **Gunicorn `--config` flag:** `start.sh` must pass `--config gunicorn.conf.py` to Gunicorn, not inline all parameters on the command line. This keeps configuration version-controlled and auditable.

### Patterns to Avoid

- **`APScheduler` imports anywhere in the codebase** — must be completely removed. The static verification `grep -r "apscheduler" .` must return zero matches before merge.
- **Credentials in source code** — broker URL, result backend URL, and all test credentials must never appear as literals. Use environment variables exclusively.
- **Blocking I/O in `get_status()`** — the `celery.control.inspect()` call must always specify an explicit `timeout` parameter (≤ 2.0 seconds). Never use the default (which blocks indefinitely).
- **Shared SQLAlchemy session across tasks** — Celery tasks must obtain their own database session within the task function body. Sessions must not be shared between the HTTP tier and task workers.
- **Silent exception swallowing in audit operations** — COMP-014 must never catch exceptions without re-raising them after rollback. Catching and logging without re-raising would produce the silent partial-commit failure that REQ-015 prohibits.
- **`# nosec` annotations added without reviewer justification** — any Bandit suppression must be accompanied by a code comment explaining why the finding is a false positive, and must be explicitly validated in code review.

### New Dependencies

| Package | Version Pin | Purpose | ADR |
|---|---|---|---|
| `gunicorn` | Pinned (e.g., `==21.x.x`) | Production WSGI server (REQ-002) | ADR-003 |
| `celery[redis]` | Pinned (e.g., `==5.x.x`) | Distributed task queue with Redis transport (REQ-003) | ADR-001, ADR-002 |
| `redis` | Pinned | Redis Python client (broker + result backend) | ADR-002 |
| `pip-audit` | CI-only, pinned | Dependency CVE scanning (REQ-008) | ADR-007 |
| `bandit` | CI-only, pinned | Python SAST (REQ-008) | ADR-007 |

> All new runtime dependencies must be added to `requirements.txt`. CI-only tools (`pip-audit`, `bandit`) must be added to a separate `requirements-ci.txt` to avoid polluting the production dependency set.

---

## Testing Strategy

### Unit Tests

Each of the following units requires isolated unit tests with all external dependencies mocked:

| Unit | Test Scope | Key Scenarios |
|---|---|---|
| `startup_checks.py` (COMP-004) | Validation logic | Missing secret exits non-zero; decryption failure exits non-zero; DB unreachable exits non-zero; all checks pass exits zero; error message identifies failing check by name |
| `celery_app.py` (COMP-005) | Configuration loading | Broker URL read from env var; raises on missing env var; Flask app context applied correctly |
| Each task in `tasks/` (COMP-007–010) | Task function logic | Success path; transient failure triggers retry with 30s countdown; retry count increments correctly; `max_retries` exhaustion calls COMP-011 |
| `tasks/dlq_handler.py` (COMP-011) | DLQ write + alert | DB write contains all required fields; alert dispatch called once; DB failure does not suppress alert |
| `services/ctask_scheduler.py` (COMP-012) | All four operations | `get_status()` with broker available returns structured dict; `get_status()` with broker unavailable returns degraded dict within 5s; `force_check()` enqueues task within 1s; `start()`/`stop()` send correct Celery commands |
| `utils/validators.py` (COMP-015) | Validation rules | Empty field returns named error; null value returns named error; out-of-range value returns range error; valid inputs return empty error map |
| `utils/rbac_errors.py` (COMP-016) | Error message format | `user` attempting `team_admin` action returns message identifying `team_admin`; every supported role/action combination produces a non-generic message |
| `services/audit_service.py` (COMP-014) | Transaction atomicity | Both writes succeed → commit called; audit log write fails → rollback called, handover record not persisted; error re-raised after rollback |
| `tests/config.py` (COMP-019) | Credential sourcing | Env vars set → credentials match env var values; env vars unset, localhost target → sentinel values used; env vars unset, non-localhost target → raises ConfigurationError |

### Integration Tests

| Interaction | Test Scope |
|---|---|
| Celery task execution with live Redis | Task dispatched via `.delay()` executes in worker; result accessible via result backend; retry mechanics fire on injected failure |
| `get_status()` with live Celery workers | Returns active worker count and job state; returns degraded state when Redis stopped |
| `force_check()` end-to-end | Task appears in Celery worker queue within 1 second of dispatch |
| Handover submission transaction | Full DB integration: both records written on success; neither record written on injected audit log failure |
| CI security stage (`.gitlab-ci.yml`) | Pipeline passes with clean dependencies; pipeline fails with a known-CVE dependency injected into `requirements.txt` |

### E2E Scenarios

| Scenario | Steps | Expected Outcome |
|---|---|---|
| **Container startup — healthy** | Start container with all required env vars set and DB available | Container starts; port 5000 bound; Gunicorn reports 1 worker; logs show startup health check passed |
| **Container startup — missing secret** | Start container with a required secret env var unset | Container exits within 10s; exit code non-zero; log identifies missing secret by name; no port bound |
| **Multi-worker deduplication** | Start 2 gunicorn workers + Celery Beat; observe job execution logs for 2 trigger intervals | Exactly 1 execution record per interval per job type; no duplicates |
| **Form submission with invalid fields** | Submit handover form with 2 empty required fields | HTTP 400; response body contains field-specific errors for both fields by name; no 500 error |
| **Insufficient permissions** | `user`-role account attempts handover approval | HTTP 403; response body identifies `team_admin` as required role; message is not generic |
| **DLQ routing** | Inject a ServiceNow polling task that fails on all 3 retries | Task appears in `failed_tasks` table with all context fields populated; operations alert dispatched |

### Coverage Approach

- **P0 requirements (REQ-001–009, REQ-015):** Target ≥ 80% line coverage for new modules. All happy-path and defined error-path acceptance criteria must have corresponding test cases.
- **P1 requirements (REQ-010–014, REQ-016–017):** Target ≥ 70% line coverage. At minimum one positive and one negative test case per acceptance criterion.
- **Modified existing files (`services/ctask_scheduler.py`, `routes/scheduler.py`):** Existing tests must continue to pass without modification; no regression on existing scheduler behaviour.
- **CI enforcement:** Coverage thresholds are not enforced as pipeline gates in this iteration; coverage reports are generated and published as pipeline artefacts for baseline measurement.

---

## Security Considerations

| # | Concern | Mitigation | OWASP Category |
|---|---|---|---|
| **SEC-001** | Broker credentials (Redis URL with auth token) exposed in source or version-controlled config | `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` sourced exclusively from environment variables. These vars must not appear in `.env` files tracked by git. `.gitignore` must exclude `.env`. | A02: Cryptographic Failures / A05: Security Misconfiguration |
| **SEC-002** | Test credentials (superadmin, admin, user passwords) valid in non-localhost environments if hardcoded | `tests/config.py` (COMP-019) reads from env vars; fallback sentinel values are non-guessable, localhost-only strings. A guard aborts test execution if sentinel values are used against a non-localhost target. | A05: Security Misconfiguration |
| **SEC-003** | Committed secrets in git history | GitLab Secret Detection template in COMP-017 scans full git history on every pipeline run; any detected secret blocks merge. Historical secrets must be revoked before this gate is activated. | A02: Cryptographic Failures |
| **SEC-004** | Known CVEs in declared Python dependencies | `pip-audit` (COMP-017) scans `requirements.txt` on every CI run; pipeline fails on any CVE finding, blocking merge. | A06: Vulnerable and Outdated Components |
| **SEC-005** | Python source code contains common security anti-patterns (SQL injection, subprocess injection, hardcoded keys) | Bandit SAST (COMP-017) scans all Python source; HIGH-severity findings are blocking. Any `# nosec` suppression requires code reviewer explicit approval and inline justification comment. | A03: Injection / A02: Cryptographic Failures |
| **SEC-006** | Binary document files (PDF, DOCX, etc.) tracked in git may contain PII or sensitive operational data | COMP-018 adds extension patterns to `.gitignore`; existing tracked binary files must be removed from all reachable commits via `git filter-repo` before the cleanup commit is merged. | A05: Security Misconfiguration (PII handling) |
| **SEC-007** | Session token validation bypassed during scheduler refactoring | `validate_session()` middleware runs on every request (existing control). COMP-012 and COMP-013 do not touch the session or authentication middleware. The refactoring is internal-only; no auth code path is modified. | A07: Identification and Authentication Failures |
| **SEC-008** | RBAC enforcement weakened during scheduler route modifications | COMP-013 modifies only the internal call to COMP-012; all inline RBAC checks in `routes/scheduler.py` are preserved verbatim. A code review checklist item must explicitly confirm no RBAC check was removed. | A01: Broken Access Control |
| **SEC-009** | Celery task arguments may contain user-supplied data that is persisted to `failed_tasks` table | COMP-011 must sanitise or truncate task argument values before writing to `failed_tasks.task_args` (JSON column). Maximum field length constraints on `task_args` and `task_kwargs` prevent storage-based DoS. Input to Celery tasks must be validated upstream (COMP-015) before dispatch. | A03: Injection |
| **SEC-010** | Operations alert dispatch (from COMP-011) may leak task internals to untrusted channels | Alert payloads must contain only: task name, timestamp, failure count, and a reference ID (the `failed_tasks.id`). Full error traces and task arguments must not appear in alert payloads; they are accessible only via authenticated DB query. | A02: Cryptographic Failures / PII Handling |

---

## Error Handling Strategy

### Error Propagation Chain

```
External input (form submission)
  → COMP-015 (validation) → ValidationError (field map) → HTTP 400 (field-level errors)
  → COMP-016 (RBAC check) → PermissionError (role context) → HTTP 403 (specific message)
  → COMP-014 (audit transaction) → DatabaseError → rollback → HTTP 500 (retry message)
  → Application code → UnhandledException → Flask errorhandler → HTTP 500 (generic safe message)

Background task
  → Celery task execution → TransientError → retry (max 3, interval 30s)
  → Final failure → COMP-011 (DLQ handler) → DB write + alert
  → COMP-011 DB write failure → alert still dispatched; error logged to structured log
```

### User-Facing Error Messages vs. Internal Logging

| Error Class | User-Facing Message | Internal Log |
|---|---|---|
| Field validation failure | Specific field name + actionable correction (e.g., "Shift end time is required") | DEBUG: field name, received value |
| RBAC denial | Specific required role/privilege (e.g., "team_admin access is required to approve handovers") | INFO: user_id, attempted action, user role, required role |
| Audit transaction failure | "Submission failed: no data was saved. Please retry or contact support." (no technical detail) | ERROR: exception type, stack trace, user_id, handover context |
| Startup check failure | Human-readable description identifying the failing check and the configuration key (e.g., "SECRET_KEY_FOO is absent from the secrets store") | CRITICAL: full exception; written to stderr |
| DLQ exhaustion | Not user-facing (async operation) | ERROR: task_name, celery_task_id, failure_count, full traceback |
| Scheduler broker unavailable | Degraded-state indicator in `get_status()` response; explicit `broker_reachable: false` field | WARNING: inspect timeout duration, broker URL (redacted auth) |

**Rule:** No stack trace, database error message, or internal component name appears in any user-facing response. Internal errors are logged with structured fields (user_id, request_id, timestamp) at the appropriate severity level using the application's existing logging configuration.

### Retry Strategy for Transient Failures

- **Celery tasks (COMP-007–010):** `max_retries=3`, `countdown=30` (seconds). Applies to all transient errors from external services (ServiceNow timeout, SMTP connection error, DB transient error). Non-transient errors (e.g., `ValueError` from bad task arguments) must NOT trigger retries; the task must raise immediately to avoid wasting retry budget.
- **Startup health checks (COMP-004):** No retry. A single failure is deterministic and fatal at container startup. The container must exit and be restarted by the orchestrator (which has its own restart policy).
- **Scheduler `get_status()` (COMP-012):** No retry. The inspect call uses a 2.0-second timeout and returns the degraded state immediately on timeout. The web tier must not be blocked waiting for a retry.
- **Handover submission (COMP-014):** No retry at the service layer. The route handler returns an error to the user, who retries via a new form submission. Automatic retry of a failed DB transaction risks duplicate writes if the first transaction's commit status is uncertain.

### Graceful Degradation When Dependencies Are Unavailable

| Dependency | Unavailable Scenario | Degradation Behaviour |
|---|---|---|
| **Redis (task queue broker)** | Broker unreachable during HTTP request | `get_status()` returns degraded indicator; `force_check()` and `start()`/`stop()` return HTTP 503 with specific message. HTTP request processing continues unaffected. |
| **Redis (during task execution)** | Broker recovers; in-flight tasks continue to completion; new enqueue operations resume normally | No action required from HTTP tier. COMP-011 records the failure if a task could not re-enqueue for retry. |
| **Primary database (during startup)** | DB unreachable | COMP-004 exits non-zero; container does not start; no port bound (REQ-014). |
| **Primary database (at runtime)** | DB connection lost mid-request | SQLAlchemy raises `OperationalError`; Flask errorhandler returns HTTP 500 with a safe user message; structured error logged. COMP-014 rolls back the transaction. |
| **ServiceNow (external API)** | Timeout or 5xx error | Celery retry (up to 3 attempts, 30-second intervals). After exhaustion, task enters DLQ via COMP-011; operations alerted. |
| **Operations alert channel** | Alert dispatch fails | Failure is logged at ERROR level. The `failed_tasks` DB record is still written. Alert failure must not prevent DLQ record persistence. |


---
## Implementation Plan (Phase 2)

## Summary

The ShiftOps Archaeology Gap Remediation (CTCOAMSHM-6) closes 8 medium-severity gaps across the shifthandover_v3 codebase by replacing the Flask development server with a Gunicorn startup script, migrating all background job execution from in-process APScheduler to a Celery + Redis execution tier, adding a three-gate CI security stage, cleanses binary artefacts from version control history, and establishing migration cataloguing, credential hygiene, and branch protection enforcement. The overall approach preserves all ~45–50 existing Blueprint route contracts, session mechanics, and inline RBAC patterns while introducing 16 new files and modifying 7 existing ones across startup, scheduling, audit, and pipeline layers.

---

## Key Requirements & Constraints

| ID | Priority | Description |
|---|---|---|
| REQ-001 | P0 | Application startup shall be defined in a dedicated, version-controlled startup script; container orchestration shall invoke that script rather than the application module directly. |
| REQ-002 | P0 | Application shall be served by a production-grade WSGI-compliant server (Gunicorn); default initial worker count shall be 1. |
| REQ-003 | P0 | All scheduled background job execution (email digest, ServiceNow polling, task retry, ctask assignment) shall be delegated exclusively to Celery; no scheduled job shall execute within the HTTP-serving process. |
| REQ-004 | P0 | The scheduler management interface (start, stop, get_status, force_check) shall be backed exclusively by Celery; status queries shall use `celery.control.inspect`. |
| REQ-005 | P0 | With two or more HTTP worker processes active, each scheduled background job shall execute exactly once per trigger interval — duplicate execution is not permitted. |
| REQ-006 | P0 | Failing background tasks shall be retried up to 3 times with ≥30-second intervals; tasks exhausting all retries shall be moved to a dead-letter queue and trigger an operations alert. |
| REQ-007 | P0 | All test credentials in `tests/config.py` shall be sourced from named environment variables; no valid non-localhost credential shall appear as a literal in source. |
| REQ-008 | P0 | CI/CD pipeline shall include a security stage executing: (a) dependency CVE scan via pip-audit, (b) Python SAST via Bandit, and (c) committed-secret detection via GitLab template; CVE findings shall block merge. |
| REQ-009 | P0 | `.gitignore` shall exclude `*.pdf`, `*.doc`, `*.docx`, `*.xlsx`, `*.pptx`; no such files shall remain reachable from the primary integration branch. |
| REQ-010 | P1 | Every database migration artefact shall be catalogued in `migrations/README.md` with identifier, application status, and execution order. |
| REQ-011 | P1 | All future schema changes shall be introduced exclusively through `flask db migrate`; each change requires a registered migration artefact per REQ-010. |
| REQ-012 | P1 | GitLab branch protection shall enforce a minimum of 1 approved peer review before any merge to master/main is permitted. |
| REQ-013 | P1 | `get_status()` shall complete within 5 seconds and must not block in-flight HTTP request threads when the task queue broker is unavailable. |
| REQ-014 | P1 | Application shall abort startup and emit a descriptive, human-readable error if required secrets are absent/undecryptable or the primary database is unreachable; no port shall be bound under these conditions. |
| REQ-015 | P0 | Handover submissions and audit-log writes shall execute atomically; neither record shall be persisted without the other, and failures shall surface a clear, specific error to the caller. |
| REQ-016 | P1 | All form submissions shall return specific, field-level, actionable error messages for each invalid field; no silent failures or unhandled 500 errors are permitted. |
| REQ-017 | P1 | Authorisation failures shall return a message identifying the specific missing privilege or role required for the attempted operation; generic 403 responses are not acceptable. |
| REQ-018 | P2 | All end-user and administrator documentation shall be maintained in Confluence as the single authoritative source; repository binary document artefacts shall not serve as documentation. |

---

## Architecture Summary

**Overall Pattern — Layered Monolith with Discrete Async Execution Tier (ADR-001):** The Flask monolith is retained as the HTTP-serving layer with no Blueprint decomposition. Celery + Redis is formalised as the exclusive execution tier for all background jobs. The two tiers communicate only through the Redis message broker and share no in-process scheduler state. Celery Beat runs as a single dedicated process, enqueuing each job exactly once per interval regardless of HTTP worker count — eliminating duplicate execution at the architectural level.

| ADR | Decision | Rationale |
|---|---|---|
| ADR-001 | Flask monolith + Celery execution tier | Celery Beat single-process design provides native deduplication; no Blueprint restructuring required |
| ADR-002 | Redis as both broker and result backend | Single infrastructure component already referenced in project config; broker credentials sourced from env vars only |
| ADR-003 | Gunicorn with version-controlled `gunicorn.conf.py` | Official Flask WSGI recommendation; auditable config; supports future worker count scaling with no code changes |
| ADR-004 | Complete APScheduler removal | Eliminates any residual in-process scheduling; statically verifiable via `grep -r "apscheduler" .` returning zero matches |
| ADR-005 | Hybrid DLQ: Celery retry mechanics + application `failed_tasks` DB table | Operator-visible records for forensic review without Celery tooling; natural alerting hook on exhaustion |
| ADR-006 | Dedicated pre-start script (`startup_checks.py`) invoked by `start.sh` | Runs exactly once before any port is bound; non-zero exit prevents Gunicorn launch; independently testable |
| ADR-007 | pip-audit + Bandit + GitLab Secret Detection template | Zero licensing cost; GitLab-native secret scanning; pip-audit covers PyPI Advisory Database |

**Component Structure (20 components across 5 layers):**

- **Startup tier:** COMP-001 `start.sh`, COMP-002 `gunicorn.conf.py`, COMP-003 `docker-compose.yml`, COMP-004 `startup_checks.py`
- **Celery execution tier:** COMP-005 `celery_app.py`, COMP-006 `celeryconfig.py`, COMP-007 `tasks/email_tasks.py`, COMP-008 `tasks/servicenow_tasks.py`, COMP-009 `tasks/retry_tasks.py`, COMP-010 `tasks/ctask_tasks.py`, COMP-011 `tasks/dlq_handler.py`
- **Scheduler management (modified):** COMP-012 `services/ctask_scheduler.py`, COMP-013 `routes/scheduler.py`
- **Application utilities (new):** COMP-014 `services/audit_service.py`, COMP-015 `utils/validators.py`, COMP-016 `utils/rbac_errors.py`
- **CI/VCS/test hygiene:** COMP-017 `.gitlab-ci.yml`, COMP-018 `.gitignore`, COMP-019 `tests/config.py`, COMP-020 `migrations/README.md`

**New data model:** `failed_tasks` table (14 columns including `celery_task_id`, `task_name`, `task_args`, `error_trace`, `status`) written exclusively by COMP-011; requires a new Alembic migration registered in COMP-020. The existing `audit_log` table gains no schema change but its writes are now atomically coupled with handover record writes via COMP-014.

---

## Pre-Implementation Baseline

Run the following before any file changes. Capture output as the regression reference; all tasks must keep this baseline green.

```bash
# Primary regression baseline
pytest tests/ -v --tb=short 2>&1 | tee baseline_test_results.txt; echo "Exit: $?"

# Inventory current APScheduler import surface (must reach zero after T-019)
grep -r "apscheduler\|APScheduler" . --include="*.py" | tee baseline_apscheduler_imports.txt

# Audit tracked binary files targeted for history removal (T-002)
git log --all --name-only --diff-filter=A -- '*.pdf' '*.docx' '*.doc' '*.xlsx' '*.pptx' | tee baseline_binary_files.txt
```

---

## Task Breakdown

| Task ID | Title | Dependencies | Effort (days) | Component | Type |
|---|---|---|---|---|---|
| T-001 | Add binary document extension patterns to `.gitignore` with Confluence redirect comment | — | 0.5 | COMP-018 | config |
| T-002 | Purge all tracked binary document files from full git history via `git filter-repo`; verify zero reachable matches | T-001 | 1.0 | COMP-018 | config |
| T-003 | Create `migrations/README.md` registry cataloguing all existing Alembic revisions and ad-hoc SQL scripts with status and execution order | — | 0.5 | COMP-020 | new |
| T-004 | Update `requirements.txt`: add `gunicorn`, `celery[redis]`, `redis` at pinned versions; remove `APScheduler` | — | 0.5 | COMP-001/002/005 | modify |
| T-005 | Create `requirements-ci.txt` with pinned versions of `pip-audit` and `bandit` (CI-only; not in production requirements) | — | 0.25 | COMP-017 | new |
| T-006 | Add `security` stage to `.gitlab-ci.yml` with three jobs: dependency CVE scan (`pip-audit`), Python SAST (`bandit`), and committed-secret detection (GitLab template); configure CVE scan as blocking merge gate | T-005 | 1.0 | COMP-017 | modify |
| T-007 | Create `startup_checks.py`: validate all required secrets are present and decryptable via SecretsManager; probe primary database connectivity; exit non-zero with named-field error message on any failure | — | 1.0 | COMP-004 | new |
| T-008 | Create `gunicorn.conf.py`: declare `workers=1`, `bind=0.0.0.0:5000`, timeout, log level, and access log format as version-controlled parameters | — | 0.5 | COMP-002 | new |
| T-009 | Create `start.sh`: invoke `startup_checks.py`; propagate non-zero exit without launching Gunicorn; on success invoke `gunicorn --config gunicorn.conf.py app:app` | T-007, T-008 | 0.5 | COMP-001 | new |
| T-010 | Update `tests/config.py`: replace hardcoded credential literals with `os.environ` reads for `TEST_SUPERADMIN_PASSWORD`, `TEST_ADMIN_PASSWORD`, `TEST_USER_PASSWORD`; add localhost-only sentinel fallbacks and non-localhost guard | — | 0.5 | COMP-019 | modify |
| T-011 | Create `celery_app.py`: Celery application factory; read `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` exclusively from environment variables; bind Flask app context | — | 1.0 | COMP-005 | new |
| T-012 | Create `tasks/__init__.py`: package init enabling Celery autodiscovery of all task modules | T-011 | 0.25 | COMP-007/008/009/010/011 | new |
| T-013 | Create `tasks/dlq_handler.py`: on-failure callback that writes full-context record to `failed_tasks` table and dispatches operations alert; alert failure must not suppress DB write | T-011, T-012 | 1.0 | COMP-011 | new |
| T-014 | Create `tasks/email_tasks.py`: email digest Celery task with `bind=True`, `max_retries=3`, `countdown=30`; route to COMP-011 on exhaustion | T-011, T-012, T-013 | 1.0 | COMP-007 | new |
| T-015 | Create `tasks/servicenow_tasks.py`: ServiceNow polling Celery task with `bind=True`, `max_retries=3`, `countdown=30`; route to COMP-011 on exhaustion | T-011, T-012, T-013 | 1.0 | COMP-008 | new |
| T-016 | Create `tasks/retry_tasks.py`: task retry sweep Celery task with `bind=True`, `max_retries=3`, `countdown=30`; route to COMP-011 on exhaustion | T-011, T-012, T-013 | 1.0 | COMP-009 | new |
| T-017 | Create `tasks/ctask_tasks.py`: ctask assignment check Celery task (`run_ctask_assignment`) with `bind=True`, `max_retries=3`, `countdown=30`; route to COMP-011 on exhaustion | T-011, T-012, T-013 | 1.0 | COMP-010 | new |
| T-018 | Create `celeryconfig.py`: declare Celery Beat periodic schedule mapping all four job types (COMP-007–010) to their task function references and trigger intervals | T-014, T-015, T-016, T-017 | 1.0 | COMP-006 | new |
| T-019 | Modify `services/ctask_scheduler.py`: replace all APScheduler calls with Celery-backed implementations; `get_status()` uses `celery.control.inspect(timeout=2.0)`; `force_check()` dispatches `run_ctask_assignment.delay()`; return structured dict (not raise) on broker unavailability; verify zero `apscheduler` imports remain | T-011, T-017 | 2.0 | COMP-012 | modify |
| T-020 | Modify `routes/scheduler.py`: preserve all existing route paths, HTTP methods, and response shapes; update internal calls to modified COMP-012 service; register `400`/`403` Blueprint errorhandlers returning structured JSON | T-019 | 1.0 | COMP-013 | modify |
| T-021 | Update `docker-compose.yml`: change `web` service CMD to `bash start.sh`; add `worker` service (`celery -A celery_app worker`), `beat` service (`celery -A celery_app beat`), and `redis` service; wire environment variables for broker/backend URLs | T-009, T-018 | 1.0 | COMP-003 | modify |
| T-022 | Generate Alembic migration for `failed_tasks` table via `flask db migrate -m "add_failed_tasks_table"`; verify all 14 columns, constraints, and indexes match the approved data model | T-013 | 1.0 | COMP-011 (schema) | migration |
| T-023 | Add `failed_tasks` migration entry to `migrations/README.md` with identifier, status `pending`, and execution order relative to existing revisions | T-022, T-003 | 0.25 | COMP-020 | migration |
| T-024 | Create `utils/validators.py`: `validate_{form}_fields(data: dict) -> dict` functions returning field-name-keyed actionable error messages for empty, null, and out-of-range values; empty dict on all-valid input | — | 1.0 | COMP-015 | new |
| T-025 | Create `utils/rbac_errors.py`: `resolve_rbac_error(user_role, required_role, action) -> str` returning specific permission-context messages for every supported role/action combination | — | 0.5 | COMP-016 | new |
| T-026 | Create `services/audit_service.py`: execute handover record write and audit log write within a single explicit SQLAlchemy transaction; rollback both on any exception; re-raise after rollback (no silent swallowing) | — | 1.5 | COMP-014 | new |
| T-027 | Integrate COMP-014, COMP-015, and COMP-016 into the handover route handler: add field validation gate (COMP-015), RBAC error resolution (COMP-016), and atomic audit transaction (COMP-014); preserve existing route path and HTTP method | T-024, T-025, T-026 | 1.0 | COMP-013/014/015/016 | modify |
| T-028 | Configure GitLab branch protection policy on master/main: set minimum 1 approval required; block direct pushes; verify policy rejects a zero-approval merge request | — | 0.5 | GitLab Config | config |
| T-029 | Update `CLAUDE.md` and `CONTRIBUTING.md`: document Celery scheduler architecture, Celery worker startup requirement, and environment variable credential patterns for test configuration | T-019, T-010 | 1.0 | COMP-019/COMP-012 | modify |
| T-030 | Unit tests for `startup_checks.py` (COMP-004): missing secret exits non-zero with named field; decryption failure exits non-zero; DB unreachable exits non-zero; all-pass exits zero | T-007 | 1.0 | COMP-004 | test |
| T-031 | Unit tests for `celery_app.py` (COMP-005): broker URL read from env var; raises on missing env var; Flask app context applied correctly | T-011 | 0.5 | COMP-005 | test |
| T-032 | Unit tests for `tasks/dlq_handler.py` (COMP-011): DB write contains all required fields; alert dispatched once; DB failure does not suppress alert dispatch; alert payload excludes full trace and args | T-013 | 0.5 | COMP-011 | test |
| T-033 | Unit tests for all four Celery task modules COMP-007–010: success path; transient failure triggers `self.retry` with 30-second countdown; retry count increments correctly; `max_retries` exhaustion invokes COMP-011; non-transient errors raise immediately without retry | T-014, T-015, T-016, T-017 | 1.5 | COMP-007/008/009/010 | test |
| T-034 | Unit tests for `services/ctask_scheduler.py` (COMP-012): `get_status()` with broker available returns structured dict within 3 s; `get_status()` with broker unavailable returns degraded dict within 5 s; `force_check()` enqueues task; `start()`/`stop()` send correct Celery control commands | T-019 | 1.0 | COMP-012 | test |
| T-035 | Unit tests for `utils/validators.py` (COMP-015): empty field returns named error; null value returns named error; out-of-range value returns range error; fully valid input returns empty map | T-024 | 0.5 | COMP-015 | test |
| T-036 | Unit tests for `utils/rbac_errors.py` (COMP-016): every supported role/action combination returns a non-generic, role-identifying message; `user` attempting `team_admin` action identifies `team_admin` by name | T-025 | 0.5 | COMP-016 | test |
| T-037 | Unit tests for `services/audit_service.py` (COMP-014): both writes succeed → commit called; audit log write fails → rollback called, handover record not persisted, exception re-raised; DB failure mid-transaction → full rollback | T-026 | 1.0 | COMP-014 | test |
| T-038 | Unit tests for `tests/config.py` (COMP-019): env vars set → credential values match; env vars unset + localhost target → sentinel fallbacks used; env vars unset + non-localhost target → `ConfigurationError` raised before credential transmitted | T-010 | 0.5 | COMP-019 | test |
| T-039 | Integration tests: Celery task end-to-end with live Redis (dispatch, execute, result); `get_status()` with live worker and with Redis stopped; `force_check()` task appears in queue within 1 s; handover transaction both-success and injected-audit-failure rollback; CI security stage passes clean deps and blocks on injected CVE | T-021, T-027, T-034, T-037 | 2.0 | COMP-003/012/013/014 | test |
| T-040 | E2E test scenarios: healthy container startup (port bound, 1 worker, health-check log); missing-secret container startup (exits <10 s, non-zero, no port bound); multi-worker job deduplication (exactly 1 execution log per interval across 2 workers); form submission with invalid fields (HTTP 400, field-level errors); `user`-role approval attempt (HTTP 403, `team_admin` named); DLQ routing after 3 exhausted retries (`failed_tasks` record populated, alert dispatched) | T-039 | 1.5 | All | test |

## Implementation Steps


### T-001: Add binary document extension patterns to `.gitignore` with Confluence redirect comment (config) [COMP-018]

- **Purpose**: Prevent future accidental commits of binary document files (PDF, Word, Excel, PowerPoint) to the repository by declaring them in `.gitignore`, with an inline comment directing contributors to the Confluence documentation space for document storage.
- **File(s)**: `.gitignore`
- **Dependencies**: None
- **Key notes**:
  - Append a clearly delimited block (e.g., `# --- Binary documents: store in Confluence, not in git ---`) so the intent is unambiguous to reviewers.
  - Patterns to add: `*.pdf`, `*.doc`, `*.docx`, `*.xlsx`, `*.pptx` — one per line inside the block.
  - The comment must reference the Confluence space URL or name so contributors know where to upload files instead.
  - Do **not** remove or reorder existing `.gitignore` entries; only append.
  - This step only prevents *future* commits; T-002 handles history purge.
- **Acceptance criteria**: REQ-009
- **Verify**:
  ```bash
  # Create a test file and confirm git ignores it
  touch test_doc.pdf test_doc.docx
  git status --short | grep -E "\.(pdf|doc|docx|xlsx|pptx)$"
  # Expected: no output (files are ignored)
  rm test_doc.pdf test_doc.docx
  # Confirm patterns are present in .gitignore
  grep -E "^\*\.(pdf|doc|docx|xlsx|pptx)$" .gitignore | wc -l
  # Expected: 5
  ```

---

### T-002: Purge all tracked binary document files from full git history via `git filter-repo`; verify zero reachable matches (config) [COMP-018]

- **Purpose**: Eliminate all historical commits of binary document files so that no `.pdf`, `.doc`, `.docx`, `.xlsx`, or `.pptx` file is reachable anywhere in the repository's object graph, satisfying REQ-009's "zero such files in primary branch history" clause.
- **File(s)**: Repository git history (no source file edits; git metadata rewrite only). Optionally document the purge in a `SECURITY_NOTES.md` or commit message for audit trail.
- **Dependencies**: T-001 (`.gitignore` must be committed first so purged files cannot re-enter)
- **Key notes**:
  - Use `git filter-repo` (not the deprecated `git filter-branch`): `git filter-repo --path-glob '*.pdf' --path-glob '*.doc' --path-glob '*.docx' --path-glob '*.xlsx' --path-glob '*.pptx' --invert-paths`
  - Run against a **fresh clone** to avoid accidental local-ref contamination.
  - After rewrite, run `git gc --prune=now --aggressive` to ensure loose objects are pruned.
  - Force-push all branches and tags: `git push --force --all && git push --force --tags`. Coordinate with all team members to re-clone; warn that any local branches rebased on old SHAs must be reset.
  - All CI runners and GitLab mirrors must be notified to re-clone.
  - If GitLab repository mirroring is enabled, pause it before the force-push and re-enable after.
  - Document the purge action (date, operator, reason) in a commit message or `CHANGELOG` entry so the audit trail is preserved.
- **Acceptance criteria**: REQ-009
- **Verify**:
  ```bash
  # Confirm zero binary doc objects remain in all reachable history
  git log --all --full-history -- '*.pdf' '*.doc' '*.docx' '*.xlsx' '*.pptx' \
    | wc -l
  # Expected: 0

  # Deeper object-level check
  git rev-list --objects --all \
    | git cat-file --batch-check='%(objecttype) %(rest)' \
    | grep blob \
    | awk '{print $2}' \
    | grep -E '\.(pdf|doc|docx|xlsx|pptx)$' \
    | wc -l
  # Expected: 0
  ```

---

### T-003: Create `migrations/README.md` registry cataloguing all existing Alembic revisions and ad-hoc SQL scripts with status and execution order (new) [COMP-020]

- **Purpose**: Establish a human-readable, version-controlled registry of every schema migration so operators can audit execution order, identify pending migrations, and comply with REQ-010 and REQ-011.
- **File(s)**: `migrations/README.md` (create new)
- **Dependencies**: None
- **Key notes**:
  - Discover all existing revisions by running `flask db history` (or inspecting `migrations/versions/*.py` directly) and listing each with: Alembic revision ID, migration file name, one-line description, `status` (`applied` | `pending`), and sequential execution order number.
  - Also enumerate any ad-hoc SQL scripts found in the repo (e.g., `migrations/sql/*.sql`) with the same fields plus a `type: sql` marker.
  - Use a Markdown table with columns: `Order | Revision ID | File | Description | Type | Status`.
  - Add a **Contributing** section explaining: all new schema changes must be Alembic-only, and every new migration must have a corresponding row added to this table before the MR is merged.
  - `status` for all currently applied revisions should be `applied`; any not yet run against production should be `pending`.
  - This file will be updated in T-023 when the `failed_tasks` migration is added.
- **Acceptance criteria**: REQ-010, REQ-011
- **Verify**:
  ```bash
  # Confirm file exists and contains expected headers
  grep -E "Order|Revision ID|Status" migrations/README.md
  # Count rows matches number of migration files
  ls migrations/versions/*.py | wc -l
  grep -c "| applied\|| pending" migrations/README.md
  # Counts should match (one row per migration file)
  ```

---

### T-004: Update `requirements.txt`: add `gunicorn`, `celery[redis]`, `redis` at pinned versions; remove `APScheduler` (modify) [COMP-001/002/005]

- **Purpose**: Align production dependencies with the new Gunicorn WSGI server and Celery/Redis scheduler architecture while removing the deprecated APScheduler dependency.
- **File(s)**: `requirements.txt`
- **Dependencies**: None
- **Key notes**:
  - Pin exact versions using `==` (not `>=`) to ensure reproducible builds: choose the latest stable releases available as of the implementation date (e.g., `gunicorn==21.2.0`, `celery[redis]==5.3.6`, `redis==5.0.1` — confirm exact versions against PyPI at implementation time).
  - Remove **all** lines referencing `APScheduler` (including any `APScheduler[asyncio]` extras or transitive-hint comments).
  - Do not add `pip-audit` or `bandit` here — those belong in `requirements-ci.txt` (T-005).
  - After editing, run `pip install -r requirements.txt` in a clean virtual environment to confirm no dependency conflicts.
  - If a `requirements.in` / `pip-compile` workflow exists, update the source `.in` file and recompile; do not hand-edit the compiled output.
- **Acceptance criteria**: REQ-002, REQ-003 (indirect — enables Gunicorn and Celery)
- **Verify**:
  ```bash
  grep "gunicorn==" requirements.txt
  grep "celery\[redis\]==" requirements.txt
  grep "redis==" requirements.txt
  grep -i "apscheduler" requirements.txt
  # Expected: first three lines return matches; last returns nothing
  pip install --dry-run -r requirements.txt 2>&1 | grep -i "error" | wc -l
  # Expected: 0
  ```

---

### T-005: Create `requirements-ci.txt` with pinned versions of `pip-audit` and `bandit` (CI-only; not in production requirements) (new) [COMP-017]

- **Purpose**: Isolate CI-only security scanning tools into a separate requirements file so they never enter the production image, keeping the attack surface and image size minimal.
- **File(s)**: `requirements-ci.txt` (create new)
- **Dependencies**: None
- **Key notes**:
  - File must contain exactly two runtime entries: `pip-audit==<pinned>` and `bandit==<pinned>` (confirm latest stable versions at implementation time, e.g., `pip-audit==2.7.3`, `bandit==1.7.8`).
  - Add a header comment: `# CI-only security tooling — do NOT install in production images`.
  - Do **not** include `-r requirements.txt` in this file; it must be installed independently in CI alongside, not instead of, `requirements.txt`.
  - Pin with `==` for reproducibility; CI dependency drift must be a deliberate change, not silent.
- **Acceptance criteria**: REQ-008
- **Verify**:
  ```bash
  cat requirements-ci.txt
  # Confirm exactly two package lines (pip-audit and bandit) plus comment
  grep -c "^[a-z]" requirements-ci.txt
  # Expected: 2
  grep -i "requirements.txt" requirements-ci.txt | wc -l
  # Expected: 0 (no -r inclusion)
  pip install --dry-run -r requirements-ci.txt 2>&1 | grep -i "error" | wc -l
  # Expected: 0
  ```

---

### T-006: Add `security` stage to `.gitlab-ci.yml` with three jobs: dependency CVE scan (`pip-audit`), Python SAST (`bandit`), and committed-secret detection (GitLab template); configure CVE scan as blocking merge gate (modify) [COMP-017]

- **Purpose**: Enforce automated security checks on every merge request: CVE scanning blocks merges on detected vulnerabilities; SAST and secret detection surface findings without requiring remediation to unblock (advisory).
- **File(s)**: `.gitlab-ci.yml`
- **Dependencies**: T-005
- **Key notes**:
  - Add `security` to the top-level `stages` list. Position it after `test` and before `deploy` (or at the end if no deploy stage exists).
  - **Job 1 — `dependency-scan` (blocking)**:
    - `stage: security`
    - `image: python:3.x-slim` (match project Python version)
    - Script: `pip install -r requirements-ci.txt && pip-audit -r requirements.txt --format=json -o pip-audit-report.json`
    - `artifacts: reports:` pointing to `pip-audit-report.json` with `when: always`
    - No `allow_failure` key (defaults to `false`), making it a hard merge gate.
  - **Job 2 — `sast-bandit` (advisory)**:
    - `stage: security`
    - Script: `pip install -r requirements-ci.txt && bandit -r . -x tests/ -f json -o bandit-report.json`
    - `allow_failure: true` (advisory; does not block merge)
    - Artifact: `bandit-report.json`
  - **Job 3 — `secret-detection` (advisory)**:
    - Use the official GitLab template: `include: - template: Security/Secret-Detection.gitlab-ci.yml`
    - Override `stage: security` via `secret_detection:` job extension if needed.
    - `allow_failure: true` initially; tighten after baseline false-positive review.
  - Ensure all three jobs run only on merge requests and main/master branches: use `rules:` or `only: [merge_requests, master, main]`.
  - Do **not** install `requirements-ci.txt` packages in any non-security stage to avoid polluting test or build environments.
- **Acceptance criteria**: REQ-008
- **Verify**:
  ```bash
  # Validate YAML syntax
  gitlab-ci-lint .gitlab-ci.yml
  # or
  python -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml'))"

  # Confirm stage ordering
  grep -A 10 "^stages:" .gitlab-ci.yml | grep "security"

  # Confirm blocking job has no allow_failure
  grep -A 20 "dependency-scan:" .gitlab-ci.yml | grep "allow_failure"
  # Expected: no output (allow_failure absent = false by default)

  # Dry-run pip-audit locally to confirm it executes
  pip install -r requirements-ci.txt
  pip-audit -r requirements.txt --format=json
  ```

---

### T-007: Create `startup_checks.py`: validate all required secrets are present and decryptable via SecretsManager; probe primary database connectivity; exit non-zero with named-field error message on any failure (new) [COMP-004]

- **Purpose**: Implement a fail-fast pre-flight check that prevents the application from binding to a port when it cannot function correctly, satisfying REQ-014's "exit within 10s with named error; no port bound" requirement.
- **File(s)**: `startup_checks.py` (create new at project root)
- **Dependencies**: None
- **Key notes**:
  - **Secrets check**: Read the list of required secret names from a constant (e.g., `REQUIRED_SECRETS = ["DB_PASSWORD", "API_KEY", ...]` — enumerate all secrets the app depends on). For each, call SecretsManager (AWS `boto3.client('secretsmanager')` or equivalent) with a short timeout (≤3s). If any secret is missing (`ResourceNotFoundException`) or decryption fails (`DecryptionFailureException`, `InternalServiceError`), print a structured error to `stderr` in the form `{"check": "secrets", "field": "<SECRET_NAME>", "error": "<reason>"}` and `sys.exit(1)`.
  - **Database check**: Attempt a lightweight connectivity probe (e.g., `SELECT 1` via SQLAlchemy `engine.connect()` or a raw `psycopg2` connect) with a connect timeout of ≤5s. On failure, print `{"check": "database", "field": "PRIMARY_DB", "error": "<reason>"}` to `stderr` and `sys.exit(1)`.
  - **Total timeout budget**: The sum of all check timeouts must be ≤10s to meet REQ-014. Implement checks sequentially (secrets first, then DB); short-circuit on first failure.
  - **Success path**: Print `{"check": "all", "status": "ok"}` to `stdout` and `sys.exit(0)`.
  - **No side effects**: This script must not start any threads, bind sockets, or modify application state. It is read-only with respect to the system.
  - **Credentials**: Read DB URL and SecretsManager config exclusively from environment variables — no hardcoded values.
  - The script must be executable standalone (`python startup_checks.py`) without importing the Flask app to keep startup time minimal.
- **Acceptance criteria**: REQ-014
- **Verify**:
  ```bash
  # All-pass case
  python startup_checks.py; echo "Exit: $?"
  # Expected: {"check": "all", "status": "ok"} and Exit: 0

  # Missing secret simulation
  FAKE_SECRET_MODE=missing python startup_checks.py; echo "Exit: $?"
  # Expected: stderr JSON with "field": "<SECRET_NAME>" and Exit: 1

  # DB unreachable simulation
  DATABASE_URL=postgresql://invalid:5432/nodb python startup_checks.py; echo "Exit: $?"
  # Expected: stderr JSON with "field": "PRIMARY_DB" and Exit: 1
  ```

---

### T-008: Create `gunicorn.conf.py`: declare `workers=1`, `bind=0.0.0.0:5000`, timeout, log level, and access log format as version-controlled parameters (new) [COMP-002]

- **Purpose**: Codify all Gunicorn server parameters in a version-controlled file so that server configuration is reviewable, auditable, and consistent across deployments, rather than buried in shell flags or environment variables.
- **File(s)**: `gunicorn.conf.py` (create new at project root)
- **Dependencies**: None
- **Key notes**:
  - Required parameters (exact variable names that Gunicorn reads from a config file):
    - `workers = 1` — REQ-002 mandates exactly 1 worker initially.
    - `bind = "0.0.0.0:5000"` — must match the Docker port mapping in COMP-003.
    - `timeout = 120` — or match the existing application timeout expectation; document the rationale in a comment.
    - `loglevel = "info"` — appropriate for production; `"debug"` must not be the default.
    - `accesslog = "-"` — log to stdout so Docker/container logging captures access logs.
    - `errorlog = "-"` — log to stderr.
    - `access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'` — standard combined log format.
  - Add a comment block at the top: `# Gunicorn configuration — edit this file to tune server parameters.` and reference REQ-002.
  - All values must be Python literals (not `os.environ` reads) in this file; runtime overrides via environment variables are acceptable as an additional layer but defaults must be here.
  - Do **not** set `daemon = True`; containers must run in the foreground.
- **Acceptance criteria**: REQ-002
- **Verify**:
  ```bash
  # Validate Python syntax
  python -c "import py_compile; py_compile.compile('gunicorn.conf.py')"
  # Confirm workers=1
  python -c "exec(open('gunicorn.conf.py').read()); print(workers)"
  # Expected: 1
  # Confirm bind address
  python -c "exec(open('gunicorn.conf.py').read()); print(bind)"
  # Expected: 0.0.0.0:5000
  # Run Gunicorn with this config in dry-run (check config only)
  gunicorn --config gunicorn.conf.py --check-config app:app
  # Expected: exits 0 with no errors
  ```

---

### T-009: Create `start.sh`: invoke `startup_checks.py`; propagate non-zero exit without launching Gunicorn; on success invoke `gunicorn --config gunicorn.conf.py app:app` (new) [COMP-001]

- **Purpose**: Implement the container entrypoint script that enforces the fail-fast startup contract: health checks must pass before the WSGI server is started, ensuring no port is ever bound when the application is in a degraded state.
- **File(s)**: `start.sh` (create new at project root)
- **Dependencies**: T-007 (`startup_checks.py` must exist), T-008 (`gunicorn.conf.py` must exist)
- **Key notes**:
  - First line must be `#!/bin/bash` (or `#!/bin/sh` if POSIX portability is needed — prefer `bash` for `set -e` semantics).
  - Second line: `set -e` — ensures any non-zero exit code propagates and terminates the script immediately.
  - Invoke startup checks: `python startup_checks.py` — because `set -e` is active, a non-zero exit here stops the script before reaching Gunicorn.
  - On success, exec Gunicorn: `exec gunicorn --config gunicorn.conf.py app:app` — using `exec` replaces the shell process with Gunicorn, making Gunicorn PID 1 in the container (correct signal handling for graceful shutdown).
  - Do **not** add `|| true` or any error-suppression construct around `startup_checks.py`.
  - File must be committed with executable permission: `git add --chmod=+x start.sh` or `chmod +x start.sh` before committing.
  - Add a brief comment block explaining the startup sequence for future maintainers.
  - Validate `app:app` matches the actual Flask application module and instance name in the project.
- **Acceptance criteria**: REQ-001, REQ-014
- **Verify**:
  ```bash
  # Confirm executable bit is set
  ls -la start.sh | grep "^-rwx"

  # Verify script syntax
  bash -n start.sh

  # Simulate failing startup check: script must exit non-zero and not invoke gunicorn
  # (mock startup_checks.py to exit 1, confirm gunicorn is never called)
  cat > /tmp/mock_startup_checks.py << 'EOF'
  import sys; sys.exit(1)
  EOF
  # Replace temporarily and run — expect exit 1, no gunicorn process
  cp startup_checks.py startup_checks.py.bak
  cp /tmp/mock_startup_checks.py startup_checks.py
  bash start.sh; echo "Exit: $?"
  # Expected: Exit: 1, no gunicorn process started
  cp startup_checks.py.bak startup_checks.py

  # Full integration: confirm gunicorn starts when checks pass
  bash start.sh &
  sleep 3 && curl -s http://localhost:5000/health | grep -i "ok"
  kill %1
  ```

---

### T-010: Update `tests/config.py`: replace hardcoded credential literals with `os.environ` reads for `TEST_SUPERADMIN_PASSWORD`, `TEST_ADMIN_PASSWORD`, `TEST_USER_PASSWORD`; add localhost-only sentinel fallbacks and non-localhost guard (modify) [COMP-019]

- **Purpose**: Eliminate plaintext credential literals from source control and enforce that tests cannot silently run against non-local targets with fallback credentials, satisfying REQ-007.
- **File(s)**: `tests/config.py`
- **Dependencies**: None
- **Key notes**:
  - Replace every hardcoded password literal with `os.environ.get("TEST_SUPERADMIN_PASSWORD")`, `os.environ.get("TEST_ADMIN_PASSWORD")`, `os.environ.get("TEST_USER_PASSWORD")`.
  - **Sentinel fallbacks**: If an env var is absent and the target host resolves to `localhost` / `127.0.0.1`, use a clearly non-production sentinel string (e.g., `"dev-only-sentinel-XXXX"`) so local developers can run tests without setting env vars. The sentinel must be obviously non-production (not a real password format).
  - **Non-localhost guard**: Detect the target host (read from `TEST_BASE_URL` or the existing config pattern). If the target is **not** localhost and a required env var is absent (i.e., the sentinel would be used), raise `ConfigurationError` (define as a local exception class or use `RuntimeError`) with a message like `"TEST_ADMIN_PASSWORD env var required for non-localhost target; refusing to transmit sentinel credential"`. This must fire **before** any HTTP request is made.
  - Remove or comment out all previous literal credential strings. Leave no valid password strings in the file.
  - Import `os` at the top of the file if not already present.
  - Ensure existing test fixtures that reference these config values require no changes to their call sites — only the config module internals change.
- **Acceptance criteria**: REQ-007
- **Verify**:
  ```bash
  # Confirm no plaintext credential literals remain
  grep -E "(password|passwd|pwd)\s*=\s*['\"][^'\"]{4,}['\"]" tests/config.py
  # Expected: no output (or only sentinel strings that are visibly non-production)

  # Env vars set → values used
  TEST_SUPERADMIN_PASSWORD=mysecret python -c \
    "from tests.config import SUPERADMIN_PASSWORD; assert SUPERADMIN_PASSWORD == 'mysecret'"

  # Env vars unset + localhost → sentinel returned without error
  python -c \
    "import os; os.environ.pop('TEST_ADMIN_PASSWORD', None); \
     from tests import config; print(config.ADMIN_PASSWORD)"
  # Expected: sentinel string printed, no exception

  # Env vars unset + non-localhost → ConfigurationError raised
  TEST_BASE_URL=https://staging.example.com python -c \
    "import os; os.environ.pop('TEST_ADMIN_PASSWORD', None); \
     from tests import config"
  # Expected: ConfigurationError or RuntimeError raised
  ```

### T-011: Create `celery_app.py` (new) COMP-005

- **Purpose**: Establish the single, shared Celery application instance used by all task modules, the Beat scheduler, and the Celery worker process. Reading broker/backend exclusively from environment variables ensures no credentials appear in source.
- **File(s)**: `celery_app.py` (project root)
- **Dependencies**: None
- **Key notes**:
  - Import `Celery` from `celery` and `Flask` app factory from `app.py` (or wherever the Flask app is created).
  - Read `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` via `os.environ` — do **not** provide hardcoded defaults. Raise `RuntimeError` with a descriptive message if either variable is absent at import time so container startup fails fast.
  - Create the Celery instance: `celery = Celery(__name__, broker=broker_url, backend=result_backend)`.
  - Bind the Flask application context using `celery.conf.update(app.config)` and a `TaskBase` subclass that pushes/pops an app context on `__call__`, so all task functions can use SQLAlchemy and Flask extensions normally.
  - Set `celery.conf.task_serializer = 'json'` and `celery.conf.result_serializer = 'json'` for security.
  - Do **not** import any task modules here; autodiscovery is handled in `tasks/__init__.py` (T-012).
  - Do **not** import `celeryconfig`; Beat schedule is applied separately.
- **Acceptance criteria**: REQ-003, REQ-005
- **Verify**:
  ```bash
  CELERY_BROKER_URL=redis://localhost:6379/0 CELERY_RESULT_BACKEND=redis://localhost:6379/1 python -c "from celery_app import celery; print(celery.conf.broker_url)"
  # Expect: redis://localhost:6379/0

  python -c "from celery_app import celery"
  # Expect: RuntimeError mentioning missing env var
  ```

---

### T-012: Create `tasks/__init__.py` (new) COMP-007/008/009/010/011

- **Purpose**: Mark `tasks/` as a Python package and trigger Celery autodiscovery so all task modules are registered with the shared Celery instance when the worker or Beat process starts.
- **File(s)**: `tasks/__init__.py`
- **Dependencies**: T-011
- **Key notes**:
  - Import the shared `celery` instance from `celery_app`.
  - Call `celery.autodiscover_tasks(['tasks.email_tasks', 'tasks.servicenow_tasks', 'tasks.retry_tasks', 'tasks.ctask_tasks', 'tasks.dlq_handler'])` with explicit module list (avoids filesystem-scan surprises in Docker layer caching).
  - Keep this file minimal — no business logic.
  - After T-014–T-017 are created, a worker started with `-A celery_app` must list all four periodic task names in `celery inspect registered`.
- **Acceptance criteria**: REQ-003
- **Verify**:
  ```bash
  python -c "import tasks; print('tasks package loaded')"
  # After T-014–T-017 exist:
  celery -A celery_app inspect registered
  # Expect: all four task names listed
  ```

---

### T-013: Create `tasks/dlq_handler.py` (new) COMP-011

- **Purpose**: Provide the on-failure callback (`on_failure` / `link_error` target) that writes a full-context record to the `failed_tasks` table and dispatches an operations alert when a task exhausts all retries. DB write and alert dispatch are independently guarded so a failure in one does not suppress the other.
- **File(s)**: `tasks/dlq_handler.py`
- **Dependencies**: T-011, T-012
- **Key notes**:
  - Define a regular Celery task `handle_failed_task(task_id, task_name, args, kwargs, error_message, error_trace)` decorated with `@celery.task(name='tasks.dlq_handler.handle_failed_task')`.
  - **DB write**: inside a `try/except`, open a SQLAlchemy session, insert a `FailedTask` record with all 14 columns from the data model (`failure_count=3`, `status='failed'`, `failed_at=datetime.utcnow()`). Commit. Log any DB exception but do **not** re-raise — proceed to alert step regardless.
  - **Alert dispatch**: inside a separate `try/except`, call the existing operations-alert utility (email/Slack/etc. per project convention). Set `alerted_at` on the record if the alert succeeds (best-effort UPDATE). Log any alert exception but do **not** re-raise.
  - `task_args` and `task_kwargs` must be stored as JSON. **Strip** raw exception tracebacks from the alert payload; the full trace goes only to `error_trace` column in DB.
  - This handler must **not** itself retry (no `bind=True`, no `max_retries`).
  - Import `celery` from `celery_app`; import the `FailedTask` model (to be created in T-022's migration; use a lazy import or conditional guard until then).
- **Acceptance criteria**: REQ-006
- **Verify**:
  ```bash
  python -m pytest tests/unit/test_dlq_handler.py -v
  # Tests (T-032): DB write contains all required fields; alert dispatched once;
  # DB failure does not suppress alert; alert payload excludes full trace.
  ```

---

### T-014: Create `tasks/email_tasks.py` (new) COMP-007

- **Purpose**: Implement the periodic email digest as a Celery task with retry policy and DLQ routing on exhaustion.
- **File(s)**: `tasks/email_tasks.py`
- **Dependencies**: T-011, T-012, T-013
- **Key notes**:
  - Decorate with `@celery.task(bind=True, max_retries=3, default_retry_delay=30, name='tasks.email_tasks.send_email_digest')`.
  - Port existing email digest business logic verbatim from the APScheduler job body; do **not** change the logic itself in this task.
  - Wrap the entire body in `try/except`. On **transient** exceptions (network errors, SMTP timeouts — use an explicit tuple of exception types, not bare `except`), call `self.retry(exc=exc, countdown=30)`. On **non-transient** exceptions, call `handle_failed_task.delay(...)` with all required fields (task id via `self.request.id`) and then `raise`.
  - On `MaxRetriesExceededError`, call `handle_failed_task.delay(...)` and re-raise.
  - Never silently swallow exceptions.
- **Acceptance criteria**: REQ-003, REQ-006
- **Verify**:
  ```bash
  python -m pytest tests/unit/test_task_modules.py::TestEmailDigestTask -v
  # Tests (T-033): success path; transient → self.retry(countdown=30);
  # retry count increments; max_retries exhaustion → DLQ; non-transient → raise immediately.
  ```

---

### T-015: Create `tasks/servicenow_tasks.py` (new) COMP-008

- **Purpose**: Implement the periodic ServiceNow polling job as a Celery task with retry policy and DLQ routing on exhaustion.
- **File(s)**: `tasks/servicenow_tasks.py`
- **Dependencies**: T-011, T-012, T-013
- **Key notes**:
  - Decorate with `@celery.task(bind=True, max_retries=3, default_retry_delay=30, name='tasks.servicenow_tasks.poll_servicenow')`.
  - Port existing ServiceNow polling business logic verbatim from the APScheduler job body.
  - Apply identical retry/DLQ pattern as T-014: explicit transient exception types → `self.retry(countdown=30)`; non-transient or `MaxRetriesExceededError` → `handle_failed_task.delay(...)` then re-raise.
  - ServiceNow HTTP calls should use a session with an explicit `timeout` (e.g. 10 s) to prevent indefinite blocking of the worker thread.
- **Acceptance criteria**: REQ-003, REQ-006
- **Verify**:
  ```bash
  python -m pytest tests/unit/test_task_modules.py::TestServiceNowPollTask -v
  # Tests (T-033): same four scenarios as T-014.
  ```

---

### T-016: Create `tasks/retry_tasks.py` (new) COMP-009

- **Purpose**: Implement the periodic task retry sweep as a Celery task with retry policy and DLQ routing on exhaustion.
- **File(s)**: `tasks/retry_tasks.py`
- **Dependencies**: T-011, T-012, T-013
- **Key notes**:
  - Decorate with `@celery.task(bind=True, max_retries=3, default_retry_delay=30, name='tasks.retry_tasks.run_retry_sweep')`.
  - Port existing retry sweep business logic verbatim from the APScheduler job body.
  - Apply identical retry/DLQ pattern as T-014 and T-015.
  - The sweep queries for records in a retriable state; ensure the DB query uses the Flask app context (available via the `TaskBase` context binding established in T-011).
- **Acceptance criteria**: REQ-003, REQ-006
- **Verify**:
  ```bash
  python -m pytest tests/unit/test_task_modules.py::TestRetrySweepTask -v
  # Tests (T-033): same four scenarios as T-014.
  ```

---

### T-017: Create `tasks/ctask_tasks.py` (new) COMP-010

- **Purpose**: Implement the ctask assignment check as a Celery task (`run_ctask_assignment`) with retry policy and DLQ routing. This task name is referenced directly by `services/ctask_scheduler.py` (T-019).
- **File(s)**: `tasks/ctask_tasks.py`
- **Dependencies**: T-011, T-012, T-013
- **Key notes**:
  - Decorate with `@celery.task(bind=True, max_retries=3, default_retry_delay=30, name='tasks.ctask_tasks.run_ctask_assignment')`.
  - The task name `'tasks.ctask_tasks.run_ctask_assignment'` is the stable string used in T-018 (Beat schedule) and T-019 (`force_check()`). Do not rename it.
  - Port existing ctask assignment logic verbatim from the APScheduler job body.
  - Apply identical retry/DLQ pattern as T-014–T-016.
  - Export `run_ctask_assignment` at module level so `from tasks.ctask_tasks import run_ctask_assignment` works cleanly in T-019.
- **Acceptance criteria**: REQ-003, REQ-004, REQ-006
- **Verify**:
  ```bash
  python -m pytest tests/unit/test_task_modules.py::TestCtaskAssignmentTask -v
  # Tests (T-033): same four scenarios as T-014.
  ```

---

### T-018: Create `celeryconfig.py` (new) COMP-006

- **Purpose**: Declare the Celery Beat periodic schedule that maps all four job types (COMP-007–010) to their task function references and trigger intervals, keeping schedule configuration version-controlled and separate from application code.
- **File(s)**: `celeryconfig.py` (project root)
- **Dependencies**: T-014, T-015, T-016, T-017
- **Key notes**:
  - Define `beat_schedule` as a plain `dict` mapping a human-readable key to a schedule entry with `'task'` (fully-qualified string name, e.g. `'tasks.email_tasks.send_email_digest'`), `'schedule'` (use `crontab` or `timedelta` from `celery.schedules`), and `'options': {'expires': <interval_seconds>}` to prevent stale task accumulation.
  - Use the **same task name strings** registered in T-014–T-017 decorators — copy them verbatim to prevent silent misrouting.
  - Set `timezone = 'UTC'` explicitly.
  - Set `task_acks_late = True` and `task_reject_on_worker_lost = True` at the top level to support exactly-once-per-interval semantics (REQ-005) combined with Redis lock or Celery's built-in deduplication pattern.
  - **Do not** import task functions directly here — use string task names only, to avoid circular imports.
  - Apply this config in `celery_app.py` via `celery.config_from_object('celeryconfig')` (add this call to `celery_app.py` after the instance is created — this is the only modification to T-011's file).
- **Acceptance criteria**: REQ-003, REQ-005, REQ-006
- **Verify**:
  ```bash
  CELERY_BROKER_URL=redis://localhost:6379/0 CELERY_RESULT_BACKEND=redis://localhost:6379/1 \
    celery -A celery_app inspect scheduled
  # Expect: all four task names present in beat schedule output.

  python -c "import celeryconfig; assert len(celeryconfig.beat_schedule) == 4"
  ```

---

### T-019: Modify `services/ctask_scheduler.py` (modify) COMP-012

- **Purpose**: Replace every APScheduler call with Celery-backed implementations so the scheduler interface (start/stop/get_status/force_check) operates entirely through Celery control and inspection APIs, with no APScheduler imports remaining.
- **File(s)**: `services/ctask_scheduler.py`
- **Dependencies**: T-011, T-017
- **Key notes**:
  - **Remove** all `import apscheduler` / `from apscheduler` lines. Grep must return zero matches after this task.
  - `get_status()`:
    - Call `celery.control.inspect(timeout=2.0)` — hard cap at 2.0 s.
    - Wrap in `try/except` (catches `kombu.exceptions.OperationalError` and bare `Exception`).
    - On success: return `{'status': 'ok', 'workers_active': <count>, 'scheduled_jobs': [...], 'broker_reachable': True}`.
    - On failure (including timeout): return `{'status': 'degraded', 'workers_active': 0, 'scheduled_jobs': [], 'broker_reachable': False}` — **do not raise**.
    - The entire call chain must complete within 5 s wall-clock (REQ-013).
  - `force_check()`:
    - Call `run_ctask_assignment.delay()` (import from `tasks.ctask_tasks`).
    - Return `{'status': 'ok', 'task_id': result.id}`.
    - Wrap in `try/except`; on broker unavailability return `{'status': 'error', 'broker_reachable': False}` — **do not raise**.
  - `start()`: Use `celery.control.broadcast('enable_events')` or equivalent Beat-resume control command. Return structured dict.
  - `stop()`: Use `celery.control.broadcast('disable_events')` or equivalent. Return structured dict.
  - All four methods must return structured dicts, never raise to their caller (routes handle error shapes).
- **Acceptance criteria**: REQ-003, REQ-004, REQ-013
- **Verify**:
  ```bash
  grep -r "apscheduler" services/ctask_scheduler.py
  # Expect: no output (zero matches)

  python -m pytest tests/unit/test_ctask_scheduler.py -v
  # Tests (T-034): get_status with broker up returns dict <3s; broker down returns
  # degraded dict <5s; force_check enqueues task; start/stop send correct commands.
  ```

---

### T-020: Modify `routes/scheduler.py` (modify) COMP-013

- **Purpose**: Update the scheduler route handler to call the modified COMP-012 service methods, register Blueprint-level error handlers returning structured JSON for 400/403, and preserve all existing route paths, HTTP methods, and response shapes exactly.
- **File(s)**: `routes/scheduler.py`
- **Dependencies**: T-019
- **Key notes**:
  - **Do not change** any `@blueprint.route(...)` path strings or HTTP method declarations — API contract is frozen.
  - **Do not change** the success response shapes — they must match the API endpoint table exactly (`{status, workers_active, scheduled_jobs, broker_reachable}` for GET `/scheduler/status`, etc.).
  - Replace any direct APScheduler or old scheduler service calls with calls to the updated `ctask_scheduler` service methods (`get_status()`, `start()`, `stop()`, `force_check()`).
  - Map service return dict `status == 'error'` / `broker_reachable == False` → HTTP 503 with `{'status': 'error', 'message': ...}` body.
  - `force_check` response must include `task_id` from the service return value.
  - Register two Blueprint errorhandlers:
    ```python
    @scheduler_bp.errorhandler(400)
    def bad_request(e): return jsonify({'error': str(e)}), 400

    @scheduler_bp.errorhandler(403)
    def forbidden(e): return jsonify({'error': str(e)}), 403
    ```
  - Do **not** import APScheduler anywhere in this file. Verify with grep after edit.
- **Acceptance criteria**: REQ-003, REQ-004, REQ-013, REQ-017
- **Verify**:
  ```bash
  grep -r "apscheduler" routes/scheduler.py
  # Expect: no output

  python -m pytest tests/unit/test_scheduler_routes.py -v
  # Verify all route paths unchanged, 503 returned on broker unavailability,
  # 400/403 handlers return JSON.

  # Smoke test against running stack:
  curl -s http://localhost:5000/scheduler/status | python -m json.tool
  # Expect: keys status, workers_active, scheduled_jobs, broker_reachable present.
  ```

### T-021: Update `docker-compose.yml` (modify) COMP-003

- **Purpose**: Wire together the full container topology: web service using `start.sh`, plus dedicated Celery worker, Celery beat scheduler, and Redis broker/backend services.
- **File(s)**: `docker-compose.yml`
- **Dependencies**: T-009 (`start.sh` must exist), T-018 (`celeryconfig.py` must exist so beat has a schedule to load)
- **Key notes**:
  - Change the `web` service `command` (or `CMD`) to `bash start.sh`. Do **not** invoke `python app.py` or `gunicorn` directly — the entrypoint script owns that.
  - Add a `redis` service using the official `redis:7-alpine` image (or a pinned patch version). Expose port `6379` internally only; do not publish to the host in production compose.
  - Add a `worker` service: `image` (or `build`) identical to `web`; command `celery -A celery_app worker --loglevel=info`; depends on `redis` and `web` (for shared volume/build context).
  - Add a `beat` service: command `celery -A celery_app beat --loglevel=info --schedule /tmp/celerybeat-schedule`; depends on `redis`. Beat must **not** share a schedule file with the worker.
  - All three app services (`web`, `worker`, `beat`) must receive the same environment block containing at minimum: `CELERY_BROKER_URL=redis://redis:6379/0`, `CELERY_RESULT_BACKEND=redis://redis:6379/0`, and any `AWS_*` / `DATABASE_URL` vars already used by the application. Use an `env_file: .env` reference or explicit `environment:` keys — do not hard-code secrets.
  - Add a `healthcheck` on the `redis` service (`redis-cli ping`) so dependent services can use `condition: service_healthy`.
  - Set `restart: unless-stopped` on `worker` and `beat` to survive transient broker restarts.
- **Acceptance criteria**: REQ-001, REQ-002, REQ-003, REQ-005 (single beat instance prevents duplicate scheduling)
- **Verify**:
  ```bash
  docker compose config --quiet          # validates YAML syntax
  docker compose up -d --build
  docker compose ps                      # all 4 services show "Up"
  docker compose exec web curl -sf http://localhost:5000/scheduler/status
  docker compose logs worker | grep "celery@"   # worker registered
  docker compose logs beat   | grep "beat: Starting"
  ```

---

### T-022: Generate Alembic migration for `failed_tasks` table (migration) COMP-011 (schema)

- **Purpose**: Produce a version-controlled, reproducible schema change that creates the `failed_tasks` table with all 14 columns, constraints, and indexes matching the approved data model.
- **File(s)**: `migrations/versions/<revision_id>_add_failed_tasks_table.py` (auto-generated path)
- **Dependencies**: T-013 (`tasks/dlq_handler.py` must define the `FailedTask` model or its equivalent so Alembic can introspect it)
- **Key notes**:
  - Run `flask db migrate -m "add_failed_tasks_table"` inside the application context (with `FLASK_APP` set). Commit the generated file **unedited** only if the auto-detected diff is correct; otherwise hand-edit.
  - Required columns and types (verify against generated migration before committing):
    - `id` — `INTEGER` PRIMARY KEY AUTOINCREMENT (Postgres: `SERIAL` / `BIGSERIAL`)
    - `celery_task_id` — `VARCHAR(255)` NOT NULL UNIQUE
    - `task_name` — `VARCHAR(255)` NOT NULL
    - `task_args` — `JSON` (use `sa.JSON()`)
    - `task_kwargs` — `JSON`
    - `error_message` — `TEXT`
    - `error_trace` — `TEXT`
    - `failure_count` — `INTEGER` NOT NULL DEFAULT `3`
    - `failed_at` — `DATETIME` NOT NULL
    - `alerted_at` — `DATETIME` NULL
    - `status` — `VARCHAR(20)` NOT NULL DEFAULT `'failed'`; add `CheckConstraint("status IN ('failed','alerted','resolved')")`
    - `resolved_at` — `DATETIME` NULL
    - `resolved_by` — `VARCHAR(255)` NULL
  - Indexes to verify in the `upgrade()` function:
    - `ix_failed_tasks_status` on `(status)`
    - `ix_failed_tasks_task_name` on `(task_name)`
  - `downgrade()` must `drop_table('failed_tasks')` cleanly.
  - Do **not** add any application logic here — pure schema DDL only.
- **Acceptance criteria**: REQ-011 (all schema changes via Alembic only)
- **Verify**:
  ```bash
  flask db upgrade head
  flask db downgrade -1
  flask db upgrade head        # idempotency check
  # Inspect schema:
  python - <<'EOF'
  from app import db; from sqlalchemy import inspect
  cols = {c['name'] for c in inspect(db.engine).get_columns('failed_tasks')}
  assert cols == {'id','celery_task_id','task_name','task_args','task_kwargs',
                  'error_message','error_trace','failure_count','failed_at',
                  'alerted_at','status','resolved_at','resolved_by'}
  idxs = {i['name'] for i in inspect(db.engine).get_indexes('failed_tasks')}
  assert 'ix_failed_tasks_status' in idxs and 'ix_failed_tasks_task_name' in idxs
  print("PASS")
  EOF
  ```

---

### T-023: Add `failed_tasks` migration to `migrations/README.md` (migration) COMP-020

- **Purpose**: Keep the migration registry current by recording the new `failed_tasks` Alembic revision with its identifier, status, and correct execution order relative to all existing revisions.
- **File(s)**: `migrations/README.md`
- **Dependencies**: T-022 (revision ID is not known until migration file is generated), T-003 (`migrations/README.md` must already exist with the initial catalogue structure)
- **Key notes**:
  - Append a new row to the existing revisions table using the **actual** revision ID produced by T-022 (e.g., `a3f8c1d2e4b5`). Do not use a placeholder.
  - Row fields: `Revision ID`, `Description` (`add_failed_tasks_table`), `Status` (`pending`), `Execution Order` (one greater than the currently highest-numbered entry), `File` (relative path to the generated migration file), `Dependencies` (prior revision ID that this one `down_revision` points to).
  - Status must be `pending` at commit time — it will be updated to `applied` as part of the deployment runbook, not in this task.
  - If the README uses a different table schema established in T-003, match that schema exactly — do not introduce new columns.
- **Acceptance criteria**: REQ-010, REQ-011
- **Verify**:
  ```bash
  grep "add_failed_tasks_table" migrations/README.md
  grep "pending" migrations/README.md
  # Confirm revision ID in README matches the actual migration file name:
  REVISION=$(ls migrations/versions/ | grep add_failed_tasks | cut -d_ -f1)
  grep "$REVISION" migrations/README.md
  ```

---

### T-024: Create `utils/validators.py` (new) COMP-015

- **Purpose**: Provide reusable, form-specific validation functions that return a field-name-keyed dictionary of actionable error messages, enabling the handover route (and any future route) to return precise HTTP 400 payloads.
- **File(s)**: `utils/validators.py`
- **Dependencies**: None
- **Key notes**:
  - Public API: one function per supported form, named `validate_{form}_fields(data: dict) -> dict`. Start with at minimum `validate_handover_fields`. Add others as needed by existing routes.
  - Return type contract: `{}` (empty dict) when all fields are valid; `{"field_name": "Human-readable actionable message"}` for every failing field. **Never raise** — always return.
  - Validation rules to implement per field:
    - **Empty string**: `if not str(value).strip()` → `"<FieldLabel> is required and cannot be blank."`
    - **None / missing key**: → `"<FieldLabel> is required."`
    - **Out-of-range numeric**: include the allowed range in the message, e.g. `"Priority must be between 1 and 5."`
  - Each error message must name the field (use the human-readable label, not the dict key) and state what is wrong and what is expected — it must be directly displayable to an end user without post-processing.
  - Do **not** import Flask, SQLAlchemy, or any application models — this module must be pure Python with no application context dependency.
  - Add a module-level docstring describing the contract (empty dict = valid, field-keyed dict = invalid with reasons).
- **Acceptance criteria**: REQ-016
- **Verify**:
  ```bash
  python -m pytest tests/unit/test_validators.py -v
  # Smoke check without test suite:
  python - <<'EOF'
  from utils.validators import validate_handover_fields
  assert validate_handover_fields({"title": "", "priority": 3}) != {}
  assert validate_handover_fields({"title": "My handover", "priority": 3}) == {}
  print("PASS")
  EOF
  ```

---

### T-025: Create `utils/rbac_errors.py` (new) COMP-016

- **Purpose**: Centralise RBAC error messaging so every 403 response names the specific missing role or privilege rather than returning a generic "permission denied" string.
- **File(s)**: `utils/rbac_errors.py`
- **Dependencies**: None
- **Key notes**:
  - Single public function: `resolve_rbac_error(user_role: str, required_role: str, action: str) -> str`.
  - The returned string must:
    1. Name the `required_role` explicitly (e.g., `"team_admin"`).
    2. Name the `action` being attempted.
    3. Be phrased as a complete, user-facing sentence.
    - Example: `"The action 'approve_handover' requires the 'team_admin' role. Your current role is 'user'."` 
  - Implement a lookup table (dict or match statement) covering every `(required_role, action)` combination known to the application. Add a catch-all fallback that still includes `required_role` and `action` in the output — it must never return a generic string that omits role/action context.
  - Do **not** import Flask, db, or any application context. Pure Python only.
  - All role name strings must match the canonical role names used elsewhere in the codebase — verify against existing `routes/` files before finalising the table.
- **Acceptance criteria**: REQ-017
- **Verify**:
  ```bash
  python -m pytest tests/unit/test_rbac_errors.py -v
  # Smoke check:
  python - <<'EOF'
  from utils.rbac_errors import resolve_rbac_error
  msg = resolve_rbac_error("user", "team_admin", "approve_handover")
  assert "team_admin" in msg, f"role name missing: {msg}"
  assert "approve_handover" in msg, f"action name missing: {msg}"
  assert "user" in msg, f"current role missing: {msg}"
  print("PASS:", msg)
  EOF
  ```

---

### T-026: Create `services/audit_service.py` (new) COMP-014

- **Purpose**: Guarantee that the handover record write and the audit log write either both commit or both roll back, eliminating partial-commit states where a handover exists without an audit trail.
- **File(s)**: `services/audit_service.py`
- **Dependencies**: None (depends on existing `audit_log` model and SQLAlchemy `db` session, which already exist)
- **Key notes**:
  - Primary public function signature: `def submit_handover_with_audit(handover_data: dict, user_id: int) -> HandoverRecord` (adjust to match existing model names).
  - Implementation pattern:
    ```python
    try:
        db.session.add(handover_record)
        db.session.flush()          # assigns PK without committing
        db.session.add(audit_entry) # references handover_record.id
        db.session.commit()
        return handover_record
    except Exception:
        db.session.rollback()
        raise                       # never swallow — caller decides HTTP response
    ```
  - Use a single `db.session` — do **not** open a second session or nested transaction. `flush()` before the audit write so the audit record can reference the handover PK.
  - The `except` clause must call `db.session.rollback()` before `raise`. No logging of secrets. Log the exception class and message at `ERROR` level (without the full traceback containing user data).
  - Do **not** catch `Exception` silently — the `raise` after rollback is mandatory. The route handler is responsible for translating the exception into an HTTP 500 response.
  - Keep this module free of route/HTTP concerns (no `jsonify`, no `abort`).
- **Acceptance criteria**: REQ-015
- **Verify**:
  ```bash
  python -m pytest tests/unit/test_audit_service.py -v
  ```

---

### T-027: Integrate COMP-014/015/016 into handover route handler (modify) COMP-013/014/015/016

- **Purpose**: Enforce field validation, RBAC error resolution, and atomic audit transaction on the handover submission endpoint without altering its path, HTTP method, or success response shape.
- **File(s)**: `routes/` — the file containing the `POST /handover/submit` route handler (identify exact filename from existing codebase)
- **Dependencies**: T-024 (`validate_handover_fields`), T-025 (`resolve_rbac_error`), T-026 (`submit_handover_with_audit`)
- **Key notes**:
  - **Route path and HTTP method are frozen** — do not change `@bp.route(...)` or `methods=[...]`.
  - Integrate in this order inside the handler:
    1. **RBAC gate** (earliest exit): check `current_user.role` against required role; if insufficient, call `resolve_rbac_error(current_user.role, required_role, action)` and return `jsonify({"error": msg}), 403`.
    2. **Validation gate**: call `validate_handover_fields(request.form | request.json)` (handle both content types); if result is non-empty, return `jsonify({"errors": result}), 400`.
    3. **Atomic write**: replace the existing direct `db.session` calls with a call to `submit_handover_with_audit(data, current_user.id)`; wrap in `try/except Exception` to return `jsonify({"error": "Submission failed. Please retry."}), 500`.
  - The existing **success response shape is frozen** — return it unchanged after a successful `submit_handover_with_audit` call.
  - Register a `400` and `403` Blueprint-level errorhandler (if not already present) that returns `{"error": str(e)}` as JSON — this is a safety net, not the primary path.
  - Add imports at the top of the file; do not inline from other modules.
- **Acceptance criteria**: REQ-015, REQ-016, REQ-017
- **Verify**:
  ```bash
  python -m pytest tests/unit/test_handover_route.py -v
  # Manual smoke tests (requires running app):
  # 1. Empty required field → HTTP 400 with {"errors": {"<field>": "..."}}
  # 2. user-role attempting approval → HTTP 403 with {"error": "...team_admin..."}
  # 3. Valid submission → existing success response shape unchanged
  ```

---

### T-028: Configure GitLab branch protection on master/main (config) GitLab Config

- **Purpose**: Enforce peer review by requiring at least one approval before any merge request can be merged into the primary branch, and block direct pushes that bypass the review gate.
- **File(s)**: GitLab project settings (UI or `.gitlab/branch_protection.json` / Infrastructure-as-Code if used); document the applied settings in `CONTRIBUTING.md` (see T-029)
- **Dependencies**: None
- **Key notes**:
  - Navigate to **Settings → Repository → Protected Branches** in the GitLab project.
  - Protect both `master` and `main` (whichever is the default branch; protect the other as a precaution if it exists).
  - Settings to apply:
    - **Allowed to merge**: `Maintainers` (or `Developers + Maintainers` per team policy — confirm with team lead before applying)
    - **Allowed to push**: `No one` (blocks direct push; all changes must go via MR)
    - **Allowed to force push**: disabled
    - **Required approvals**: `1` (minimum; set via **Settings → Merge Requests → Approvals** if not available on the branch protection panel)
  - Navigate to **Settings → Merge Requests** and set:
    - **Merge method**: Merge commit (preserves history) or Squash+merge per team convention
    - **Approvals required before merge**: `1`
    - **Prevent approval by author**: enabled
    - **Remove all approvals on new commit**: enabled (forces re-review after a push)
  - Verification must be performed with a real or test MR — policy files alone are insufficient.
- **Acceptance criteria**: REQ-012
- **Verify**:
  ```bash
  # Create a test branch, open a zero-approval MR targeting master:
  git checkout -b test/branch-protection-verify
  git commit --allow-empty -m "chore: branch protection verification"
  git push origin test/branch-protection-verify
  # Open MR via GitLab UI or CLI → attempt to merge without approval
  # Expected: GitLab blocks merge with "Not enough approvals" message
  # Then: add 1 approval from a non-author → merge succeeds
  # Cleanup: delete test branch
  ```

---

### T-029: Update `CLAUDE.md` and `CONTRIBUTING.md` (modify) COMP-019/COMP-012

- **Purpose**: Make the Celery scheduler architecture, worker startup requirement, and environment-variable credential pattern discoverable for any engineer onboarding to or operating the project.
- **File(s)**: `CLAUDE.md`, `CONTRIBUTING.md`
- **Dependencies**: T-019 (`services/ctask_scheduler.py` refactored to Celery — architecture must be stable before documenting it), T-010 (`tests/config.py` updated — env var pattern must be final)
- **Key notes**:
  - **`CLAUDE.md`** (agent context file) — add or update the following sections:
    - **Scheduler Architecture**: explain that all 4 job types (email digest, ServiceNow poll, retry sweep, ctask check) run exclusively as Celery tasks dispatched by Celery Beat. HTTP processes contain no scheduler logic. `services/ctask_scheduler.py` delegates to `celery.control.inspect` (2 s timeout) and `task.delay()`.
    - **Local Development Prerequisites**: `docker compose up redis` must be running before the Flask dev server or tests that exercise scheduler routes. Without Redis, `get_status()` returns a degraded dict (not an exception) within 5 s.
    - **Environment Variables for Tests**: document `TEST_SUPERADMIN_PASSWORD`, `TEST_ADMIN_PASSWORD`, `TEST_USER_PASSWORD`; state that these must be set in the shell or a `.env.test` file before running tests against any non-localhost target. Include the exact guard behaviour: tests abort before transmitting credentials if target is not localhost and vars are unset.
  - **`CONTRIBUTING.md`** — add or update:
    - **Running Workers Locally**: exact commands to start worker and beat (`celery -A celery_app worker` / `celery -A celery_app beat`), and the Redis dependency.
    - **Test Credential Setup**: step-by-step `export TEST_*_PASSWORD=...` instructions; note sentinel fallbacks for localhost-only use.
    - **Branch Protection**: cross-reference T-028 policy (1 approval required, no direct push to master).
  - Do **not** paste actual credential values — only document the variable names and the pattern.
  - Both files must remain Markdown-valid (`markdownlint` or equivalent).
- **Acceptance criteria**: REQ-007 (documents the env var pattern), REQ-018 (internal documentation current)
- **Verify**:
  ```bash
  grep -n "CELERY_BROKER_URL\|celery_app worker\|celery_app beat" CLAUDE.md CONTRIBUTING.md
  grep -n "TEST_SUPERADMIN_PASSWORD\|TEST_ADMIN_PASSWORD\|TEST_USER_PASSWORD" CLAUDE.md CONTRIBUTING.md
  grep -n "branch protection\|1 approval" CONTRIBUTING.md
  # Optional lint:
  npx markdownlint CLAUDE.md CONTRIBUTING.md --config .markdownlint.json
  ```

---

### T-030: Unit tests for `startup_checks.py` (test) COMP-004

- **Purpose**: Verify that the startup health checker produces the correct exit codes and named-field error messages under every failure mode, preventing regressions where a broken secret or unreachable database allows the server to start silently.
- **File(s)**: `tests/unit/test_startup_checks.py`
- **Dependencies**: T-007 (`startup_checks.py` must exist)
- **Key notes**:
  - Use `unittest.mock.patch` to mock AWS SecretsManager and the database connection — no real AWS calls or DB connections in unit tests.
  - **Test cases** (one test function per case):
    1. **Missing secret exits non-zero with named field**: mock SecretsManager to raise `ClientError` for a specific secret name; call `startup_checks.run()` (or capture `SystemExit`); assert exit code is non-zero; assert the secret's name appears in the captured stderr/stdout output.
    2. **Decryption failure exits non-zero**: mock SecretsManager to return a response where decryption fails (e.g., KMS `InvalidCiphertextException`); assert exit code non-zero; assert error output names the affected secret.
    3. **DB unreachable exits non-zero**: mock the DB connection probe to raise `OperationalError`; assert exit code non-zero; assert error output contains `"database"` or equivalent named field from the implementation.
    4. **All checks pass exits zero**: mock SecretsManager to return valid secrets for all expected names; mock DB probe to succeed; assert exit code is `0`.
  - Use `pytest.raises(SystemExit) as exc_info` to capture the exit and inspect `exc_info.value.code`.
  - Use `capsys` (pytest fixture) or `unittest.mock.patch('sys.stderr')` to capture output and assert named fields appear in error messages.
  - Each test must be independent — no shared state between test functions.
  - Tests must not require network access, AWS credentials, or a running database.
- **Acceptance criteria**: REQ-014
- **Verify**:
  ```bash
  python -m pytest tests/unit/test_startup_checks.py -v --tb=short
  # All 4 test cases must pass
  # Coverage check:
  python -m pytest tests/unit/test_startup_checks.py --cov=startup_checks --cov-report=term-missing
  # Target: ≥90% line coverage of startup_checks.py
  ```

### T-031: Unit tests for `celery_app.py` (new) — COMP-005

- **Purpose**: Verify the Celery application factory reads broker/backend URLs exclusively from environment variables, raises on missing env vars, and correctly applies the Flask app context.
- **File(s)**: `tests/unit/test_celery_app.py`
- **Dependencies**: T-011 (celery_app.py must exist)
- **Key notes**:
  - Use `unittest.mock.patch.dict(os.environ, ...)` to isolate env var state per test; never rely on ambient environment.
  - Test 1 — **broker from env**: set `CELERY_BROKER_URL=redis://localhost:6379/0` and `CELERY_RESULT_BACKEND=redis://localhost:6379/1`, import/call the factory, assert `celery_app.conf.broker_url == "redis://localhost:6379/0"` and `celery_app.conf.result_backend == "redis://localhost:6379/1"`.
  - Test 2 — **raises on missing broker URL**: unset `CELERY_BROKER_URL` entirely, assert calling the factory raises `KeyError` (or the application-defined exception — match whatever `celery_app.py` raises).
  - Test 3 — **Flask context applied**: mock `Flask` app context; after factory call assert `app.app_context().__enter__` was invoked or that `celery_app.conf` carries the expected Flask integration (e.g., `flask_app` attribute is set).
  - Do NOT start a real broker; mock `celery.Celery` if needed to avoid network calls.
- **Acceptance criteria**: REQ-003 (Celery is sole scheduler runtime); verifies factory isolation from hardcoded config.
- **Verify**: `pytest tests/unit/test_celery_app.py -v`

---

### T-032: Unit tests for `tasks/dlq_handler.py` (new) — COMP-011

- **Purpose**: Verify the DLQ on-failure callback writes all required fields to `failed_tasks`, dispatches exactly one operations alert, does not suppress the DB write when the alert fails, and omits full trace and raw args from the alert payload.
- **File(s)**: `tests/unit/test_dlq_handler.py`
- **Dependencies**: T-013 (dlq_handler.py must exist)
- **Key notes**:
  - Mock the SQLAlchemy session (`db.session`) and the alert dispatch function; do not touch a real DB or network.
  - Test 1 — **DB record contains all 14 required fields**: call the handler with a synthetic `context` dict; assert `db.session.add` was called with an object whose attributes cover every column in the `failed_tasks` model (`celery_task_id`, `task_name`, `task_args`, `task_kwargs`, `error_message`, `error_trace`, `failure_count`, `failed_at`, `alerted_at`, `status`, `resolved_at`, `resolved_by` — all non-null columns set correctly, nullables left `None`).
  - Test 2 — **alert dispatched exactly once**: verify the ops-alert function is called exactly `1` time with a payload that does NOT contain the full stack trace string or raw `args`/`kwargs` values.
  - Test 3 — **DB failure does not suppress alert**: patch `db.session.add` to raise `SQLAlchemyError`; assert the alert dispatch is still called once (i.e., alert is sent regardless of DB outcome).
  - Test 4 — **alert failure does not suppress DB write**: patch the alert function to raise an exception; assert `db.session.add` and `db.session.commit` were still called.
  - Use `pytest.raises` or `assert mock.call_count` patterns — no try/except swallowing in test body.
- **Acceptance criteria**: REQ-006 (DLQ + alert on exhaustion); REQ-015 (no silent swallowing).
- **Verify**: `pytest tests/unit/test_dlq_handler.py -v`

---

### T-033: Unit tests for Celery task modules COMP-007–010 (new) — COMP-007/008/009/010

- **Purpose**: Verify success path, transient-failure retry behavior, retry counter increment, max-retries exhaustion routing to DLQ, and immediate raise on non-transient errors — for all four task modules.
- **File(s)**: `tests/unit/test_email_tasks.py`, `tests/unit/test_servicenow_tasks.py`, `tests/unit/test_retry_tasks.py`, `tests/unit/test_ctask_tasks.py`
- **Dependencies**: T-014, T-015, T-016, T-017
- **Key notes**:
  - All four files follow the same five-scenario template; parametrize or copy per module to keep failures localized.
  - **Setup**: use `@pytest.fixture` that patches the underlying service call (email sender, ServiceNow client, DB query, ctask API) and patches `dlq_handler` to a `MagicMock`.
  - Test 1 — **success path**: mock service returns normally; assert task return value is truthy/expected shape; assert `self.retry` never called; assert DLQ never invoked.
  - Test 2 — **transient failure triggers retry**: mock service raises a transient exception (e.g., `ConnectionError`); assert `self.retry` is called with `countdown=30`; assert `exc` argument matches raised exception.
  - Test 3 — **retry count increments**: simulate `self.request.retries = 2`; invoke task; assert retry is called with `countdown=30` (not a different value).
  - Test 4 — **max_retries exhaustion → DLQ**: set `self.request.retries = 3` (== `max_retries`); mock service raises; assert `self.retry` raises `MaxRetriesExceededError` which the task catches and routes to `dlq_handler`; assert DLQ mock called once.
  - Test 5 — **non-transient error raises immediately**: mock service raises a non-transient exception (e.g., `ValueError`); assert the exception propagates out of the task without calling `self.retry`.
  - Bind tasks with `task.apply()` using Celery's `ALWAYS_EAGER=True` test mode **or** call the underlying function directly with a mocked `self`; do NOT require a live broker.
  - Countdown value must be exactly `30` seconds in all retry assertions.
- **Acceptance criteria**: REQ-003, REQ-006 (min 3 retries, 30 s interval, DLQ on exhaustion).
- **Verify**: `pytest tests/unit/test_email_tasks.py tests/unit/test_servicenow_tasks.py tests/unit/test_retry_tasks.py tests/unit/test_ctask_tasks.py -v`

---

### T-034: Unit tests for `services/ctask_scheduler.py` (new) — COMP-012

- **Purpose**: Verify `get_status()` returns a structured dict within timing bounds both when the broker is available and unavailable, `force_check()` enqueues the correct task, and `start()`/`stop()` send the correct Celery control commands.
- **File(s)**: `tests/unit/test_ctask_scheduler.py`
- **Dependencies**: T-019 (modified ctask_scheduler.py must exist)
- **Key notes**:
  - Do NOT start a real broker or worker; mock `celery.control.inspect` and `run_ctask_assignment.delay`.
  - Test 1 — **`get_status()` broker available**: mock `inspect(timeout=2.0).active()` to return a dict with worker entries; assert return value is a dict with keys `status`, `workers_active`, `scheduled_jobs`, `broker_reachable`; assert `broker_reachable == True`; use `time.perf_counter` to assert total call time < 3 s.
  - Test 2 — **`get_status()` broker unavailable**: mock `inspect(timeout=2.0).active()` to raise `Exception` (simulating timeout); assert returned dict has `status == "degraded"` and `broker_reachable == False`; assert total call time < 5 s; assert no exception propagates.
  - Test 3 — **`force_check()` enqueues task**: mock `run_ctask_assignment.delay`; call `force_check()`; assert mock was called once with no required positional args (or the expected signature); assert returned dict contains a `task_id` field.
  - Test 4 — **`start()` sends correct control command**: mock `celery_app.control`; call `start()`; assert appropriate Celery control method was invoked (e.g., `broadcast` or `enable_events`).
  - Test 5 — **`stop()` sends correct control command**: same pattern for `stop()`.
  - Timing assertions must use wall-clock measurement (`time.perf_counter`), not mocked time.
  - Confirm zero `apscheduler` imports remain by asserting `"apscheduler"` not in `inspect.getfile(ctask_scheduler)` or by grepping the source in a setup fixture.
- **Acceptance criteria**: REQ-004 (Celery-backed scheduler interface); REQ-013 (`get_status()` ≤ 5 s when broker unavailable).
- **Verify**: `pytest tests/unit/test_ctask_scheduler.py -v`

---

### T-035: Unit tests for `utils/validators.py` (new) — COMP-015

- **Purpose**: Confirm `validate_{form}_fields` returns a field-name-keyed error dict for empty, null, and out-of-range inputs, and returns an empty dict for fully valid input.
- **File(s)**: `tests/unit/test_validators.py`
- **Dependencies**: T-024 (validators.py must exist)
- **Key notes**:
  - Import every `validate_*_fields` function exported from `utils/validators.py`; test each independently.
  - Test 1 — **empty string field**: pass `{field: ""}` for each required field; assert return dict contains that field key with a non-empty string value (the actionable error message).
  - Test 2 — **null/None field**: pass `{field: None}`; assert the field key appears in the returned error dict.
  - Test 3 — **out-of-range value** (for any numeric/length-bounded field): pass a value outside defined bounds; assert the returned message references the valid range (e.g., contains the boundary values).
  - Test 4 — **fully valid input**: pass a complete, valid payload; assert return value equals `{}` (empty dict — not `None`, not a falsy non-dict).
  - Test 5 — **multiple invalid fields simultaneously**: pass a dict with two invalid fields; assert both field keys are present in the returned error dict (not short-circuited after first failure).
  - Error messages must be strings; assert `isinstance(msg, str) and len(msg) > 0` for each.
- **Acceptance criteria**: REQ-016 (field-level actionable errors for each invalid field).
- **Verify**: `pytest tests/unit/test_validators.py -v`

---

### T-036: Unit tests for `utils/rbac_errors.py` (new) — COMP-016

- **Purpose**: Verify `resolve_rbac_error` returns specific, role-identifying messages for every supported role/action combination, with no generic fallback text.
- **File(s)**: `tests/unit/test_rbac_errors.py`
- **Dependencies**: T-025 (rbac_errors.py must exist)
- **Key notes**:
  - Enumerate every `(user_role, required_role, action)` tuple supported by the implementation; test each one.
  - Test 1 — **non-generic message**: for every combination, assert the returned string does NOT equal a bare generic phrase (e.g., `"Permission denied"`, `"Access denied"`, `"Forbidden"` alone).
  - Test 2 — **role name present**: assert the returned message contains the `required_role` string literally (e.g., `"team_admin"` appears in the message when `required_role="team_admin"`).
  - Test 3 — **`user` attempting `team_admin` action**: call `resolve_rbac_error("user", "team_admin", <action>)`; assert the string `"team_admin"` appears in the result.
  - Test 4 — **action context present**: assert the returned message references or is specific to the `action` argument (i.e., same role pair with different actions returns different messages).
  - Test 5 — **return type**: assert every call returns `str`, not `None` or an exception.
  - Build a parametrized test using `@pytest.mark.parametrize` over the full combination matrix so adding new roles automatically triggers new test cases.
- **Acceptance criteria**: REQ-017 (auth failures identify specific missing role/privilege; no generic 403 message).
- **Verify**: `pytest tests/unit/test_rbac_errors.py -v`

---

### T-037: Unit tests for `services/audit_service.py` (new) — COMP-014

- **Purpose**: Verify the audit transaction service commits both writes on success, rolls back both on audit log failure (with exception re-raise), and performs a full rollback on mid-transaction DB failure.
- **File(s)**: `tests/unit/test_audit_service.py`
- **Dependencies**: T-026 (audit_service.py must exist)
- **Key notes**:
  - Mock `db.session` completely; do not use a real DB.
  - Test 1 — **both writes succeed → commit**: mock both the handover record write and audit log write to succeed; assert `db.session.commit()` called exactly once; assert `db.session.rollback()` never called.
  - Test 2 — **audit log write fails → rollback + handover not persisted + exception re-raised**: mock handover write to succeed but `audit_log` write to raise `SQLAlchemyError`; assert `db.session.rollback()` called; assert `db.session.commit()` NOT called; assert the exception propagates out of the service call (use `pytest.raises`).
  - Test 3 — **DB failure mid-transaction → full rollback**: mock `db.session.add` on the second call to raise `SQLAlchemyError`; assert `db.session.rollback()` called; assert no partial `commit()`.
  - Test 4 — **no silent swallowing**: for both failure tests, assert the caught exception type is re-raised (not swapped for a different type, not swallowed into a return value).
  - Use `unittest.mock.MagicMock` with `side_effect` to control call-by-call behavior on `db.session.add`.
  - Each test must be fully isolated; use `autouse` fixture to reset mock state between tests.
- **Acceptance criteria**: REQ-015 (atomic handover + audit log; partial commits prohibited; re-raise on failure).
- **Verify**: `pytest tests/unit/test_audit_service.py -v`

---

### T-038: Unit tests for `tests/config.py` (new) — COMP-019

- **Purpose**: Confirm test credential config reads from env vars when set, uses sentinel fallbacks only on localhost, and raises `ConfigurationError` before transmitting any credential when target is non-localhost with env vars unset.
- **File(s)**: `tests/unit/test_tests_config.py`
- **Dependencies**: T-010 (tests/config.py must be updated)
- **Key notes**:
  - Reload `tests.config` within each test after patching env vars (use `importlib.reload`) so module-level reads are re-evaluated.
  - Test 1 — **env vars set → values match**: set `TEST_SUPERADMIN_PASSWORD=s1`, `TEST_ADMIN_PASSWORD=a1`, `TEST_USER_PASSWORD=u1` in `os.environ`; reload module; assert each credential attribute equals the injected value.
  - Test 2 — **env vars unset + localhost target → sentinel fallbacks**: unset all three env vars; set target host to `localhost` (or `127.0.0.1`); reload module; assert credential attributes equal the defined sentinel strings (not `None`, not empty).
  - Test 3 — **env vars unset + non-localhost target → `ConfigurationError` before credential used**: unset all three env vars; set target host to a non-localhost value (e.g., `"10.0.0.1"`); assert reloading the module (or accessing credentials) raises `ConfigurationError` (or the specific exception type defined in `tests/config.py`).
  - Test 4 — **sentinel values are not valid production credentials**: assert sentinel fallback strings do NOT match the format of real credentials (e.g., are clearly placeholder strings such as `"test-only-localhost-sentinel"`).
  - Use `patch.dict(os.environ, ..., clear=True)` to guarantee no ambient env leakage between tests.
- **Acceptance criteria**: REQ-007 (credentials from env vars; no valid non-localhost literals in source; abort before credential transmitted to non-localhost).
- **Verify**: `pytest tests/unit/test_tests_config.py -v`

---

### T-039: Integration tests (new) — COMP-003/012/013/014

- **Purpose**: Validate end-to-end Celery task dispatch/execution with a live Redis broker, scheduler service behavior with live and stopped Redis, `force_check()` queue latency, handover transaction atomicity under injected failure, and CI security stage behavior with clean and CVE-injected dependencies.
- **File(s)**: `tests/integration/test_celery_integration.py`, `tests/integration/test_scheduler_integration.py`, `tests/integration/test_handover_integration.py`, `tests/integration/test_ci_security.py`
- **Dependencies**: T-021, T-027, T-034, T-037
- **Key notes**:
  - **Infrastructure requirement**: all Celery integration tests require a real Redis instance; gate with a `pytest.mark.integration` marker and a `REDIS_URL` env var presence check — skip cleanly if Redis unavailable.
  - `test_celery_integration.py`:
    - **Dispatch + execute + result**: dispatch a lightweight test task to the live Redis broker; assert result state becomes `SUCCESS` within 10 s using `AsyncResult.get(timeout=10)`.
    - **`get_status()` with live worker**: start a test worker in a subprocess (or use `celery worker --pool=solo` via `subprocess.Popen`); call `get_status()`; assert `broker_reachable == True` and `workers_active >= 1`.
    - **`get_status()` with Redis stopped**: stop Redis (or point broker URL to a dead port); call `get_status()`; assert `status == "degraded"` and `broker_reachable == False`; assert total time < 5 s.
    - **`force_check()` latency**: call `force_check()`; poll `celery_app.control.inspect().reserved()` every 100 ms; assert task appears in queue within 1 s.
  - `test_handover_integration.py`:
    - **Both-success path**: call the audit service with a valid handover payload against a test DB; assert both rows committed; assert no exception.
    - **Injected audit failure rollback**: patch the audit log write to raise mid-transaction; assert the handover record is NOT present in the DB after the call; assert exception propagated.
  - `test_ci_security.py`:
    - **Clean deps pass**: run `pip-audit -r requirements.txt` in a subprocess; assert exit code 0.
    - **Injected CVE blocks**: add a known-vulnerable pinned package to a temp requirements file; run `pip-audit`; assert exit code non-zero.
  - Use `pytest-timeout` (or `@pytest.mark.timeout(N)`) on all timing-sensitive tests.
  - Tear down subprocesses and temp files in `finally` blocks or `autouse` fixtures.
- **Acceptance criteria**: REQ-003, REQ-005, REQ-008, REQ-013, REQ-015.
- **Verify**: `pytest tests/integration/ -v -m integration --timeout=30`

---

### T-040: E2E test scenarios (new) — All components

- **Purpose**: Validate six named end-to-end behavioral scenarios covering healthy startup, fail-fast startup, job deduplication across workers, form field validation, RBAC rejection, and DLQ routing after retry exhaustion — all exercised against a fully composed environment.
- **File(s)**: `tests/e2e/test_e2e_scenarios.py`
- **Dependencies**: T-039 (integration tests must pass first)
- **Key notes**:
  - All six scenarios require `docker-compose up` to be running; gate with `pytest.mark.e2e` marker and a `E2E_BASE_URL` env var; skip cleanly if absent.
  - **Scenario 1 — Healthy container startup**: `docker-compose up web`; poll `GET /health` every 500 ms for up to 15 s; assert HTTP 200 received; assert `docker-compose logs web` contains exactly one Gunicorn worker-startup log line matching `"worker with pid"`.
  - **Scenario 2 — Missing-secret fail-fast**: launch `web` service with `SECRETS_MANAGER_SECRET_ARN` unset; assert container exits within 10 s; assert exit code non-zero; assert no `0.0.0.0:5000` socket appears in `ss -tlnp` output during that window.
  - **Scenario 3 — Multi-worker job deduplication**: scale Celery workers to 2 (`docker-compose up --scale worker=2`); wait one full beat interval plus 5 s; collect logs from both worker containers; assert the target task's `"Executing task"` log line appears exactly once across both containers for the interval under test.
  - **Scenario 4 — Form submission with invalid fields**: `POST /handover/submit` with two known-invalid fields (one empty, one out-of-range); assert HTTP 400; assert response JSON body has key `"errors"` whose value is a dict containing both field names as keys with non-empty string values.
  - **Scenario 5 — `user`-role approval attempt returns 403 with role name**: authenticate as a `user`-role account; attempt an action requiring `team_admin`; assert HTTP 403; assert response JSON body has key `"error"` whose string value contains `"team_admin"` literally.
  - **Scenario 6 — DLQ routing after 3 exhausted retries**: trigger a task that always fails (inject via a feature flag or test endpoint); wait for 3 retry cycles (3 × 30 s = 90 s max, poll at 10 s intervals); assert one row exists in `failed_tasks` with `status == "failed"` and `failure_count == 3`; assert `alerted_at` is not null (alert was dispatched).
  - Each scenario must be fully independent; run them in sequence (not parallel) to avoid Docker port conflicts.
  - Capture `docker-compose logs` artifacts on failure for CI debugging.
  - Scenario 6 requires a real Celery worker, beat, and Redis; assert the test skips gracefully if the full stack is not running.
- **Acceptance criteria**: REQ-001, REQ-002, REQ-005, REQ-006, REQ-014, REQ-015, REQ-016, REQ-017.
- **Verify**: `E2E_BASE_URL=http://localhost:5000 pytest tests/e2e/test_e2e_scenarios.py -v -m e2e --timeout=120`

## Execution Waves

| Wave | Tasks | Dependencies Satisfied | Verify Command |
|---|---|---|---|
| **0** | T-001, T-003, T-004, T-005, T-007, T-008, T-010, T-011, T-024, T-025, T-026, T-028 | None — all independent foundations | `python -m py_compile startup_checks.py celery_app.py utils/validators.py utils/rbac_errors.py services/audit_service.py && echo PASS` |
| **1** | T-002, T-006, T-009, T-012, T-027, T-030, T-031, T-035, T-036, T-037, T-038 | `.gitignore` rules (T-001); CI tools file (T-005); startup + Gunicorn scripts (T-007, T-008); Celery factory (T-011); validators, RBAC resolver, audit service, test creds (T-010, T-024–T-026) | `git log --all -- '*.pdf' '*.docx' '*.xlsx' '*.pptx' \| wc -l` (expect 0); `pytest tests/unit/test_startup_checks.py tests/unit/test_celery_app.py tests/unit/test_validators.py tests/unit/test_rbac_errors.py tests/unit/test_audit_service.py tests/unit/test_config.py -q` |
| **2** | T-013 | Tasks package init (T-012); Celery factory (T-011) | `python -c "from tasks.dlq_handler import dlq_on_failure; print('ok')"` |
| **3** | T-014, T-015, T-016, T-017, T-022, T-032 | DLQ handler (T-013) | `pytest tests/unit/test_dlq_handler.py -q`; `flask db migrate --dry-run -m add_failed_tasks_table` (expect 14-column migration preview) |
| **4** | T-018, T-019, T-023, T-033 | All 4 task modules (T-014–T-017); `failed_tasks` migration (T-022); migration registry (T-003) | `python -c "import celeryconfig; assert len(celeryconfig.beat_schedule)==4"`; `grep -c 'apscheduler' services/ctask_scheduler.py` (expect 0); `pytest tests/unit/test_tasks.py -q` |
| **5** | T-020, T-021, T-029, T-034 | Beat config (T-018); APScheduler removed (T-019); `start.sh` (T-009) | `docker compose config -q`; `pytest tests/unit/test_ctask_scheduler.py -q`; verify route shapes: `curl -s http://localhost:5000/scheduler/status \| python -m json.tool` |
| **6** | T-039 | Full orchestration (T-021); scheduler routes (T-020); handover integration (T-027); audit service tests (T-037); scheduler unit tests (T-034) | `pytest tests/integration/ -q` |
| **7** | T-040 | All integration tests passing (T-039) | `pytest tests/e2e/ -q` |

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| **`git filter-repo` history rewrite (T-002) corrupts repo or diverges active forks** | High — permanent data loss; all clone/fork SHAs invalidated | Medium | Run on a bare clone first; coordinate a repo freeze window; force-push to all remotes atomically; notify all contributors to re-clone before T-002 merges |
| **Task deduplication failure (REQ-005): multiple workers execute same Beat-dispatched task** | High — duplicate emails, duplicate ServiceNow tickets, duplicate DB writes | Medium | Enforce single Beat process per deployment (T-021 must not run multiple `beat` replicas); add idempotency keys or DB-level unique constraints on task side-effects; validate in T-040 E2E deduplication scenario |
| **Redis single point of failure silently drops all scheduled jobs** | High — all 4 scheduled job types halt with no alert | Medium | Add Redis health check to `startup_checks.py` (T-007); configure `get_status()` degraded response to surface in monitoring; document restart procedure in T-029 |
| **Celery `inspect(timeout=2.0)` does not reliably bound HTTP response time (REQ-013)** | Medium — HTTP thread blocked beyond 5 s SLA | Medium | Wrap `inspect()` call in `concurrent.futures.ThreadPoolExecutor` with hard 4.5 s wall-clock timeout; cover with T-034 broker-unavailable timing test |
| **Committed-secret detection (T-006) blocks CI on existing history secrets** | High — all MRs blocked until history is cleaned; blocks T-002 prerequisite ordering | Low–Medium | Run secret scan locally against full history before enabling the CI gate; sequence T-006 merge after T-002 history clean is confirmed |
| **APScheduler → Celery cutover drops in-flight jobs (T-019 deployed to live system)** | Medium — jobs executing at deployment moment are lost | Low | Deploy during a scheduled maintenance window; confirm no APScheduler jobs are running before cutover; T-019 must verify zero `apscheduler` imports before merge |
| **`failed_tasks` table missing at DLQ handler deploy time (T-013 before T-022 applied)** | High — DLQ handler raises `OperationalError`; retry exhaustion silently swallowed | Medium | T-022 migration is in Wave 3 (same wave as T-013's consumers); enforce migration runs before app deploy in `start.sh` via Alembic `upgrade head` gate |
| **Test credential env vars absent in existing CI pipelines (T-010)** | Medium — all existing test suite runs fail after T-010 merges | High | Pre-populate `TEST_SUPERADMIN_PASSWORD`, `TEST_ADMIN_PASSWORD`, `TEST_USER_PASSWORD` as masked CI variables before T-010 lands; T-038 covers the localhost-guard path |
| **Branch protection applied too late (T-028 deferred past Wave 0)** | Medium — unreviewed code merges during implementation window | Medium | T-028 has no dependencies; treat it as a Day 0 prerequisite; complete before any implementation task merges to main |
| **DLQ alert–DB write isolation failure (T-013): exception in alert path swallows DB write** | Medium — failed task record not persisted; ops unaware of exhausted retries | Medium | Unit test T-032 explicitly injects alert failure and asserts DB write completes; code review must confirm try/except wraps only the alert call, not the DB write |
| **Celery Beat multi-instance footgun in `docker-compose.yml` (T-021)** | High — duplicate task dispatch if Beat is scaled | Low | Explicitly document `replicas: 1` constraint on beat service; add E2E guard in T-040 deduplication scenario; CI `docker compose config` lint in Wave 5 verify step |
| **Alembic migration conflicts from parallel feature branches** | Medium — autogenerate produces conflicting revision heads | Low | Enforce single active migration branch policy in T-003 registry; squash before merge; `flask db heads` must return exactly one head |

---

## Non-Functional Hardening

**API Boundary**
- [ ] `/scheduler/*` routes: all 400/403 responses return structured JSON (T-020 errorhandlers)
- [ ] `/handover/submit`: field validation gate executes before any DB write (T-027 ordering enforced)
- [ ] No endpoint exposes raw Python exception messages in response body

**Service Layer**
- [ ] `audit_service.py`: null session handle raises, not silently no-ops
- [ ] `ctask_scheduler.py`: `get_status()` returns structured degraded dict — never raises — on broker unavailability
- [ ] `dlq_handler.py`: alert dispatch wrapped independently; DB write not contingent on alert success
- [ ] All new service functions have defined return types; no implicit `None` returns on partial success

**Data Access**
- [ ] `failed_tasks` table: composite indexes on `(status)` and `(task_name)` as specified; `celery_task_id` UNIQUE constraint prevents duplicate DLQ writes
- [ ] Audit transaction (T-026): explicit `session.begin()` / `session.rollback()` — not reliant on implicit transaction scope
- [ ] Alembic migration (T-022): `upgrade` and `downgrade` paths both verified; `downgrade` drops table cleanly

**Error Handling**
- [ ] `startup_checks.py`: each failure path emits a named-field error to `stderr` before `sys.exit(1)`
- [ ] All Celery tasks: non-transient errors (e.g., `ValueError`) raise immediately without retry
- [ ] `resolve_rbac_error()`: covers every supported role/action combination; no fallthrough to generic string

**Logging**
- [ ] Celery task logs include `task_id`, `task_name`, `attempt_number` — no user PII
- [ ] `dlq_handler.py`: `error_trace` stored in DB but excluded from alert payload (spec requirement)
- [ ] Gunicorn access log format (T-008): does not log `Authorization` headers or query-string credentials
- [ ] Startup checks log which named secret or DB host failed — not the secret value

**Security**
- [ ] `tests/config.py`: non-localhost guard fires before any credential is transmitted (T-010)
- [ ] `requirements-ci.txt` kept separate from production `requirements.txt`; CI tools not installable in production image
- [ ] `pip-audit` CVE scan is a **blocking** merge gate (T-006); Bandit is informational unless P0 severity
- [ ] `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` read exclusively from env vars; never hardcoded (T-011)

**Tests**
- [ ] Every new module has a corresponding unit test task (T-030–T-038)
- [ ] Integration tests cover live Redis path and Redis-stopped degraded path (T-039)
- [ ] E2E tests cover missing-secret fast-fail, DLQ exhaustion, and multi-worker deduplication (T-040)
- [ ] All tests runnable with `pytest` from repo root with no additional setup beyond env vars

---

## Post-Implementation Checklist

- [ ] All pre-existing tests pass without modification (no regressions from APScheduler removal or credential refactor)
- [ ] All new unit tests pass (T-030–T-038)
- [ ] All integration tests pass with live Redis (T-039)
- [ ] All E2E scenarios pass including failure paths (T-040)
- [ ] `git log --all -- '*.pdf' '*.docx' '*.xlsx' '*.pptx'` returns zero commits
- [ ] `docker compose up` starts 4 services (web, worker, beat, redis); web binds port 5000; Beat dispatches on schedule
- [ ] `docker compose up` with a missing required secret: container exits < 10 s, non-zero, port never bound
- [ ] `GET /scheduler/status` response matches approved shape with all required fields
- [ ] `POST /handover/submit` with invalid fields returns HTTP 400 with field-keyed error map
- [ ] `POST /handover/submit` with insufficient role returns HTTP 403 with role-identifying message
- [ ] All four Celery task types appear in `celeryconfig.py` Beat schedule with correct intervals
- [ ] `grep -r 'apscheduler' .` (excluding `.git`) returns no matches
- [ ] `flask db heads` returns exactly one head revision
- [ ] `migrations/README.md` contains entry for `failed_tasks` migration with `pending` status
- [ ] CI security stage runs on every MR; pip-audit blocks merge on any known CVE
- [ ] Branch protection on main: direct push blocked; minimum 1 approval enforced
- [ ] `CLAUDE.md` and `CONTRIBUTING.md` reflect Celery architecture and env-var credential pattern
- [ ] No NFR hardening item left unchecked

---

## Milestones

| Milestone | Waves Complete | Completion Criteria |
|---|---|---|
| **M1 — Security & Foundation** | 0–1 | Binary files purged from git history and `.gitignore` blocking; CI security stage live and blocking on CVE; branch protection enforced; `startup_checks.py` + `start.sh` + `gunicorn.conf.py` syntactically valid; test credentials reading from env vars; all Wave 1 unit tests green |
| **M2 — Celery Core** | 2–3 | Celery app factory, tasks package, DLQ handler, and all 4 task modules exist and import cleanly; `failed_tasks` migration generated and verified against 14-column schema; `migrations/README.md` updated; all DLQ and task unit tests pass |
| **M3 — Orchestration Complete** | 4–5 | Beat schedule maps all 4 job types; APScheduler fully removed from scheduler service (zero imports); Docker Compose defines all 4 services with correct commands; scheduler routes preserve all existing paths and response shapes; `CLAUDE.md`/`CONTRIBUTING.md` updated; all unit tests pass |
| **M4 — Verified & Deployable** | 6–7 | All integration tests pass with live Redis including degraded-broker path; all E2E scenarios pass (healthy startup, missing-secret fast-fail, deduplication across 2 workers, field validation, RBAC 403, DLQ routing); zero regressions in pre-existing suite; deployment sign-off granted |


---
## Interrogation Summary

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
