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