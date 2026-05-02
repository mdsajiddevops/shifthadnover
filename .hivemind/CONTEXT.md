# HiveMind Development Context
**Ticket:** CTCOAMSHM-7

Phase 2 artifacts for CTCOAMSHM-7: Realtime infra + handover draft auto-save.


---
## Problem Specification

# Functional Specification: ShiftOps Archaeology & Hardening

---

## Meta

| Field | Value |
|-------|-------|
| **Ticket ID** | CTCOAMSHM-7 |
| **Project Name** | ShiftOps (Shifthandover) |
| **Creation Date** | 2026-05-02 |
| **Status** | In Review |
| **Branch Scope** | Archaeology & Hardening |
| **Spec Author** | Generated from interrogation session |

---

## Problem Statement

### Summary
Resolve 8 medium-severity production-readiness gaps in ShiftOps spanning infrastructure, security, process, and documentation hygiene.

### User Problem
Development and operations teams cannot safely scale, deploy, or audit the ShiftOps application: the production entry point uses a development-mode server, scheduled tasks co-run with web workers causing duplicate task execution on scale-out, test credentials are hardcoded in source code, and migration history is undocumented — creating risk of schema drift, security exposure, and undetected operational failures across environments.

### Business Value
Closing these gaps reduces the attack surface from credential leakage and unscanned CVEs, removes the architectural constraint blocking safe multi-worker deployment, and enforces a reviewable, auditable change pipeline — collectively lowering the probability and blast radius of a security incident or production outage caused by unreviewed or misconfigured code.

---

## Requirements

| ID | Type | Priority | Description | Depends On |
|----|------|----------|-------------|------------|
| REQ-001 | Functional | P0 | The system shall execute all scheduled background tasks — including notification digests, third-party service polling operations, and retry operations — in a process isolated from the web request-handling process, such that running multiple concurrent web-serving workers does not produce duplicate task executions. | — |
| REQ-002 | Functional | P0 | The system shall resolve all test suite authentication credentials from named environment variables; a localhost-only fallback to documented default values shall be permitted exclusively for individual developer convenience and shall not activate in any shared, staging, or production environment. | — |
| REQ-003 | Functional | P0 | The system shall serve all production HTTP traffic through a production-grade WSGI-compatible server with a request timeout of at least 120 seconds; the development-mode server shall not be used as the production entry point under any condition. | — |
| REQ-004 | Functional | P1 | The system shall maintain a human-readable document within the repository that unambiguously categorises every database migration script as one of: (1) applied to production, (2) superseded — must not be re-applied, or (3) environment-specific; all future schema changes shall be introduced exclusively via the versioned migration toolchain. | — |
| REQ-005 | Functional | P0 | The system's CI/CD pipeline shall enforce a dedicated security scanning stage that completes before any build artifact is produced, comprising: (1) a dependency vulnerability scan that fails the pipeline on any known CVE and persists a machine-readable scan report as a pipeline artifact, (2) Python static application security analysis, and (3) full git-history scanning for committed secrets. | — |
| REQ-006 | Functional | P1 | The system's source repository shall contain no tracked binary documentation files (portable document, word processing, spreadsheet, or presentation formats); these file-type patterns shall be permanently excluded from source tracking via repository-level ignore configuration. | — |
| REQ-007 | Functional | P1 | The system's source repository shall require a minimum of one peer-reviewer approval on every merge request targeting the protected main branch; the merge request author shall be prohibited from satisfying the approval requirement through self-approval. | — |
| REQ-008 | Functional | P0 | The system shall validate all user-submitted input on submission; for any validation failure the system shall return a response containing a specific, human-readable error message that identifies the offending field and the nature of the constraint violation. | — |
| REQ-009 | Non-Functional | P0 | The background task subsystem shall guarantee at-most-once execution per trigger event; zero duplicate task executions shall be observed when the web-serving process is scaled to three or more concurrent workers, measurable by task execution log count matching trigger count over a 24-hour observation window. | REQ-001 |
| REQ-010 | Non-Functional | P1 | Scheduled tasks that encounter a transient external-service failure shall automatically retry up to 3 times with a minimum 30-second delay between each attempt before recording a terminal failure state; retry count and final status shall be observable without manual log parsing. | REQ-001 |
| REQ-011 | Non-Functional | P0 | The application shall terminate immediately at startup with a logged, human-readable error message when any required configuration value (credentials, database reachability) is absent or unreachable; it shall not enter a partially operational or silently degraded state. | — |
| REQ-012 | Non-Functional | P1 | A failure of any non-critical background instrumentation service (e.g., background worker status queries) shall not propagate to the web-serving tier; core application routes shall return HTTP 200 and remain fully functional during an instrumentation outage, measurable by monitoring core route responses during a simulated instrumentation failure. | REQ-001 |
| REQ-013 | Non-Functional | P0 | Authentication credentials (application, test, and service-account) shall never appear in source code, git commit history, CI/CD pipeline logs, or any pipeline-produced artifact; the sole permitted exception is an explicitly documented, localhost-only developer fallback value; violations shall be automatically detectable by the pipeline secret-detection stage. | REQ-005 |

---

## Acceptance Criteria

### REQ-001 — Isolated Background Task Execution

- **AC-001a** *(Happy Path)*: Given the application is running with three concurrent web-serving workers and the background task process is running in a separate isolated process, when a scheduled email digest task is triggered once, then exactly one completion record is written to the task execution log and exactly one email is dispatched; no duplicate records are observed.
- **AC-001b** *(Error Path)*: Given the background task process is unavailable when a scheduled trigger fires, when the web-serving workers continue handling HTTP requests, then no task execution is attempted within the web-serving process, HTTP request handling continues without error, and the triggered task remains in a pending or queued state until the background process recovers.

### REQ-002 — Environment Variable Credentials

- **AC-002a** *(Happy Path)*: Given the named environment variables for superadmin, admin, and user test credentials are populated in the CI/CD environment, when the test suite runs, then all authentication-dependent tests pass using the environment variable values and no credential literal appears in pipeline stdout, log output, or saved test artifacts.
- **AC-002b** *(Error Path)*: Given the named environment variables are absent and the test runner is not executing on a localhost environment, when the test suite initialises, then the suite fails immediately with a clear error message identifying which environment variables are missing rather than silently substituting insecure default values.

### REQ-003 — Production-Grade WSGI Server

- **AC-003a** *(Happy Path)*: Given the application is started via the designated production entry-point, when the first inbound HTTP request arrives, then the request is served successfully; the running process is identifiable as the production WSGI server (not the development server); and a request requiring at least 90 seconds of processing time is not terminated prematurely.
- **AC-003b** *(Error Path)*: Given the production entry-point is invoked but a required system resource (e.g., the target port is already bound) is unavailable, when the server process attempts to start, then the process exits with a non-zero exit code and writes a human-readable error message to the process log; the development-mode server is not invoked as a fallback.

### REQ-004 — Migration Documentation

- **AC-004a** *(Happy Path)*: Given the migration documentation file exists at its expected repository path, when a developer reads it, then every migration script in the repository is unambiguously classified as "applied to production," "superseded — do not re-apply," or "environment-specific," with no script left uncategorised.
- **AC-004b** *(Error Path)*: Given a developer locates a migration script documented as "superseded — do not re-apply," when they consult the document before executing the script, then the documentation provides an explicit warning and identifies which versioned migration supersedes it, enabling the developer to avoid accidental re-application.

### REQ-005 — Pipeline Security Scanning

- **AC-005a** *(Happy Path)*: Given a commit introduces no new CVE-affected dependencies and contains no credential literals in git history, when the CI/CD pipeline runs, then the security scanning stage passes, a dependency scan artifact is saved to the pipeline, and the build stage proceeds.
- **AC-005b** *(Error Path — CVE introduced)*: Given a dependency with a published CVE is added to the project's dependency manifest, when the CI/CD pipeline runs, then the dependency scan step fails, the pipeline does not advance to the build stage, and the artifact identifies the affected package name, version, and CVE identifier.
- **AC-005c** *(Error Path — committed secret)*: Given a credential literal is present in any commit in the repository history, when the pipeline runs the secret-detection step, then the step fails, the pipeline does not advance to the build stage, and the finding is reported with sufficient context (file reference) to locate and remediate the exposure.

### REQ-006 — Binary File Exclusion

- **AC-006a** *(Happy Path)*: Given the repository ignore configuration has been committed with binary documentation file patterns, when a developer clones the repository from scratch, then no files matching *.pdf, *.docx, *.doc, *.xlsx, or *.pptx patterns are present in the working tree.
- **AC-006b** *(Boundary — attempted add)*: Given a developer attempts to stage a binary documentation file for commit, when the version control tooling evaluates the staged files, then the file is excluded by the ignore rules and does not appear in the changeset to be committed.

### REQ-007 — Merge Request Approval Enforcement

- **AC-007a** *(Happy Path)*: Given a merge request targeting the main branch has been approved by at least one peer reviewer who is not the author, when the author initiates a merge, then the merge is permitted and completes.
- **AC-007b** *(Error Path — no approval)*: Given a merge request is opened by an author who has repository merge rights, when the author attempts to merge without any peer-reviewer approval, then the merge is blocked and the platform reports that one approval is required before merging is permitted.
- **AC-007c** *(Error Path — self-approval)*: Given a merge request is open, when the author attempts to approve their own merge request, then the approval is rejected and does not increment the approval count toward the required threshold.

### REQ-008 — Input Validation and Error Messages

- **AC-008a** *(Happy Path)*: Given a user submits a fully valid form with all required fields populated within their permitted ranges, when the system processes the submission, then the operation proceeds without validation errors and the data is persisted.
- **AC-008b** *(Error Path — empty required field)*: Given a user submits a form with a required field left empty, when the system validates the input, then the response contains an error message identifying the specific empty field as required; no partial record is persisted.
- **AC-008c** *(Error Path — null or out-of-range value)*: Given a user submits a field with a null value or a value outside its permitted range, when the system validates the input, then the response contains an error message specifying the field name and the constraint that was violated.

### REQ-009 — Scheduled Task Deduplication

- **AC-009a** *(Happy Path)*: Given three concurrent web-serving workers and one background task worker, when a scheduled email digest trigger fires exactly once over a 24-hour window, then the task execution log records exactly one completion event corresponding to that trigger; no duplicate completion records are present.
- **AC-009b** *(Error Path — worker restart mid-execution)*: Given the background task worker restarts while a task is partially executed, when the task resumes, then no duplicate execution record is created and the task either completes cleanly or records a single terminal failure state.

### REQ-010 — Scheduled Task Retry Behaviour

- **AC-010a** *(Happy Path — recovery on retry)*: Given a scheduled task encounters a transient external service error on its first attempt, when the retry policy activates, then the task retries up to 3 times at minimum 30-second intervals; upon recovery of the external service the task completes and records a single success state.
- **AC-010b** *(Error Path — retries exhausted)*: Given a scheduled task exhausts all 3 retry attempts without success, when the final retry fails, then the task transitions to a terminal failed state that is observable without manual log parsing and no further automatic retry is attempted.

### REQ-011 — Startup Failure Behaviour

- **AC-011a** *(Happy Path)*: Given all required configuration values are present and the database is reachable, when the application process starts, then it enters the running state and begins accepting traffic within the normal startup window.
- **AC-011b** *(Error Path)*: Given a required environment variable is absent at process start, when the application attempts to initialise, then the process exits with a non-zero exit code and writes a human-readable log message identifying the missing variable by name; the process does not continue to a partially running state.

### REQ-012 — Non-Critical Service Degradation Isolation

- **AC-012a** *(Happy Path)*: Given all background instrumentation services are operational, when a user navigates to core application pages, then all pages load successfully and instrumentation data is visible.
- **AC-012b** *(Error Path)*: Given the background worker status instrumentation endpoint is unavailable, when a user navigates to core application pages, then all core routes return HTTP 200 and function correctly; only the instrumentation-specific UI element reflects the degraded state; no error is propagated to the user for core functionality.

### REQ-013 — Credential Absence from Source and Logs

- **AC-013a** *(Happy Path)*: Given the repository contains only environment variable references for credentials (with documented localhost-only fallbacks), when the secret detection stage runs against the full git history, then zero credential findings are reported and the stage passes.
- **AC-013b** *(Error Path)*: Given a developer accidentally commits a credential literal to any branch, when the CI/CD pipeline runs, then the secret detection stage fails, the pipeline is blocked from producing build artifacts, and the finding is reported with sufficient context to locate and remediate the exposure.

---

## Constraints

### Performance
- The application shall support steady-state traffic measured in the order of thousands of HTTP requests per day. No formal SLA, P99 latency target, or peak RPS figure has been established for this branch; standard caching and database indexing are considered sufficient for the stated load.
- Scheduled tasks that fail transiently shall complete within a maximum resolution window of approximately 90 seconds from first failure to final retry (1 initial attempt + 3 retries at ≥ 30-second intervals).
- No load testing or performance benchmarking is required as part of this hardening branch.

### Security
- Credentials (application, test, and service-account) shall never be stored in plain text in source code, with the sole permitted exception of explicitly documented localhost-only developer fallback values that do not activate in shared or production environments.
- All declared project dependencies shall be scanned for known CVEs on every CI/CD pipeline run; any pipeline run introducing a newly CVE-affected dependency shall be blocked from producing a build artifact.
- The full git commit history shall be scanned for committed secrets on every CI/CD pipeline run without exception.
- Python application source code shall be subject to static security analysis on every CI/CD pipeline run.
- Direct commits to the main branch shall be blocked; all changes must pass through a merge request with at least one qualifying peer-reviewer approval.
- Audit-critical operations (e.g., handover form submission) shall never silently fail or produce a partial success state; each operation shall either complete fully or raise a recorded exception that triggers the defined retry or abort strategy.
- The existing session token validation mechanism (per-request validation against the `session_tokens` table, administrator-forced logout capability) shall remain intact and unmodified.

### Compatibility
- This branch introduces no changes to existing route contracts, URL structures, request or response schemas, session formats, RBAC role definitions, or database table schemas. All changes are internal infrastructure hardening.
- The two-path authentication model (SSO primary, local login fallback) is preserved without modification. Existing authenticated sessions shall remain valid across the deployment boundary.
- The existing four-tier RBAC role hierarchy (`super_admin` → `account_admin` → `team_admin` → `user`) and associated privilege boundaries are unchanged.

### Accessibility
Not applicable to this branch — no UI or front-end changes are introduced.

---

## Non-Goals

| Non-Goal | Rationale |
|----------|-----------|
| **Production credential rotation or adoption of a centralised secrets management system** | Environment variable injection from the deployment platform satisfies the current threat model. A dedicated vault service would introduce significant scope beyond this hardening branch and is not required to close the identified gaps. |
| **Jira project permission configuration or board reconfiguration** | The required service-account role upgrade is an external administrative action with no associated code change; it is tracked as an open item (see Dependencies) and resolved outside this branch. |
| **Load testing, performance benchmarking, or infrastructure provisioning for increased capacity** | This branch removes the architectural constraint blocking safe multi-worker deployment but does not include validation of scale-out behaviour beyond the duplicate-execution acceptance criterion. No SLA or latency target has been specified. |
| **Real-time audit log streaming or SIEM integration** | Audit-critical operations are logged at the application level; the delivery mechanism, retention policy, and integration with security monitoring infrastructure are out of scope for this branch. |
| **Replacement of the background task scheduler with a distributed workflow orchestration platform** | Current task volume and complexity do not require a dedicated orchestration system. The isolated background task worker approach satisfies present scaling requirements without that investment. |
| **New user-visible features of any kind** | This branch is exclusively production-readiness and security hardening. Zero new user-visible functionality shall be introduced. |

---

## Assumptions

| ID | Assumption | Risk if Wrong | Validation Needed Before Implementation? |
|----|-----------|--------------|------------------------------------------|
| A-001 | The message queue service backing the background task worker is continuously available and monitored in all deployed environments. A prolonged outage would cause task queues to back up, potentially resulting in delayed notifications or stale handover data — though no duplicate executions would occur. | **Medium** — Backlogged tasks could produce missed notifications or stale handover states; prolonged failure without alerting may go undetected. | **Yes** — Confirm that message queue uptime monitoring and alert thresholds are in place before scaling the web-serving tier beyond a single worker. |
| A-002 | All required environment variables (test credentials, application secrets) will be correctly populated in every non-localhost environment (CI, staging, production) prior to container startup. Misspelled or absent variables could cause test failures or silent use of insecure defaults in shared environments. | **Medium** — Insecure defaults in shared environments constitute a security exposure; missing variables cause startup failures that may not be immediately diagnosed. | **Yes** — A deployment verification runbook must be produced and validated against a staging environment before the first production deployment of this branch. |
| A-003 | Python static application security analysis provides sufficient coverage for the application's current threat model without requiring custom rule authoring or supplementary scanning tools. | **Low** — Mature tooling with broad coverage is used; combined with dependency scanning and secret detection, the pipeline provides reasonable composite security signal. | **No** — Proceed; revisit if the application's threat model materially changes. |
| A-004 | The external Jira administrator will complete the HiveMind service-account role upgrade to Developer on board 344407 within two weeks of this branch merging. | **Medium** — If unresolved, Jira issue correlation remains broken, potentially impeding sprint planning continuity and issue traceability. | **Yes** — Escalate to the Jira administrator if no confirmation is received within two weeks of merge. |
| A-005 | "Thousands of requests per day" represents the steady-state average traffic volume, not a burst or sustained peak figure. Standard caching and database indexing are assumed sufficient without additional infrastructure investment. | **Low** — No burst or spike scenario has been identified. If sustained peaks exceed 10× the stated average, caching and indexing assumptions may need revisiting. | **No** — Proceed; revisit if production monitoring reveals sustained peaks exceeding 10× the average. |
| A-006 | The failure-handling strategy classifications — abort on startup failure, retry on transient task failure, graceful degrade on non-critical instrumentation failure — are correctly scoped to their respective operations in the existing codebase. An incorrectly classified "non-critical" operation could silently fail without triggering retry or abort strategies. | **Medium** — A misclassified audit-critical operation could produce silent data loss that is not caught by automated means. | **Yes** — A dedicated code review pass verifying each task and startup check carries the correct failure strategy must be completed as part of merge request review before this branch is merged. |
| A-007 | A second team member will join within six months, at which point the merge request approval rule becomes enforceable as a genuine peer-review gate rather than a formality for a single-developer project. | **Low** — The rule is configured and active from the point of enforcement regardless of team size; it provides immediate protection against accidental self-merges. | **No** — No action required; revisit rule configuration only if team structure changes significantly. |

---

## Edge Cases

| Scenario | Expected Behaviour | Related Requirement(s) |
|----------|--------------------|------------------------|
| **Empty or null required field submitted** | The system validates the submission before any data is persisted; the response identifies the specific field as empty or null and states what is required. No partial record is created. | REQ-008 |
| **Required environment variable absent at application startup** | The process terminates immediately with a non-zero exit code and a human-readable log message naming the missing variable; the application does not enter a degraded running state; no insecure default value is used in a non-localhost environment. | REQ-002, REQ-011 |
| **Third-party service (e.g., ServiceNow, Jira) unreachable during a scheduled task** | The task records the transient failure and is automatically retried up to 3 times at minimum 30-second intervals. If all retries are exhausted the task is recorded in a terminal failed state that is observable without manual log parsing. Core HTTP request handling remains unaffected. | REQ-001, REQ-010 |
| **Background task worker unavailable when a scheduled trigger fires** | The task enters a pending or queued state in the task store. No execution is attempted within the web-serving process. HTTP request handling continues normally. When the background worker recovers the task is dequeued and executed exactly once. | REQ-001, REQ-009 |
| **Background worker status instrumentation unreachable during a web request** | The web-serving tier handles the request normally; core routes return HTTP 200 and function correctly. Only the instrumentation-specific UI component reflects the degraded state; no error is propagated to the user for any core feature. | REQ-012 |
| **Developer attempts to commit a binary documentation file** | The repository ignore configuration excludes the file from the changeset; the file is not staged and does not appear in the commit. The pipeline is not triggered for a file that would violate the binary exclusion policy. | REQ-006 |
| **Credential literal committed to any branch** | The CI/CD pipeline's secret detection stage detects the committed credential, fails the stage, and blocks the pipeline from producing any build artifact. The finding is reported with file-reference context sufficient to locate and remediate the exposure before deployment. | REQ-005, REQ-013 |
| **Merge request author attempts self-approval** | The repository platform rejects the self-approval; the approval count does not increment toward the required threshold; the merge remains blocked until a qualifying peer reviewer approves. | REQ-007 |
| **Ad-hoc migration script marked "superseded — do not re-apply" is attempted** | The migration documentation unambiguously identifies the script as superseded, names the versioned migration that replaces it, and contains an explicit warning — enabling the operator to avoid or reverse the erroneous application without consulting an external resource. | REQ-004 |
| **Audit-critical operation (e.g., handover submission) encounters a partial failure** | The operation either completes fully or raises a recorded exception and enters the retry cycle. Silent partial success or silent data loss shall not occur; the failure state is observable in the task execution record. | REQ-001, REQ-008, REQ-010 |

---

## Backward Compatibility

**No breaking changes — all changes are additive or internal-only.**

This branch introduces no modifications to existing route contracts, URL structures, request or response schemas, session formats, RBAC role definitions, or database table schemas. The existing authentication flows (SSO primary, local login fallback) are preserved without alteration. The session token mechanism — including per-request validation against the database and administrator-forced session revocation — is unchanged. The background task scheduler replacement is an internal infrastructure change that preserves all externally observable task outcomes (email digests dispatched, polling results recorded, retry behaviour). Existing authenticated sessions will remain valid across the deployment boundary.

---

## Dependencies

| Dependency | Type | Purpose | Risk |
|-----------|------|---------|------|
| **Message queue service** | Infrastructure | Persists and dispatches background and scheduled tasks; required for process-isolated task execution and safe multi-worker deployment | Medium — see A-001; must have uptime monitoring before scaling |
| **External database (MySQL-compatible)** | Infrastructure | Persistent storage for all application data, session tokens, and encrypted configuration; required for startup; abort strategy applies if unreachable | Medium — startup failure strategy terminates the process immediately on unreachability |
| **Versioned migration toolchain** (Flask-Migrate / Alembic) | Internal toolchain | All future schema changes must be introduced exclusively via versioned migrations; already in use; no new adoption required | Low — tooling already integrated |
| **CI/CD platform** (GitLab) | Infrastructure | Hosts pipeline definitions, SAST and secret detection templates, merge request approval rules, and pipeline artifact storage | Low — platform already in use; no new platform adoption |
| **Dependency vulnerability database** | External service (public) | Consulted by the dependency vulnerability scan stage to identify known CVEs against declared dependencies | Low — standard public databases; no authentication or SLA required |
| **External identity provider** (OAuth 2.0 / SAML — EPAM Microsoft) | External service | Primary SSO authentication; configuration loaded from the encrypted credential store at startup; not modified by this branch | Low — pre-existing integration; unchanged |
| **ServiceNow** | External REST API | Polled by scheduled background tasks; transient unavailability handled by retry policy (REQ-010) | Medium — prolonged outage causes task backlog; monitoring/alerting recommended |
| **Jira** (board 344407) | External service | Issue correlation and sprint planning; HiveMind service account requires Developer role upgrade before Jira integration is fully functional | Medium — unresolved; no code change in this branch; tracked as open item; escalate if unresolved within two weeks of merge |
| **Confluence** | External service | Single source of truth for user documentation (Admin Guide, User Guide) following binary file removal from the repository | Low — documentation-only dependency; no runtime impact |

---

## Glossary

| Term | Definition |
|------|-----------|
| **Alembic** | Database schema migration framework providing versioned, incremental migration scripts. Used via Flask-Migrate. All future schema changes in ShiftOps shall use this mechanism exclusively. |
| **APScheduler** | Advanced Python Scheduler — the in-process library previously used to run periodic tasks within the web-serving process. Its removal from the web-serving process is the subject of REQ-001. |
| **Audit-critical operation** | Any operation whose partial or silent failure constitutes an unacceptable data integrity risk — principally handover form submission and associated incident logging. These operations shall never silently fail. |
| **Background task worker** | A process isolated from the web-serving tier responsible for executing scheduled and queued tasks (notification digests, third-party polling, retries). |
| **Celery** | Distributed task queue framework referenced in project context as the implementation technology for the isolated background task worker. Not prescribed as a requirement; listed for glossary context only. |
| **CVE** | Common Vulnerabilities and Exposures — a publicly disclosed software security vulnerability with a standardised identifier (e.g., CVE-2024-12345). |
| **EPAM** | The organisation operating the Microsoft identity provider used for ShiftOps SSO authentication. |
| **Fernet** | Symmetric authenticated encryption scheme (AES-128-CBC with HMAC-SHA256) used to protect credentials stored in the application database. |
| **Flask-Migrate** | Flask extension wrapping Alembic to provide versioned database migration management within the ShiftOps application. |
| **Gunicorn** | Production-grade WSGI HTTP server referenced in project context. Not prescribed as a requirement technology; listed for glossary context only. |
| **Handover** | The primary work artefact in ShiftOps — a structured record of shift status, incidents, key points, and actions passed from one operational shift team to the next. |
| **HiveMind** | The service account used by ShiftOps for Jira integration; currently awaiting a Developer role upgrade on board 344407. |
| **pip-audit** | Command-line tool that audits Python project dependencies against known vulnerability databases and produces a machine-readable report. Referenced in project context; not prescribed as a requirement. |
| **RBAC** | Role-Based Access Control — the authorisation model governing user permissions in ShiftOps across four roles: `super_admin`, `account_admin`, `team_admin`, `user`. |
| **SAML** | Security Assertion Markup Language — an open standard for exchanging authentication and authorisation data between an identity provider and a service provider. Used as part of the ShiftOps SSO flow. |
| **SAST** | Static Application Security Testing — automated analysis of source code to identify potential security vulnerabilities without executing the code. |
| **Secret Detection** | Automated scanning of source code and git history to identify committed credentials, API keys, or other sensitive literal values. |
| **Session Token** | A server-side record in the `session_tokens` database table created on login and validated on every request; administrators can revoke tokens to force logout regardless of client cookie state. |
| **ShiftOps** | The production name of the Shifthandover project — a server-side rendered web application for shift handover management built on the Flask framework. |
| **SSO** | Single Sign-On — authentication mechanism allowing users to authenticate once with the EPAM Microsoft identity provider and access ShiftOps without re-entering credentials. |
| **Superseded migration** | A migration script that has been replaced by a versioned Alembic migration and must not be re-applied to any environment. Documented in the migration README (REQ-004). |
| **WSGI** | Web Server Gateway Interface — the Python standard (PEP 3333) defining the interface between web servers and Python web applications. |


---
## Technical Design Specification

# Architecture Design Specification
## ShiftOps Archaeology & Hardening — CTCOAMSHM-7

---

## Meta

| Field | Value |
|-------|-------|
| **Ticket ID** | CTCOAMSHM-7 |
| **Project Name** | ShiftOps (Shifthandover) |
| **Creation Date** | 2026-05-02 |
| **Spec Reference** | Functional Specification: ShiftOps Archaeology & Hardening (In Review) |
| **Status** | Draft — Ready for Engineering Review |
| **Branch Scope** | Archaeology & Hardening (no new user-visible features) |
| **Architecture Author** | Generated from approved specification and interrogation summary |

---

## Problem Spec Reference

This design addresses the 13 requirements (REQ-001 through REQ-013) defined in the approved **Functional Specification: ShiftOps Archaeology & Hardening**. Requirements span four categories: infrastructure (scheduled task isolation, WSGI server replacement, container orchestration), security (credential hygiene, CI/CD scanning, input validation), process (migration documentation, branch protection, binary file exclusion), and operational resilience (startup validation, retry behaviour, graceful degradation). All requirements are additive or internal-only — no existing route contracts, database schemas, session formats, or RBAC definitions are modified. Refer to the approved specification for full requirement text, acceptance criteria, constraints, and glossary.

---

## Current Architecture

### Existing Components Relevant to This Hardening Branch

**Web Serving Tier**
- `app.py` — Flask application factory; registers all ~45–50 Blueprint modules; currently initialises APScheduler in-process and starts the application via `app.run()` (Flask development server / Werkzeug). This file is the primary modification target.
- `routes/` directory — ~45–50 Blueprint modules, each handling a domain area (auth, dashboard, handover, incidents, key points, change info, SSO, etc.). Route handlers contain inline RBAC checks and currently have inconsistent or absent input validation before persistence.
- `auth.py` / `routes/auth.py` — Local login path; Fernet-encrypted password store.
- `routes/sso_auth.py` / `routes/sso_config.py` — OAuth 2.0 / SAML SSO path.

**Background Task Tier (current — to be refactored)**
- `services/ctask_scheduler.py` — Exists today; dispatches scheduled jobs (email notification digests, ServiceNow polling, retry operations) using APScheduler running **inside** the Gunicorn/Flask process. This is the root cause of duplicate task execution on scale-out and is the primary functional refactoring target.
- APScheduler — In-process Python scheduler; will be removed from the web-serving process entirely.

**Data & Configuration Tier**
- `models/sso_config.py` — Encrypted OAuth configuration stored in the database; loaded at startup via `Config.init_from_database()`.
- `models/` — SQLAlchemy model definitions for all application entities.
- Flask-Migrate / Alembic — Versioned database migration toolchain; already integrated. Ad-hoc SQL scripts exist alongside versioned migrations with undocumented status.
- `session_tokens` table — Server-side session token store; validated on every request by `validate_session()` middleware. Unchanged by this branch.

**Test Infrastructure**
- `tests/config.py` — Resolves test credentials; currently contains hardcoded literal values for superadmin, admin, and user credentials. Primary credential hygiene target.

**CI/CD & Repository**
- `.gitlab-ci.yml` — GitLab pipeline definition; currently has no dedicated security scanning stage. To be extended.
- `.gitignore` — Does not currently exclude binary documentation file types. To be extended.
- Binary documentation files (`.pdf`, `.docx`, `.doc`, `.xlsx`, `.pptx`) — Tracked in the repository. To be removed and excluded.
- GitLab branch protection — Main branch currently permits direct pushes; no MR approval requirement is enforced. To be configured.

### Existing Patterns

| Pattern | Current State |
|---------|--------------|
| **Route style** | Server-side rendered HTML; Flask Blueprint per domain; limited inline JSON for in-page ops |
| **RBAC enforcement** | Inline within individual route handler functions; no shared decorator |
| **Session management** | Flask-Login + per-request `validate_session()` DB check; administrator-forced revocation via `session_tokens` table |
| **Error handling** | Inconsistent; partial validation in some routes, none in others; no shared validation utility |
| **Configuration loading** | `Config.init_from_database()` at startup; OAuth secrets via `SecretsManager` (Fernet AES); test credentials hardcoded |
| **Task scheduling** | APScheduler in-process alongside Gunicorn workers |
| **Container orchestration** | `docker-compose.yml`; web service currently uses `python app.py` as command |

### Integration Points Where This Design Connects to Existing Code

| Integration Point | Nature of Connection |
|-------------------|---------------------|
| `app.py` | Remove APScheduler init; add Celery app init; invoke startup validator |
| `services/ctask_scheduler.py` | Refactor task functions from APScheduler jobs to Celery tasks |
| `docker-compose.yml` | Add `redis`, `celery-worker`, `celery-beat` services; change web command |
| `routes/dashboard*.py` | Wrap Celery worker status queries via instrumentation adapter |
| All `routes/*.py` handling form POST | Integrate centralized validation utility before persistence |
| `tests/config.py` | Replace literal credentials with environment variable resolution |
| `.gitlab-ci.yml` | Insert security stage before build |
| `.gitignore` | Append binary documentation exclusion patterns |

---

## Architecture

### Pattern

**Process-Isolated Worker Architecture** layered on the existing Flask SSR monolith.

The web tier (Flask + Gunicorn) and background task tier (Celery worker + Celery Beat) are separated into distinct OS processes communicating exclusively through a Redis message broker. This is the minimal pattern change required to eliminate duplicate task execution on Gunicorn scale-out, preserve all existing route contracts and database schemas, and satisfy REQ-001 and REQ-009 without introducing a full distributed workflow orchestration platform (explicitly a non-goal).

All remaining hardening changes (startup validation, credential hygiene, WSGI server, input validation, pipeline security, repository hygiene, branch protection) are additive hardening measures applied to the monolith without altering its external pattern. The SSR monolith pattern itself is preserved.

**Why this pattern and not others:** The application's task volume and complexity do not warrant Airflow, Prefect, or a distributed workflow orchestrator. The risk being closed is architectural (APScheduler co-located with Gunicorn), not operational complexity. Celery + Redis provides the necessary broker-mediated deduplication guarantee with the lowest adoption footprint given the existing Python ecosystem.

---

### Components

---

#### COMP-001 — Production WSGI Entry Point Script
- **Type**: Shell script / process entry point
- **Responsibility**: Launch the Flask application under Gunicorn with production-grade settings, making the development server unreachable as a startup path.
- **File Path**: `start.sh` (repository root)
- **Dependencies**: None within the Python application; invoked by COMP-012 (docker-compose web service command)
- **Requirements Addressed**: REQ-003, AC-003a, AC-003b

**Interface Contract:**
- **Invocation**: `bash start.sh` (set as executable; called directly by container orchestration)
- **Gunicorn arguments to specify** (exact values are implementation; these are the required parameters):
  - `-w <N>` — number of worker processes (initially `1`; safe to increase after Redis monitoring confirmed per A-001)
  - `-b 0.0.0.0:5000` — bind address
  - `--timeout 120` — worker request timeout (≥ 120 seconds per REQ-003)
  - `--access-logfile -` — access log to stdout for container log capture
  - `app:app` — WSGI application target
- **Exit behaviour**: If Gunicorn fails to bind (e.g., port already in use), `start.sh` exits with the non-zero exit code propagated from Gunicorn. It must not attempt to fall back to `python app.py` or any other invocation.
- **What must NOT appear**: Any invocation of `python app.py`, `flask run`, or `app.run(debug=...)`.

---

#### COMP-002 — Application Startup Validator
- **Type**: Utility module
- **Responsibility**: Verify all required runtime configuration values are present and all critical external services are reachable before the Flask application enters the running state.
- **File Path**: `startup_checks.py` (repository root, adjacent to `app.py`)
- **Dependencies**: Python standard library (`os`, `sys`, `logging`); existing `Config` class in `app.py`; database connection configured by Flask-SQLAlchemy; Redis connection URL from environment
- **Requirements Addressed**: REQ-011, AC-011a, AC-011b; partially REQ-002 (no-fallback enforcement in non-localhost environments)

**Interface Contract:**

```
Function: run_startup_checks(app: Flask) -> None
  Called once during application factory initialization in app.py,
  after configuration loading, before route registration.

  Checks (in order):
    1. For each name in REQUIRED_ENV_VARS (list defined in this module):
       - If os.environ.get(name) is None or empty string:
         → log.critical("STARTUP FAILURE: Required environment variable '<name>' is not set.")
         → sys.exit(1)
    2. Database reachability: execute a trivial SQL probe (e.g., SELECT 1) within the app context.
       - On failure: log.critical("STARTUP FAILURE: Database unreachable — <error>")
         → sys.exit(1)
    3. Redis/broker reachability: attempt connection to CELERY_BROKER_URL.
       - On failure: log.critical("STARTUP FAILURE: Redis broker unreachable at <url> — <error>")
         → sys.exit(1)

  On all checks passing: returns normally; application initialization continues.
  On any check failing: process exits with code 1 before any route is registered.
```

**REQUIRED_ENV_VARS registry** (minimum set; implementation must enumerate all):
- `SECRET_KEY`
- `DATABASE_URL` (or component env vars: `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`)
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`

**Note:** Test-specific variables (`TEST_SUPERADMIN_PASSWORD`, etc.) are NOT checked here; they are checked by COMP-006 within the test runner context.

---

#### COMP-003 — Celery Application Factory
- **Type**: Service module
- **Responsibility**: Instantiate, configure, and expose the single shared Celery application object used by all task definitions and the worker process.
- **File Path**: `services/celery_app.py`
- **Dependencies**: `celery` library; `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` environment variables; COMP-005 (imports beat schedule)
- **Requirements Addressed**: REQ-001, REQ-009

**Interface Contract:**

```
Module-level export:
  celery_app: Celery  — the configured Celery application instance

Configuration properties to be set on celery_app:
  broker_url                  ← os.environ["CELERY_BROKER_URL"]
  result_backend              ← os.environ["CELERY_RESULT_BACKEND"]
  task_serializer             = "json"
  result_serializer           = "json"
  accept_content              = ["json"]
  timezone                    = "UTC"
  enable_utc                  = True
  task_acks_late              = False   (at-most-once guarantee; see ADR-002)
  beat_schedule               ← imported from COMP-005
  worker_hijack_root_logger   = False   (preserve Flask/application logger configuration)

Flask integration:
  celery_app.conf.update(app.config) is called from the Flask app factory in app.py
  after the Flask app is created, binding the Celery instance to the Flask app context.
  This follows the "Flask-Celery integration without flask-celery extension" pattern.
```

---

#### COMP-004 — Background Task Definitions
- **Type**: Service module (modified from existing `services/ctask_scheduler.py`)
- **Responsibility**: Define all background task functions as Celery task objects with retry policy, task routing, and execution logging.
- **File Path**: `services/ctask_scheduler.py` (modified in-place)
- **Dependencies**: COMP-003 (`celery_app`); existing business logic for email digests, ServiceNow polling; external service clients
- **Requirements Addressed**: REQ-001, REQ-009, REQ-010, AC-010a, AC-010b

**What Changes vs. What Stays the Same:**
- **Removed**: APScheduler `@scheduler.scheduled_job(...)` decorators and any APScheduler `BackgroundScheduler` initialization.
- **Preserved**: The underlying task business logic (email construction, ServiceNow API calls, retry-eligible operations). Task function signatures may change to match Celery conventions but outcomes are identical.
- **Added**: Celery `@celery_app.task(...)` decorators with retry configuration.

**Interface Contract — Task Decorator Specification:**

Every task function in this module must be decorated with the following parameters (minimum):

```
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,        # seconds; satisfies REQ-010 ≥30s delay
    autoretry_for=(ExternalServiceError, ConnectionError, Timeout),
    retry_backoff=False,           # flat 30-second delay, not exponential
    acks_late=False,               # at-most-once; consistent with COMP-003
    name="shiftops.<task_name>"    # explicit task name prevents import-path collisions
)
def <task_name>(self, *args, **kwargs) -> dict:
    ...
    # Return contract:
    # { "status": "success", "task": "<task_name>", "completed_at": "<ISO8601>" }
    # On terminal failure (retries exhausted): exception propagates; Celery records FAILURE state.
```

**Task Execution Log Contract:**
Each task must emit a structured log entry on completion and on each retry attempt:
- `log.info("TASK_STARTED task=<name> task_id=<celery_task_id> attempt=<N>")`
- `log.info("TASK_COMPLETED task=<name> task_id=<celery_task_id> attempt=<N>")`
- `log.warning("TASK_RETRY task=<name> task_id=<celery_task_id> attempt=<N> reason=<str>")`
- `log.error("TASK_FAILED task=<name> task_id=<celery_task_id> attempts_exhausted=3 error=<str>")`

This log contract satisfies REQ-010's observability requirement ("observable without manual log parsing") by enabling log aggregation queries on the `TASK_` prefix.

**Audit-Critical Task Designation:**
Tasks that invoke handover submission or incident logging must never silently fail. If such a task raises a non-retryable exception (e.g., database integrity error after retries exhausted), it must log `TASK_FAILED` at `ERROR` level and re-raise the exception to ensure Celery records a `FAILURE` state in the result backend. No `try/except: pass` blocks are permitted in audit-critical tasks.

---

#### COMP-005 — Celery Beat Periodic Schedule Configuration
- **Type**: Configuration module
- **Responsibility**: Define the periodic task trigger schedule consumed by the Celery Beat process, mapping task names to their cron/interval expressions.
- **File Path**: `celeryconfig.py` (repository root)
- **Dependencies**: COMP-004 (task names must match); standard `celery.schedules` primitives
- **Requirements Addressed**: REQ-001, REQ-009

**Interface Contract:**

```
Module-level export:
  beat_schedule: dict[str, dict]  — Celery beat schedule mapping

Shape:
  {
    "<schedule_entry_name>": {
      "task": "shiftops.<task_name>",     # must match COMP-004 task name
      "schedule": crontab(...) | timedelta(...),
      "args": (...),                       # optional positional args
      "kwargs": {...},                     # optional keyword args
      "options": { "expires": <seconds> } # task expiry to prevent stale execution
    },
    ...
  }

Constraint: This file defines exactly ONE authoritative source of truth for all scheduled
triggers. The Celery Beat process runs from EXACTLY ONE container instance (no scaling of
the beat service). See COMP-012 for enforcement.
```

---

#### COMP-006 — Test Credential Resolver
- **Type**: Configuration module (modified from existing `tests/config.py`)
- **Responsibility**: Resolve test suite authentication credentials from named environment variables, enforcing a hard failure when variables are absent in non-localhost environments.
- **File Path**: `tests/config.py` (modified in-place)
- **Dependencies**: Python standard library (`os`, `socket`); no Flask app context required
- **Requirements Addressed**: REQ-002, REQ-013, AC-002a, AC-002b

**What Changes vs. What Stays the Same:**
- **Removed**: All credential literal strings (e.g., `"admin123"`, `"password"`, etc.).
- **Preserved**: The exported credential name constants (`TEST_SUPERADMIN_PASSWORD`, `TEST_ADMIN_PASSWORD`, `TEST_USER_PASSWORD`) that existing test modules import.
- **Added**: Environment variable resolution logic with localhost-only fallback gate.

**Interface Contract:**

```
Required environment variable names (exact strings):
  TEST_SUPERADMIN_PASSWORD    → credentials for superadmin-level test operations
  TEST_ADMIN_PASSWORD         → credentials for account_admin-level test operations
  TEST_USER_PASSWORD          → credentials for user-level test operations

Resolution logic (described, not coded):

  is_localhost: bool ← (socket.gethostname() resolves to loopback) OR
                       (os.environ.get("CI") is not set) OR
                       (os.environ.get("ENVIRONMENT") not in {"staging", "production", "ci"})

  For each of the three variables:
    value = os.environ.get("<VAR_NAME>")
    if value is None or value == "":
      if is_localhost:
        value = <DOCUMENTED_FALLBACK_VALUE>
        # Fallback value must be documented in CLAUDE.md and CONTRIBUTING.md
        # Fallback value must NOT be the same as any production credential
      else:
        raise EnvironmentError(
          "Test credential '<VAR_NAME>' is not set. "
          "Set this environment variable before running the test suite. "
          "See CONTRIBUTING.md for setup instructions."
        )

Module-level exports after resolution:
  TEST_SUPERADMIN_PASSWORD: str
  TEST_ADMIN_PASSWORD: str
  TEST_USER_PASSWORD: str
```

**Localhost Detection Note:** The `is_localhost` check must be conservative — it must default to `False` (non-localhost behaviour, i.e., raise error) in any ambiguous case, rather than defaulting to `True`. The only safe fallback condition is confirmed loopback hostname AND absence of CI environment markers.

---

#### COMP-007 — Migration Registry Document
- **Type**: Documentation artifact
- **Responsibility**: Provide a human-readable classification of every database migration script in the repository, enabling operators to determine safe application order without consulting any external system.
- **File Path**: `migrations/README.md`
- **Dependencies**: None (static document; references migration script filenames in the `migrations/` directory)
- **Requirements Addressed**: REQ-004, AC-004a, AC-004b

**Document Structure Contract:**

The document must contain four sections, in order:

1. **Overview** — States the migration toolchain (Flask-Migrate / Alembic), the single rule ("all future schema changes via `flask db migrate` exclusively"), and the date of last audit.

2. **Migration Classification Table** — A table with columns: `Script Filename`, `Classification`, `Applied to Production?`, `Notes`. Every migration script file present in `migrations/versions/` and every ad-hoc `.sql` file in `migrations/` (or equivalent directory) must appear in this table with exactly one of three classifications:
   - `APPLIED — production` — has been run against the production database; safe to skip on fresh installs only if included in the Alembic version chain.
   - `SUPERSEDED — do not re-apply` — replaced by a versioned Alembic migration; must never be executed manually against any environment.
   - `ENVIRONMENT-SPECIFIC` — applies only to a named non-production environment (name must be stated in Notes).

3. **Superseded Script Detail** — For every script classified as `SUPERSEDED`, a subsection that: (a) names the superseding versioned migration by filename and Alembic revision ID, (b) states an explicit operator warning ("Do not execute this script. Applying it after the versioned migration will cause schema inconsistency."), and (c) describes what the script originally did and why it was superseded.

4. **Future Migration Policy** — A single authoritative paragraph stating that no ad-hoc SQL scripts shall be introduced; all future schema changes must be introduced as Alembic migrations via `flask db migrate` and reviewed in a merge request before execution.

---

#### COMP-008 — CI/CD Security Stage Configuration
- **Type**: Pipeline configuration (modified)
- **Responsibility**: Declare and enforce a security scanning stage in the GitLab CI/CD pipeline that completes and passes before any build artifact is produced.
- **File Path**: `.gitlab-ci.yml` (modified in-place)
- **Dependencies**: GitLab Runner; GitLab-provided SAST and Secret Detection CI/CD templates; `pip-audit` tool available in the pipeline runner environment; `requirements.txt` present in repository root
- **Requirements Addressed**: REQ-005, REQ-013, AC-005a, AC-005b, AC-005c

**What Changes vs. What Stays the Same:**
- **Preserved**: All existing stages and jobs.
- **Added**: A new `security` stage that runs before `build`. The `build` stage must be listed after `security` in the top-level `stages` array.

**Stage and Job Contract:**

```yaml
# Stage ordering (within the top-level stages: list)
stages:
  - security    # NEW — must precede build
  - build
  - <...existing stages...>

# Job 1: Dependency vulnerability scan
dependency-scan:
  stage: security
  script:
    - pip install pip-audit
    - pip-audit --requirement requirements.txt --format json --output pip-audit-report.json
    # pip-audit exits non-zero on any CVE finding; this causes the job to fail.
  artifacts:
    when: always           # Save report even on failure for triage
    paths:
      - pip-audit-report.json
    reports:
      # No native GitLab report type for pip-audit; saved as generic artifact
  allow_failure: false     # Failing this job blocks the pipeline

# Job 2: Python SAST
# Uses the GitLab-managed SAST template (Bandit-based for Python)
include:
  - template: Security/SAST.gitlab-ci.yml
  - template: Security/Secret-Detection.gitlab-ci.yml
# Both templates produce jobs in the "test" stage by default;
# override their stage to "security" using job-level stage: overrides
# or per GitLab documentation for stage override of included templates.

sast:
  stage: security

secret_detection:
  stage: security
  # GitLab Secret Detection scans full git history by default.
  # No additional configuration required beyond template inclusion.
```

**Failure semantics:**
- `dependency-scan` failing: pipeline stops; build stage does not execute; `pip-audit-report.json` is saved as artifact for remediation.
- `sast` failing: pipeline stops; build stage does not execute.
- `secret_detection` failing: pipeline stops; build stage does not execute; finding includes file reference per GitLab Secret Detection report format.

---

#### COMP-009 — Repository Binary Documentation Exclusion Configuration
- **Type**: VCS configuration (modified)
- **Responsibility**: Prevent binary documentation files from being staged or committed to the repository.
- **File Path**: `.gitignore` (modified in-place)
- **Dependencies**: None
- **Requirements Addressed**: REQ-006, AC-006a, AC-006b

**What Changes:**
- **Added** (appended as a clearly labelled section): The following patterns:

```
# Binary documentation files — maintained in Confluence, not in source control
*.pdf
*.doc
*.docx
*.xls
*.xlsx
*.ppt
*.pptx
```

- **Not modified**: All existing `.gitignore` entries.

**Pre-commit action required (one-time, outside CI):** All currently tracked binary documentation files must be removed from git tracking using `git rm --cached <file>` before merging this change, and the removal committed as part of this branch. The `.gitignore` entry alone does not retroactively un-track already-tracked files.

---

#### COMP-010 — Input Validation Utility
- **Type**: Utility module (new)
- **Responsibility**: Provide reusable, field-level input validation functions that return structured error descriptions for use by Flask route handlers before any data is persisted.
- **File Path**: `utils/validation.py`
- **Dependencies**: Python standard library only; no Flask context required (functions are pure)
- **Requirements Addressed**: REQ-008, AC-008a, AC-008b, AC-008c

**Interface Contract:**

```
Type alias:
  ValidationError: TypedDict with keys:
    field: str       — the name of the field that failed validation
    message: str     — human-readable description of the constraint violation
                       (e.g., "Shift date is required and must not be empty."
                             "Duration must be a positive integer between 1 and 1440.")

Function signatures (described; types are Python type hints):

  validate_required(value: Any, field_name: str) -> ValidationError | None
    Returns ValidationError if value is None, empty string, or whitespace-only.
    Returns None if valid.

  validate_not_null(value: Any, field_name: str) -> ValidationError | None
    Returns ValidationError if value is None.

  validate_range(
    value: int | float,
    field_name: str,
    min_val: int | float,
    max_val: int | float
  ) -> ValidationError | None
    Returns ValidationError if value < min_val or value > max_val.
    Message must state: "<field_name> must be between <min_val> and <max_val>. Received: <value>."

  validate_max_length(value: str, field_name: str, max_length: int) -> ValidationError | None
    Returns ValidationError if len(value) > max_length.

  validate_form(validators: list[Callable[[], ValidationError | None]]) -> list[ValidationError]
    Executes all validator callables in order.
    Returns a list of all ValidationErrors (may be empty = valid).
    Does NOT short-circuit on first failure — all fields are validated in one pass.

  format_error_response(errors: list[ValidationError]) -> dict
    Returns: { "errors": [{ "field": "...", "message": "..." }, ...] }
    Used by routes to construct the error payload.
```

**Usage contract for route handlers (pattern):**

Every form-handling POST route must:
1. Call `validate_form([...])` on the submitted data before any database operation.
2. If `errors` list is non-empty: return the error response immediately without writing to the database (no partial records).
3. If `errors` is empty: proceed with persistence.

The route handler determines which validators to assemble based on the form's field definitions. The validation utility is not responsible for knowing which fields exist on which form — that coupling remains in the route handler.

---

#### COMP-011 — Worker Status Instrumentation Adapter
- **Type**: Service module (new)
- **Responsibility**: Safely query Celery worker process status and return a structured result that represents the degraded state gracefully when the Celery broker or workers are unreachable.
- **File Path**: `services/worker_status.py`
- **Dependencies**: COMP-003 (`celery_app`); standard `celery.app.control` interface
- **Requirements Addressed**: REQ-012, AC-012a, AC-012b

**Interface Contract:**

```
Type definitions:

  WorkerStatusResult: TypedDict with keys:
    available: bool        — True if at least one worker responded within the timeout
    worker_count: int      — number of active workers (0 if unavailable)
    active_tasks: int      — total active tasks across all workers (0 if unavailable)
    error: str | None      — human-readable error description if unavailable; None if available

Function signature:

  get_worker_status(timeout_seconds: float = 1.0) -> WorkerStatusResult
    Calls celery_app.control.inspect(timeout=timeout_seconds).active()
    On success: returns WorkerStatusResult with available=True and populated counts.
    On any exception (ConnectionError, TimeoutError, any Exception):
      → catches the exception
      → logs at WARNING level: "WORKER_STATUS_CHECK_FAILED: <exception>"
      → returns WorkerStatusResult(available=False, worker_count=0, active_tasks=0,
          error="Worker status unavailable: <short_reason>")
    Does NOT re-raise the exception. Does NOT return an HTTP error response.
    The timeout must be short (default 1.0 second) to avoid blocking web request handling.
```

**Integration with dashboard routes:**

Dashboard route handlers in `routes/dashboard*.py` must call `get_worker_status()` and render the result into the template context as a `worker_status` variable. The template must conditionally render the instrumentation widget: display stats when `worker_status.available` is `True`; display a degraded indicator (e.g., "Worker status unavailable") when `False`. The route handler must not propagate exceptions from `get_worker_status()` — the function contract guarantees no exceptions escape.

---

#### COMP-012 — Container Orchestration Service Definitions
- **Type**: Infrastructure configuration (modified)
- **Responsibility**: Define the complete set of containerized services (web, celery-worker, celery-beat, redis) with correct dependencies, startup order, and scaling constraints.
- **File Path**: `docker-compose.yml` (modified in-place)
- **Dependencies**: COMP-001 (web command), COMP-003 (Celery app import path), COMP-004 (task module), COMP-005 (beat schedule)
- **Requirements Addressed**: REQ-001, REQ-003, REQ-009

**What Changes vs. What Stays the Same:**

*Modified:*
- `web` service `command`: changed from `python app.py` → `bash start.sh`
- `web` service `depends_on`: add `redis` (broker must be available before web starts)
- All services: environment variable injection via `env_file: .env` or explicit `environment:` block referencing `${VAR_NAME}` syntax (no literal credential values in this file)

*Added:*

```
Service: redis
  image: redis:<pinned_version>
  restart: unless-stopped
  ports: (internal only; not exposed to host in production)
  volumes: (optional persistence volume for broker durability)

Service: celery-worker
  build: . (same image as web)
  command: celery -A services.celery_app.celery_app worker --loglevel=info
  depends_on: [web, redis]   # web ensures Flask app context is importable; redis is the broker
  restart: unless-stopped
  deploy:
    replicas: 1              # scale as needed; safe to scale > 1 (no duplicate task risk)

Service: celery-beat
  build: . (same image as web)
  command: celery -A services.celery_app.celery_app beat --loglevel=info --scheduler celery.beat:PersistentScheduler
  depends_on: [redis]
  restart: unless-stopped
  deploy:
    replicas: 1              # MUST remain 1; scaling beat causes duplicate trigger dispatch
    # This constraint is explicitly documented in the compose file as a comment.
```

**Critical Constraint on `celery-beat` scaling:** The `celery-beat` service must never be scaled beyond a single instance. Duplicate Beat instances each independently dispatch task triggers to the broker, which produces duplicate executions violating REQ-009. This constraint must be documented as an inline comment in `docker-compose.yml` adjacent to the `celery-beat` service definition and noted in the deployment runbook (see Open Items).

---

#### COMP-013 — GitLab Branch Protection and MR Approval Configuration
- **Type**: Platform configuration (GitLab project settings — no file path in repository)
- **Responsibility**: Enforce at-minimum-one peer-reviewer approval on merge requests targeting the main branch, prohibiting self-approval and direct pushes.
- **File Path**: GitLab project → Settings → Repository → Protected Branches; Settings → Merge Requests → Approvals (no repository file)
- **Dependencies**: None within the codebase; requires GitLab Maintainer or Owner role to configure
- **Requirements Addressed**: REQ-007, AC-007a, AC-007b, AC-007c

**Configuration Contract:**

Protected Branch settings for `main` (or `master`):
- Allowed to push: No one (block all direct pushes, including Maintainers)
- Allowed to merge: Maintainers (via merge request only)
- Code owner approval required: Disabled (insufficient team size to configure CODEOWNERS)

Merge Request Approval settings:
- Required approvals: `1`
- Allow MR authors to approve their own MRs: **Disabled**
- Require new approvals when new commits are pushed: Enabled (prevents approval-then-force-push pattern)
- Remove all approvals when new commits are pushed: Enabled

---

### Data Flows

**Data Flow 1 — HTTP Request Serving (Production)**
```
Inbound HTTP request
  → COMP-001 (start.sh / Gunicorn, ≥1 worker processes)
  → Flask WSGI application (app.py)
  → validate_session() middleware (session_tokens table — unchanged)
  → Flask Blueprint route handler (routes/*.py)
  → [if POST with form data] → COMP-010 (validate_form())
      → [validation error] → error response rendered (no DB write)
      → [validation pass] → SQLAlchemy model persistence → success response
  → [if dashboard route] → COMP-011 (get_worker_status())
      → [worker available] → status data in template context
      → [worker unavailable] → degraded state in template context
  → Rendered HTML / JSON response
  ← HTTP 200 (or redirect)
```

**Data Flow 2 — Scheduled Background Task Execution (Happy Path)**
```
Wall-clock trigger time reached
  → COMP-005 (Celery Beat schedule) — single Beat process
  → Redis message broker (task message enqueued exactly once)
  → COMP-004 (Celery worker picks up message — exactly one worker consumes the message)
  → Task function executes:
      → External service call (e.g., ServiceNow API, email SMTP)
      → log.info("TASK_COMPLETED ...")
      → Result written to Redis result backend
  → Redis result backend records TASK_COMPLETED state
```

**Data Flow 3 — Scheduled Task with Transient Failure and Retry**
```
Celery task function encounters ExternalServiceError on attempt 1
  → COMP-004: log.warning("TASK_RETRY task=<name> attempt=1 reason=<error>")
  → Celery schedules retry after 30 seconds (default_retry_delay=30)
  → [30-second delay]
  → Attempt 2 executes:
      → [Success] → log.info("TASK_COMPLETED ... attempt=2") → DONE
      → [Failure] → retry → [30-second delay] → Attempt 3
      → [Success] → log.info("TASK_COMPLETED ... attempt=3") → DONE
      → [Failure] → retry → [30-second delay] → Attempt 4
      → [Failure] → retries exhausted → log.error("TASK_FAILED ... attempts_exhausted=3")
        → exception propagates → Celery records FAILURE state in result backend
```

**Data Flow 4 — Application Startup**
```
Container start
  → COMP-001 (start.sh) invokes Gunicorn
  → Gunicorn forks worker process(es)
  → Each worker imports app.py → Flask app factory runs
  → COMP-002 (run_startup_checks(app)) called:
      → Check required env vars
          → [missing] → log.critical("STARTUP FAILURE: ...") → sys.exit(1) → Gunicorn exits non-zero
      → Check DB reachability
          → [unreachable] → log.critical("STARTUP FAILURE: ...") → sys.exit(1)
      → Check Redis reachability
          → [unreachable] → log.critical("STARTUP FAILURE: ...") → sys.exit(1)
      → [all pass] → returns normally
  → Route registration continues
  → Gunicorn begins accepting requests
```

**Data Flow 5 — Test Suite Credential Resolution**
```
Test runner invoked (pytest)
  → tests/config.py (COMP-006) imported
  → is_localhost check:
      → [CI environment detected] → is_localhost = False
      → [loopback hostname, no CI markers] → is_localhost = True
  → For each credential variable:
      → os.environ.get("<VAR_NAME>")
      → [value present] → use value
      → [absent, is_localhost=True] → use documented fallback
      → [absent, is_localhost=False] → raise EnvironmentError (test suite fails immediately)
  → TEST_SUPERADMIN_PASSWORD, TEST_ADMIN_PASSWORD, TEST_USER_PASSWORD exported
  → Test modules import credentials from tests/config.py
```

**Data Flow 6 — CI/CD Pipeline Security Gate**
```
Developer pushes commit to any branch
  → GitLab pipeline triggered
  → COMP-008 (security stage) — runs before build:
      → Job 1: pip-audit
          → [CVE found] → exit non-zero → artifact saved → pipeline blocked
          → [clean] → artifact saved → job passes
      → Job 2: GitLab SAST (Bandit)
          → [finding] → job fails → pipeline blocked
          → [clean] → job passes
      → Job 3: GitLab Secret Detection (full history)
          → [secret found] → job fails → pipeline blocked
          → [clean] → job passes
      → [all three pass] → build stage proceeds
```

**Data Flow 7 — Merge Request to Main Branch**
```
Developer opens MR targeting main
  → COMP-013 (GitLab branch protection) evaluated:
      → Direct push attempt → rejected immediately (push rules)
  → Author attempts self-approval → rejected (self-approval disabled)
  → No peer approval → merge button disabled / merge attempt rejected
  → Peer reviewer approves (≥1, not author) → approval count = 1 (threshold met)
  → Author initiates merge → permitted → branch merged
```

**Data Flow 8 — Worker Unavailable During Scheduled Trigger**
```
Celery Beat dispatches task message → Redis broker
  → Celery worker service is down
  → Task message persists in Redis queue (not consumed)
  → Web tier continues serving HTTP requests normally (no impact)
  → COMP-011 returns WorkerStatusResult(available=False) for dashboard instrumentation
  → Dashboard renders degraded indicator; core routes return HTTP 200
  → Celery worker container restarts (Docker restart: unless-stopped)
  → Worker reconnects to Redis → consumes queued task message
  → Task executed exactly once (message consumed → acknowledged → executed)
```

---

## API Contracts

This application is an SSR monolith; no new HTTP endpoints are introduced. The following contracts define modifications to existing endpoint behaviour and the internal service method interfaces exposed by new components.

---

### Modified Behaviour: All Form Submission Endpoints (POST)

**Applies to:** All `POST` route handlers in `routes/` that accept user-submitted form data and write to the database. The URL paths, HTTP methods, and authentication requirements of these routes are **unchanged**.

**Current behaviour (pre-hardening):** Route handlers proceed directly to database operations on form submission; validation is absent or inconsistent; partial records may be created on malformed input.

**Modified behaviour (post-hardening):** Every form-handling POST route validates all submitted fields using COMP-010 before any database operation.

**Request (unchanged):** `application/x-www-form-urlencoded` or `multipart/form-data` — identical to current.

**Success Response (unchanged):** 302 redirect to result page, or 200 with rendered HTML, per existing route behaviour.

**Error Response (new — validation failure):**

For routes that currently return rendered HTML:
```
HTTP Status: 200 (re-render the form with errors inline — standard SSR pattern)
Content-Type: text/html
Body: Re-rendered form template with error context injected:
  - template variable: errors: list[ValidationError]
    [{ "field": "<field_name>", "message": "<human-readable constraint message>" }, ...]
  - template variable: form_data: dict — the submitted values, preserved for UX
  - Each form field with an error must render the associated error message adjacent to the field.
  - No partial record is created in the database.
```

For routes that currently return JSON (in-page operations):
```
HTTP Status: 422 Unprocessable Entity
Content-Type: application/json
Body: {
  "errors": [
    { "field": "<field_name>", "message": "<human-readable constraint message>" },
    ...
  ]
}
```

**Error Cases and Handling:**

| Error Condition | HTTP Status | Response |
|----------------|-------------|----------|
| Required field empty or null | 200 (HTML) / 422 (JSON) | Error message: `"<Field Label> is required and must not be empty."` |
| Value out of permitted range | 200 (HTML) / 422 (JSON) | Error message: `"<Field Label> must be between <min> and <max>. Received: <value>."` |
| Value exceeds max length | 200 (HTML) / 422 (JSON) | Error message: `"<Field Label> must not exceed <N> characters."` |
| Multiple validation failures | 200 (HTML) / 422 (JSON) | All errors returned in a single response; all fields validated before returning |
| Database error after passing validation | 500 / rendered error page | Internal error logged; user sees generic "An error occurred" message; no partial record (transaction rolled back) |

**Auth requirements:** Unchanged. `validate_session()` middleware enforces authentication before any route handler is reached.

---

### Internal Service Interface: `get_worker_status()` (COMP-011)

This is not an HTTP endpoint. It is a Python function called within dashboard route handlers. Defined fully under COMP-011. Repeated here for completeness:

- **Caller:** `routes/dashboard*.py` route handlers
- **Guarantee:** Never raises an exception (all exceptions caught internally)
- **Returns:** `WorkerStatusResult` — always a valid Python dict-like object
- **Timeout:** 1.0 second (configurable; must remain low to avoid blocking web requests)
- **On success:** `available=True`, populated counts
- **On any failure:** `available=False`, `error="<short reason>"`, counts=0

---

### Internal Service Interface: `run_startup_checks()` (COMP-002)

- **Caller:** `app.py` Flask application factory
- **Called once** per process startup; never called during request handling
- **Returns:** `None` on success
- **On failure:** Calls `sys.exit(1)` — process terminates; never returns
- **Side effects on failure:** Writes to the process log at `CRITICAL` level before exiting

---

## Data Models

### No New Database Tables or Schema Changes

This branch introduces zero modifications to the MySQL database schema. All changes are internal to the application process layer. The following notes document the data models introduced at the infrastructure level (Redis) and the record contract for task execution logging.

---

### Redis Data Structures (Celery Broker and Result Backend)

These structures are managed entirely by the Celery framework; ShiftOps application code does not directly read or write to them. They are documented here for operational awareness.

| Structure | Key Pattern | Purpose | TTL |
|-----------|-------------|---------|-----|
| Task message | `celery` (default queue) | Persists pending task messages between Beat dispatch and worker pickup | Consumed on pickup |
| Task result | `celery-task-meta-<task_id>` | Stores task execution outcome (SUCCESS / FAILURE / RETRY) | Configurable via `result_expires`; recommended 24h |
| Beat schedule state | `celerybeat-schedule` | Tracks last-run timestamps for periodic tasks (PersistentScheduler) | Persistent |

**Note on `result_expires`:** Must be set to at least 24 hours in COMP-003 configuration to satisfy the 24-hour observability window in AC-009a.

---

### Task Execution Log Schema (Application-Level)

Task execution state is observable through two mechanisms:
1. **Structured application logs** — emitted by COMP-004 with the `TASK_` prefix (see COMP-004 interface contract). Queryable in any log aggregation system.
2. **Celery result backend** — Redis records of `SUCCESS` / `FAILURE` state per `task_id`.

No new database table is created for task execution logging. If structured log querying proves insufficient in a future branch, a `task_execution_log` table can be introduced via Alembic migration (per REQ-004's future migration policy).

---

### Existing Models — No Changes

| Model / Table | Change |
|--------------|--------|
| `session_tokens` | **Unchanged** — per-request validation mechanism preserved |
| All handover, incident, keypoint, change_info models | **Unchanged** — schema modifications explicitly excluded from this branch |
| `sso_config` | **Unchanged** — OAuth credential loading via `SecretsManager` preserved |
| All other existing tables | **Unchanged** |

---

### Migration Documentation Record (COMP-007)

Not a database model; described fully under COMP-007. The `migrations/README.md` document is the data artifact for REQ-004. The authoritative classification of each migration script exists only in this document — there is no programmatic enforcement of migration status.

---

## Decisions (ADRs)

---

### ADR-001 — Architecture Pattern: Process-Isolated Worker

**Title:** Process-Isolated Background Task Worker via Message Broker

**Context:**
APScheduler currently runs scheduled tasks (email digests, ServiceNow polling, retry operations) inside the Gunicorn/Flask process. When Gunicorn is scaled to multiple workers (e.g., for load), each worker runs its own APScheduler instance. This causes every scheduled task to fire N times (once per Gunicorn worker) per trigger event — violating REQ-001 and REQ-009. The application cannot be safely scaled beyond a single Gunicorn worker under this architecture.

**Decision:**
Adopt the **Process-Isolated Worker** pattern: move all scheduled and queued task execution to a dedicated worker process communicating with the web tier exclusively through a Redis message broker. The web tier (Gunicorn) dispatches tasks to the broker; the worker process dequeues and executes them. Trigger scheduling is delegated to a separate Celery Beat process.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|-------------|------|------|
| **Distributed lock around APScheduler** (acquire a Redis/DB lock before each task execution; skip if lock held) | No new process; minimal infrastructure change | Fragile — lock acquisition/release must be implemented correctly in every task; risk of lock starvation, missed releases on crash; does not remove APScheduler from web process; complexity grows with each new task; not the community-standard approach | 
| **Do nothing / document single-worker constraint** | Zero engineering cost; constraint is currently tolerated | Does not satisfy REQ-001 or REQ-009; prevents safe scale-out permanently; escalates risk of missed or duplicate notifications as task volume grows |
| **Dedicated cron container running Python scripts** | Simple; no new library dependency | No deduplication guarantee (if cron container scales); no retry mechanism; no result backend; difficult to observe task state; does not integrate with Flask app context |

**Consequences:**

*Positive:*
- Gunicorn can be safely scaled to any number of workers with zero duplicate task executions.
- Task state (SUCCESS / FAILURE / RETRY) is observable via result backend without log parsing.
- Retry logic is centralised and framework-managed.

*Negative trade-offs:*
- Redis becomes a required infrastructure dependency; its unavailability blocks task execution (tasks queue, not silently drop).
- `docker-compose.yml` now manages four services (web, celery-worker, celery-beat, redis) instead of one; operational complexity increases modestly.
- Celery Beat must not be scaled beyond one instance (enforced by compose constraint and documentation).

*Risks and mitigations:*
- **Risk**: Redis outage causes task backlog. **Mitigation**: Redis uptime monitoring and alerting must be in place before Gunicorn is scaled beyond 1 worker (per A-001 and Open Item 3).
- **Risk**: Beat service accidentally scaled to >1. **Mitigation**: Explicit `replicas: 1` in compose and inline comment; noted in deployment runbook.

---

### ADR-002 — Background Task Library: Celery with Redis

**Title:** Celery as Distributed Task Queue with Redis as Broker and Result Backend

**Context:**
The process-isolated worker pattern (ADR-001) requires a message broker to decouple task dispatch from execution, a scheduler to trigger periodic tasks, and a result backend for observability. The choice of library determines API surface, retry semantics, and the broker technology.

**Decision:**
Use **Celery** with **Redis** as both broker and result backend. Celery is already referenced in the project's glossary and interrogation summary as the chosen implementation. Redis is lightweight, operationally simple to run in Docker, and satisfies the broker durability requirements at the current task volume.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|-------------|------|------|
| **RQ (Redis Queue)** | Simpler API; lighter weight; Redis-native | No built-in periodic scheduler (requires `rq-scheduler`, a separate process with less community support than Celery Beat); fewer retry primitives; smaller ecosystem; would require more custom code for retry observability |
| **Dramatiq + APScheduler (separate process)** | Simpler task definitions; type-safe; APScheduler in a standalone process avoids duplication | APScheduler is part of the problem being solved (unfamiliarity with APScheduler's scaling behaviour was the original bug); introducing it back in a different form increases risk; Dramatiq has a smaller ecosystem than Celery |
| **Celery with RabbitMQ as broker** | More robust message durability; better dead-letter queue support | Higher operational complexity (RabbitMQ requires more configuration and resource); Redis already satisfies durability at current task volume and is simpler to operate in Docker; over-engineered for "thousands of requests per day" workload |

**Consequences:**

*Positive:*
- `max_retries`, `default_retry_delay`, `autoretry_for` parameters satisfy REQ-010 with no custom retry logic.
- `celery.control.inspect` provides worker status for COMP-011 with a single call.
- Mature ecosystem; extensive documentation.
- `acks_late=False` (default) provides at-most-once guarantee per trigger dispatch.

*Negative trade-offs:*
- Celery is a non-trivial dependency; it adds indirection between task definition and execution that must be understood by all engineers working on the codebase.
- Redis result backend TTL must be configured to avoid unbounded memory growth.

*Risks and mitigations:*
- **Risk**: `acks_late=False` means a task is lost if the worker crashes mid-execution (message already acknowledged). **Mitigation**: This is the correct trade-off given REQ-009 (no duplicates > no loss); lost tasks will be re-triggered on the next scheduled interval. For audit-critical tasks with longer execution windows, the task must write an in-progress marker to the database before calling external services so that a crash is detectable.

---

### ADR-003 — WSGI Server: Gunicorn

**Title:** Gunicorn as the Production WSGI Server

**Context:**
The application currently starts via `python app.py`, which invokes `app.run()` — the Flask/Werkzeug development server. The development server is single-threaded, not suitable for concurrent requests, not designed for production traffic, and emits a startup warning that it should not be used in production. REQ-003 requires a production-grade WSGI server with ≥120-second request timeout.

**Decision:**
Use **Gunicorn** as the production WSGI server, invoked from `start.sh` with a 120-second worker timeout. Gunicorn is pre-existing in the project context (referenced in glossary) and is the de facto standard for synchronous Flask applications.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|-------------|------|------|
| **uWSGI** | Higher performance ceiling; more configuration options; supports async protocols | Significantly more complex configuration; Emperor mode and vassal configuration are non-trivial; harder to debug; unnecessary complexity for "thousands of requests per day" load |
| **Waitress** | Pure-Python; no C extension dependency; Windows-compatible | Lower throughput ceiling; smaller community; less operator familiarity in Linux/Docker deployments; fewer production deployment examples in Flask ecosystem |
| **Do nothing (keep Werkzeug)** | Zero engineering effort | Violates REQ-003; security risk (development server exposes debug information); no worker timeout control; single-threaded; not suitable for production |

**Consequences:**

*Positive:*
- `--timeout 120` satisfies REQ-003's ≥120-second requirement out of the box.
- Pre-fork worker model is well-understood and production-proven.
- `--access-logfile -` routes access logs to stdout, compatible with container log aggregation.

*Negative trade-offs:*
- Synchronous workers; blocking I/O in route handlers (e.g., long-running DB queries) ties up a worker. Not a concern at "thousands of requests per day" volume with standard indexing.

*Risks and mitigations:*
- **Risk**: Developer accidentally runs `python app.py` instead of `bash start.sh`. **Mitigation**: COMP-001 is the sole documented entry point in README.md, CONTRIBUTING.md, and docker-compose.yml. The `start.sh` script must not be made executable conditionally — it is always the production entry point.

---

### ADR-004 — Credential Management: Environment Variables with Localhost-Only Fallback

**Title:** Runtime Credential Injection via Environment Variables

**Context:**
Test credentials (`TEST_SUPERADMIN_PASSWORD`, `TEST_ADMIN_PASSWORD`, `TEST_USER_PASSWORD`) are currently hardcoded as string literals in `tests/config.py`. This violates REQ-002 and REQ-013, exposes credentials to anyone with repository read access, and causes secret detection scanners to fail. REQ-013 prohibits credentials from appearing in source code, git history, CI logs, or pipeline artifacts.

**Decision:**
Resolve all test credentials from named environment variables at runtime (COMP-006). Permit a documented localhost-only fallback to non-production default values for individual developer convenience. Enforce hard failure (exception) when variables are absent in any non-localhost environment. Existing application secrets (database URL, Flask secret key, OAuth credentials) remain managed via environment variable injection from the deployment platform — this is the existing pattern and is not changed by this branch.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|-------------|------|------|
| **HashiCorp Vault or AWS Secrets Manager** | Industry-standard secret lifecycle management; secret rotation; access audit logs | Significant scope expansion; requires new infrastructure; overkill for the current threat model and team size; explicitly a non-goal in the approved specification |
| **Encrypted `.env` file committed to repository** | Credentials not in plain text in source; developer convenience | Encryption key itself must be managed somewhere; encrypted blob still in git history; adds complexity without meaningfully closing the gap; not compatible with standard secret detection tooling |
| **Do nothing (keep hardcoded literals)** | Zero engineering effort | Violates REQ-002 and REQ-013; credentials leak via git clone; secret detection blocks CI pipeline permanently; constitutes a security exposure |

**Consequences:**

*Positive:*
- No credential literals in any file tracked by git after this change.
- Consistent with how all other application secrets are already managed (environment variable injection).
- Secret detection CI stage will pass (zero findings for credential literals).

*Negative trade-offs:*
- Developers must populate environment variables locally before running tests; one-time setup friction. Mitigated by clear documentation in CONTRIBUTING.md.
- If `.env` files with fallback values are accidentally committed, the fallback protection is undermined. Mitigated by `.gitignore` entry for `.env` files (should already be present; verify and add if missing).

*Risks and mitigations:*
- **Risk**: `is_localhost` detection logic produces a false positive in a shared environment, allowing the fallback to activate silently. **Mitigation**: The detection logic defaults to `False` (non-localhost) in ambiguous cases; CI environments must set `CI=true` (GitLab does this automatically); the fallback values must be non-functional in any shared environment (i.e., they do not correspond to any real account).

---

### ADR-005 — Security Scanning: GitLab Native Templates + pip-audit

**Title:** CI/CD Security Scanning via GitLab SAST and Secret Detection Templates Plus pip-audit

**Context:**
REQ-005 requires three security scanning capabilities: (1) dependency vulnerability scanning that fails on CVE and produces a machine-readable artifact, (2) Python SAST, and (3) git-history secret scanning. These must run before any build artifact is produced. The CI/CD platform is GitLab.

**Decision:**
Use GitLab's built-in `Security/SAST.gitlab-ci.yml` template (Bandit-based for Python) for SAST, GitLab's `Security/Secret-Detection.gitlab-ci.yml` template for secret scanning, and `pip-audit` (invoked as a pipeline shell command) for dependency vulnerability scanning. All three run as jobs in a dedicated `security` stage defined before `build`.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|-------------|------|------|
| **Safety (pypa/safety) instead of pip-audit** | Well-known; PyPI vulnerability database integration | Requires a commercial license for up-to-date database access; free tier is stale; pip-audit uses OSV and PyPI Advisory DB which are freely maintained and current |
| **Snyk as a standalone scanning platform** | Comprehensive; developer-friendly UI; license scanning | Requires Snyk account and token management; external SaaS dependency; adds cost and operational dependency; GitLab native templates cover the stated requirements without external dependencies |
| **Bandit invoked directly (without GitLab template)** | Full control over Bandit configuration and version | GitLab SAST template manages Bandit versioning, report format, and GitLab Security Dashboard integration; no benefit to manual invocation for the current threat model |
| **Do nothing** | Zero effort | Violates REQ-005 and REQ-013; known-CVE dependencies can be deployed; committed secrets are not detected; pipeline produces no security signal |

**Consequences:**

*Positive:*
- GitLab templates are maintained by GitLab; no custom tooling to maintain.
- GitLab Secret Detection scans the full git history by default — satisfying REQ-005's history-scanning requirement without additional configuration.
- `pip-audit` produces a JSON artifact that satisfies the "machine-readable scan report as a pipeline artifact" requirement.

*Negative trade-offs:*
- GitLab SAST and Secret Detection templates are updated by GitLab; a template update could change scanner behaviour or findings without a code change.
- `pip-audit` produces false positives for CVEs in transitive dependencies. **Mitigation**: Accept the friction; CVEs in transitive dependencies should also be remediated (upgrade to a parent version that resolves the transitive dep). If the rate of false positives becomes unacceptable, a `.pip-audit-ignore` file can be introduced in a future branch.

---

### ADR-006 — Input Validation Strategy: Centralized Utility Module

**Title:** Shared Input Validation Utility for All Form-Handling Route Handlers

**Context:**
REQ-008 requires that all user-submitted input is validated before any data is persisted, and that validation failures produce specific, field-identified error messages. The existing ~45–50 route handlers have inconsistent or absent validation — some partially validate, most do not. There is no shared validation abstraction. The choice of validation strategy determines the consistency and maintainability of REQ-008 coverage.

**Decision:**
Introduce a centralized `utils/validation.py` utility module (COMP-010) providing a small set of pure validation functions that return typed error descriptors. Route handlers assemble validator calls using this utility before any database operation. This is a utility module, not a framework — it does not introspect form schemas or auto-discover fields.

**Alternatives Considered:**

| Alternative | Pros | Cons |
|-------------|------|------|
| **WTForms integration** | Declarative form schemas; built-in CSRF protection; Flask-WTF integration | Requires replacing or wrapping all 45–50 existing form handlers with WTForms Form classes — a large refactor that exceeds the scope of this hardening branch and risks introducing regressions across the entire route surface |
| **Pydantic / Flask-Pydantic** | Type-safe validation; automatic coercion; rich error model | Same refactor scope problem as WTForms; introduces a Pydantic dependency; incompatible with the "no breaking changes" compatibility constraint for this branch |
| **Inline validation per route (no shared utility)** | No new abstraction; minimal change | Does not enforce a consistent validation pattern; error message format will diverge across routes; code review cannot systematically verify REQ-008 compliance; does not satisfy the specification's requirement for testable, observable validation behavior |

**Consequences:**

*Positive:*
- Every route handler uses the same error descriptor format — consistent UX across the application.
- `validate_form()` validates all fields before returning errors — users see all errors at once, not one at a time.
- Pure functions are straightforward to unit-test with no Flask app context required.
- Minimal scope — no existing route handler structure is redesigned; only a validation call is added before the persistence block.

*Negative trade-offs:*
- Route handlers must be individually modified to add validation calls. With ~45–50 routes, this is significant but bounded work. Mitigation: The scope is limited to routes that handle form POSTs (not all 45–50 routes handle POSTs with persistent data).
- The utility does not enforce that routes *use* it — a new route can be added without calling `validate_form()`. **Mitigation**: Code review checklist must include verification that all form-handling POST routes call `validate_form()`. This is the same governance gap as the existing RBAC inline enforcement pattern, and is accepted as a known trade-off for this branch scope.

---

## Implementation Guidelines

### File Structure

Every file to be created or modified, with its purpose and component ID:

**New Files:**

| File Path | Purpose | Component |
|-----------|---------|-----------|
| `start.sh` | Production Gunicorn entry point with 120s timeout | COMP-001 |
| `startup_checks.py` | Pre-flight validation of all required config; terminates process on failure | COMP-002 |
| `services/celery_app.py` | Celery application factory; exports `celery_app` instance | COMP-003 |
| `celeryconfig.py` | Celery Beat periodic schedule; defines all task triggers | COMP-005 |
| `services/worker_status.py` | Safe Celery worker status query; never raises; returns degraded state on failure | COMP-011 |
| `utils/validation.py` | Input validation utility functions and error descriptor type | COMP-010 |
| `utils/__init__.py` | Package marker for `utils/` directory (if not already present) | COMP-010 |
| `migrations/README.md` | Migration classification registry; superseded script warnings | COMP-007 |

**Modified Files:**

| File Path | What Changes | What Stays the Same | Component |
|-----------|-------------|---------------------|-----------|
| `start.sh` | Created new | N/A | COMP-001 |
| `app.py` | Remove APScheduler initialization and `app.run()` call; add `from services.celery_app import celery_app` and Celery-Flask binding; call `run_startup_checks(app)` from factory | All Blueprint registrations; all middleware registrations; `Config.init_from_database()`; session handling; all other factory logic | COMP-002, COMP-003 |
| `services/ctask_scheduler.py` | Replace `@scheduler.scheduled_job` decorators with `@celery_app.task(...)` decorators and retry configuration; add structured log statements | All underlying task business logic (email construction, API calls, retry-eligible operations) | COMP-004 |
| `tests/config.py` | Replace credential literals with environment variable resolution and localhost fallback gate | Exported variable names (`TEST_SUPERADMIN_PASSWORD`, etc.); import patterns used by test modules | COMP-006 |
| `.gitlab-ci.yml` | Add `security` stage to `stages:` list before `build`; add `dependency-scan` job; add `include:` for SAST and Secret Detection templates; override template jobs to run in `security` stage | All existing stages, jobs, and pipeline structure | COMP-008 |
| `.gitignore` | Append binary documentation exclusion patterns as a labelled section | All existing ignore entries | COMP-009 |
| `docker-compose.yml` | Change `web` service command to `bash start.sh`; add `redis`, `celery-worker`, `celery-beat` services; add `env_file` or `environment:` blocks using `${VAR}` syntax | All other service definitions; volume mounts; network configuration | COMP-012 |
| `routes/dashboard*.py` | Import and call `get_worker_status()` from COMP-011; pass result to template context | Route paths; authentication checks; all other template context variables | COMP-011 |
| All form-handling `routes/*.py` | Import `validate_form`, `format_error_response` from COMP-010; add validation block before persistence | Route paths; HTTP methods; auth checks; RBAC logic; success response paths; all non-form routes | COMP-010 |
| `CONTRIBUTING.md` | Add section: "Running the Test Suite — Environment Variable Setup"; document `TEST_*` env var names; document localhost fallback values | All existing content | COMP-006 |
| `CLAUDE.md` (if present) | Update credential examples to show env var pattern, not literals | All other content | COMP-006 |

---

### Naming Conventions

Consistent with existing project patterns observed in the context library:

| Category | Convention | Example |
|----------|-----------|---------|
| **Python modules** | `snake_case` | `worker_status.py`, `celery_app.py` |
| **Python functions** | `snake_case` | `get_worker_status()`, `validate_required()` |
| **Python constants / env var names** | `UPPER_SNAKE_CASE` | `TEST_SUPERADMIN_PASSWORD`, `CELERY_BROKER_URL` |
| **Celery task names** | `shiftops.<task_name>` (explicit string) | `"shiftops.email_digest"` |
| **Log event prefixes** | `TASK_`, `STARTUP_`, `WORKER_STATUS_` | `TASK_COMPLETED`, `STARTUP FAILURE` |
| **Component IDs in code comments** | Reference by COMP-NNN where a design decision is non-obvious | `# COMP-002: startup validation` |
| **Blueprint module filenames** | Existing `routes/<domain>.py` pattern | Unchanged |
| **Docker service names** | `kebab-case` | `celery-worker`, `celery-beat` |

---

### Patterns to Use

| Pattern | Rationale |
|---------|-----------|
| **Flask application factory** | Existing pattern in `app.py`; Celery-Flask binding must use this pattern to ensure tasks execute within the Flask app context (access to SQLAlchemy, config, etc.) |
| **Celery `bind=True` on all tasks** | Gives the task access to `self.retry()` and `self.request.retries` for retry counting and logging |
| **`autoretry_for` over manual `self.retry()` calls** | Reduces boilerplate; ensures retry policy is applied consistently even when exceptions are unexpected; cleaner task code |
| **`validate_form()` call before any `db.session` operation** | Enforces the invariant that no partial records are created; must be the first statement in the POST-handling block |
| **`try/except` with explicit exception types in COMP-011** | Only catch known failure modes; log the exception; return degraded state — never silently swallow `Exception` without logging |
| **`sys.exit(1)` in startup checks** | Hard process termination ensures no partially-initialized state; Gunicorn respects non-zero exit and does not continue |
| **Structured log statements with key=value pairs** | Enables log aggregation queries without regex; consistent with `TASK_COMPLETED task=<name> task_id=<id>` pattern |

---

### Patterns to Avoid

| Anti-Pattern | Explanation |
|-------------|-------------|
| **`app.run()` anywhere in production code paths** | Invokes Werkzeug dev server; must only exist inside `if __name__ == '__main__': app.run(debug=True)` guard for local development, if at all; `start.sh` is the sole production entry point |
| **APScheduler `BackgroundScheduler` in any module imported by the web process** | The root cause of the duplicate task execution bug; must not be re-introduced in any form within `app.py` or any module imported at Flask startup |
| **Hardcoded credential literals in any file** | Violates REQ-013; will be detected by secret detection CI stage and block the pipeline |
| **`except Exception: pass` or `except Exception: continue`** | Silent exception swallowing makes failures unobservable; violates REQ-010's observability requirement; the only permitted silent swallow is in COMP-011 where the exception is logged at WARNING before returning the degraded result |
| **Direct `os.environ["VAR"]` in task or model modules** | Environment access must be centralised to COMP-002 (startup) and COMP-006 (test config); task modules receive values through the Flask config or Celery app configuration |
| **Multiple `celery-beat` container instances** | Each Beat instance dispatches independent triggers; two Beat instances produce duplicate task messages; replicas must be constrained to 1 |
| **Database writes before `validate_form()` completes** | Creates partial records; violates REQ-008 acceptance criteria; the validation call must precede all `db.session.add()` and `db.session.commit()` calls |
| **`celery.control.inspect()` without a timeout** | Without a timeout, the inspect call blocks indefinitely if the broker is unreachable; COMP-011 must always pass `timeout=<seconds>` |

---

### New Dependencies

| Library | Version Constraint | Purpose | ADR Reference |
|---------|--------------------|---------|--------------|
| `celery` | `>=5.3,<6.0` (pin minor; avoid Celery 6 API changes) | Distributed task queue; Beat scheduler | ADR-002 |
| `redis` (Python client) | `>=5.0,<6.0` (matches celery[redis] extras) | Redis broker and result backend client for Celery | ADR-002 |
| `gunicorn` | `>=21.0,<23.0` | Production WSGI server | ADR-003 |
| `pip-audit` | Latest stable (installed in CI runner; not in `requirements.txt`) | Dependency vulnerability scanning in CI pipeline | ADR-005 |

**Notes:**
- `celery[redis]` should be added to `requirements.txt` as the extras-enabled form to pull in the Redis transport client.
- `gunicorn` should be added to `requirements.txt` if not already present.
- `pip-audit` is a CI tool, not a runtime dependency; it must not appear in `requirements.txt` (doing so would cause it to be scanned by itself, creating circular logic).
- All version pins must be re-evaluated against the `pip-audit` scan on first pipeline run. Any pinned version with a known CVE must be upgraded before the branch is merged.

---

## Testing Strategy

### Unit Tests

All new utility modules must have standalone unit tests that require no Flask application context or external services.

| Component | Test Target | Test Scenarios |
|-----------|-------------|----------------|
| **COMP-010** `utils/validation.py` | `validate_required()` | Empty string → error; whitespace-only string → error; `None` → error; valid string → `None` |
| **COMP-010** `utils/validation.py` | `validate_not_null()` | `None` → error; `0` / `""` / `False` → `None` (not null); valid value → `None` |
| **COMP-010** `utils/validation.py` | `validate_range()` | Value at min boundary → `None`; value at max boundary → `None`; value below min → error with message containing min/max/received; value above max → error |
| **COMP-010** `utils/validation.py` | `validate_form()` | Single passing validator → empty list; single failing validator → list of one error; multiple validators, one failing → list of one error; multiple validators, all failing → list of all errors (no short-circuit) |
| **COMP-010** `utils/validation.py` | `format_error_response()` | Empty list → `{"errors": []}`; one error → correct structure; multiple errors → all present |
| **COMP-006** `tests/config.py` | `is_localhost` detection | `CI=true` env var set → non-localhost; no CI env vars, loopback hostname → localhost |
| **COMP-006** `tests/config.py` | Credential resolution | Env var set → value returned; env var absent + localhost → fallback returned; env var absent + non-localhost → `EnvironmentError` raised |
| **COMP-002** `startup_checks.py` | `run_startup_checks()` | Missing required env var → `sys.exit(1)` called with logged message naming the var; DB unreachable → `sys.exit(1)` with logged message; Redis unreachable → `sys.exit(1)` with logged message; all checks pass → returns normally |
| **COMP-011** `services/worker_status.py` | `get_worker_status()` | Inspect returns worker data → `available=True` with correct counts; inspect raises `ConnectionError` → `available=False`, `error` field non-None, no exception raised; inspect times out → same degraded result; inspect returns None → `available=False` |

**Test file locations** (following existing project structure):
- `tests/test_validation.py` — COMP-010 tests
- `tests/test_startup_checks.py` — COMP-002 tests
- `tests/test_worker_status.py` — COMP-011 tests
- COMP-006 tests embedded in `tests/test_config.py` or the existing test configuration test file

---

### Integration Tests

| Scenario | What is Tested | Test Approach |
|----------|---------------|---------------|
| **Form submission validation — empty required field** | Full POST request to a form-handling route with a missing required field returns an error response; no database record created | Flask test client; assert response contains error message for the field; assert DB count unchanged |
| **Form submission validation — valid input** | Full POST request with valid data persists the record | Flask test client; assert success response; assert DB record created |
| **Dashboard with worker status unavailable** | Dashboard route returns HTTP 200 when Celery broker is unreachable | Flask test client; mock `services.worker_status.get_worker_status` to return `available=False`; assert response.status_code == 200 |
| **Celery task dispatch** | A task dispatched via `celery_app.send_task()` is received and executed by a worker | Requires a running Redis and Celery worker (Docker); assert task result is SUCCESS; assert structured log entry `TASK_COMPLETED` appears |
| **Celery task retry on transient failure** | A task that raises a retryable exception on first attempt retries and eventually succeeds | Mock external service to fail twice then succeed; assert task result is SUCCESS; assert `TASK_RETRY` log entries appear with correct attempt numbers |
| **Celery deduplication with 3 web workers** | With 3 Gunicorn workers and 1 Beat/1 Celery worker, a scheduled trigger fires exactly once | Requires Docker; trigger one scheduled task; assert exactly one `TASK_COMPLETED` log entry in a 24-hour window |
| **Startup validator — missing env var** | Application fails to start when a required env var is absent | Invoke `run_startup_checks()` with a patched environment missing one variable; assert `SystemExit` raised with code 1 |

---

### E2E Scenarios

| ID | Scenario | Steps | Expected Outcome |
|----|----------|-------|-----------------|
| E2E-001 | Email digest with 3 workers | Start docker-compose with `celery-worker replicas=1`, `web replicas=3`; trigger email digest task; wait 60s | Exactly one email sent; exactly one `TASK_COMPLETED` log entry |
| E2E-002 | CI pipeline blocks on CVE | Add a dependency with a known CVE to `requirements.txt`; push branch; observe pipeline | `dependency-scan` job fails; `pip-audit-report.json` artifact saved; build stage not reached |
| E2E-003 | CI pipeline blocks on committed secret | Commit a file containing a mock credential literal (not a real secret) to a branch; push; observe pipeline | `secret_detection` job fails; build stage not reached; finding reported with file reference |
| E2E-004 | MR self-approval blocked | Author opens MR; author attempts to approve own MR | Approval rejected; approval count remains 0; merge blocked |
| E2E-005 | MR peer approval permits merge | Author opens MR; peer reviewer approves; author merges | Merge completes; branch protection satisfied |
| E2E-006 | Task retries on ServiceNow unavailability | Simulate ServiceNow endpoint returning 503; trigger relevant scheduled task; observe | Task retries up to 3 times at ≥30-second intervals; final `TASK_FAILED` log entry with `attempts_exhausted=3` |
| E2E-007 | Dashboard degrades gracefully | Stop Redis (celery broker); navigate to dashboard | Core dashboard returns HTTP 200; worker status widget shows degraded state; no error propagated to user |
| E2E-008 | Application startup fails on missing env var | Start container with `SECRET_KEY` env var unset | Process exits with code 1; log contains `STARTUP FAILURE: Required environment variable 'SECRET_KEY' is not set.` |

---

### Coverage Approach

| Component | Target Coverage | Rationale |
|-----------|----------------|-----------|
| `utils/validation.py` | ≥95% line coverage | Pure functions; critical correctness boundary; no external dependencies make coverage easy to achieve |
| `startup_checks.py` | ≥90% line coverage | Startup failures have significant operational impact; every check branch must be verified |
| `services/worker_status.py` | ≥90% line coverage | Graceful degradation logic is safety-critical; the "never raise" contract must be verified for all exception types |
| `tests/config.py` | ≥85% line coverage | Security-sensitive; fallback logic must be tested |
| `services/ctask_scheduler.py` (modified) | ≥70% line coverage | Business logic is unchanged; focus on retry decorator paths and log statement coverage |
| `services/celery_app.py` | Integration-tested; unit coverage not required | Configuration module; correctness verified by integration tests |
| `.gitlab-ci.yml`, `.gitignore`, `migrations/README.md`, `start.sh` | Not unit-testable | Correctness verified by E2E scenarios and manual review |

**Overall approach:** This hardening branch does not require full-application coverage uplift. Focus unit testing resources on the three new utility modules (COMP-002, COMP-010, COMP-011) and COMP-006, which contain logic that has clear correctness requirements, security implications, and no existing test coverage. Existing route handler coverage is out of scope except for the specific integration tests verifying form validation behaviour.

---

## Security Considerations

### 1. Credential Leakage in Source Code and Git History

- **Concern**: Test credentials and application secrets committed as literal strings in source files are permanently accessible to anyone with git clone access, including future repository mirrors.
- **Mitigation**: COMP-006 removes all literal credential values from `tests/config.py`. COMP-008 adds GitLab Secret Detection (full history scan) that blocks the pipeline on any credential literal in any commit. The localhost-only fallback values documented in CONTRIBUTING.md must be clearly marked as non-functional in shared environments and must not match any real account credential.
- **OWASP Category**: A07:2021 — Identification and Authentication Failures; A09:2021 — Security Logging and Monitoring Failures (credential exposure is undetected without scanning).

### 2. Dependency Vulnerabilities (CVEs)

- **Concern**: Third-party Python packages in `requirements.txt` may have published CVEs that expose the application to known exploits. Without scanning, vulnerable packages can be deployed silently.
- **Mitigation**: COMP-008 adds `pip-audit` to the `security` stage; the stage fails and blocks build artifact production on any CVE finding. Machine-readable `pip-audit-report.json` artifact is saved for remediation tracking. All new dependencies introduced by this branch (`celery`, `redis`, `gunicorn`) must be scanned before the branch is merged.
- **OWASP Category**: A06:2021 — Vulnerable and Outdated Components.

### 3. Static Application Security Analysis

- **Concern**: Python source code may contain security anti-patterns (SQL injection via string concatenation, use of `eval()`, unsafe deserialization, hardcoded secrets missed by pattern matching) that are not caught by CVE scanning.
- **Mitigation**: COMP-008 includes GitLab SAST (Bandit-based) running in the `security` stage before build. All findings at HIGH severity are blocking. Bandit configuration defaults are accepted per A-003 (sufficient coverage for current threat model).
- **OWASP Category**: A03:2021 — Injection; general SAST coverage.

### 4. User Input Validation (Injection Prevention)

- **Concern**: Unvalidated user input submitted to form handlers can be used for SQL injection, XSS, or data integrity attacks. The existing inline RBAC pattern creates a risk that form-handling routes accept malformed or oversized input without validation.
- **Mitigation**: COMP-010 provides centralized input validation enforced before any database operation. All form-handling POST routes must call `validate_form()` before any SQLAlchemy write. SQLAlchemy's parameterized query model already prevents SQL injection from ORM-level operations; COMP-010 addresses data integrity and application-level constraint violations.
- **OWASP Category**: A03:2021 — Injection; A04:2021 — Insecure Design (business logic validation).

### 5. Authentication Token Management

- **Concern**: Session tokens must remain valid and enforceable; changes to the task infrastructure must not affect the per-request `validate_session()` middleware.
- **Mitigation**: The session token validation mechanism (`validate_session()` middleware, `session_tokens` table, administrator-forced revocation) is explicitly unchanged by this branch (compatibility constraint). COMP-002 validates database reachability at startup — if the database is unreachable, the session validation mechanism cannot function and the application must not start. No Celery task reads or writes session token records.
- **OWASP Category**: A07:2021 — Identification and Authentication Failures.

### 6. PII Handling in Task Execution

- **Concern**: Email digest tasks and ServiceNow polling tasks process user data (shift records, incident data, email addresses) as part of their business logic. This PII must not appear in task execution logs or the Celery result backend.
- **Mitigation**: The structured log contract for COMP-004 defines log messages using only task name, task ID, attempt count, and error class — never user data or record content. The Celery result backend stores task return values; task functions must return only status metadata (not record contents) in their return dict. PII that must be referenced within a task should be passed as database record IDs, not as serialized user data in task arguments (which are stored in Redis).
- **OWASP Category**: A02:2021 — Cryptographic Failures (data exposure); GDPR / privacy considerations.

### 7. CI/CD Pipeline Security

- **Concern**: Pipeline logs and pipeline artifacts could expose credentials if environment variable values are accidentally echoed or if pip-audit includes them in its report.
- **Mitigation**: Test credentials are injected as masked CI/CD variables (GitLab's masked variable feature suppresses their value in pipeline logs). `pip-audit-report.json` contains only package names, versions, and CVE IDs — no credentials. The `dependency-scan` job must not print `pip install` output verbosely (use `--quiet` flag or redirect to `/dev/null`).
- **OWASP Category**: A09:2021 — Security Logging and Monitoring Failures.

### 8. Authorization — Route-Level Gaps (Existing Risk, Not Introduced by This Branch)

- **Concern**: The existing pattern of inline RBAC (no shared `@require_role` decorator) creates a risk that new routes added by this branch (none) or future branches could be added without authorization checks.
- **Mitigation**: This branch adds zero new routes, so no new authorization gaps are introduced. COMP-010 (validation utility) is not an authorization control. The existing RBAC gap is documented in the approved specification as a known risk and is not in scope for this branch. Code review checklist for future branches must explicitly check for `@require_role` absence.
- **OWASP Category**: A01:2021 — Broken Access Control.

---

## Error Handling Strategy

### Error Classification and Strategy Mapping

| Error Category | Strategy | Implementation |
|----------------|----------|---------------|
| Missing required env var / DB unreachable at startup | **Abort (Strategy A)** | `sys.exit(1)` in COMP-002; logged at CRITICAL before exit; no partial startup |
| Transient external service failure in background task | **Retry (Strategy C)** | Celery `autoretry_for`, `max_retries=3`, `default_retry_delay=30` in COMP-004; logged at WARNING per attempt |
| Exhausted retries in background task | **Terminal Failure** | Exception propagates; Celery records FAILURE in result backend; logged at ERROR with `TASK_FAILED` prefix |
| Celery worker / broker unreachable during dashboard request | **Graceful Degrade (Strategy D)** | COMP-011 catches all exceptions; returns `available=False`; dashboard renders degraded UI; core routes unaffected |
| User input validation failure on form submission | **Reject with Message** | COMP-010 `validate_form()` returns errors; route handler returns error response without DB write; no retry |
| Database error after validation passes (unexpected) | **Surface as 500** | SQLAlchemy exception propagates to Flask error handler; transaction rolled back; user sees generic error message; full exception logged internally |
| Audit-critical operation failure (handover submission) | **Retry then Abort** | If invoked as Celery task: retry (Strategy C); if invoked synchronously in a route: exception raised → transaction rolled back → 500 response → full exception logged; never silent |

### Error Propagation Chain

```
User Form Submission (POST):
  Route handler → COMP-010 validate_form()
    → [errors present] → return error response immediately (no DB write, no propagation)
    → [valid] → SQLAlchemy operation
        → [DB exception] → SQLAlchemy rolls back transaction
                         → exception propagates to Flask error handler
                         → Flask renders 500 (or error template)
                         → exception logged at ERROR with full traceback
                         → user sees "An error occurred" message

Background Task Execution:
  Celery Beat → Redis → Celery worker → Task function
    → [ExternalServiceError] → logged at WARNING (TASK_RETRY)
                              → retry after 30s (up to 3 times)
                              → [eventual success] → logged at INFO (TASK_COMPLETED)
                              → [retries exhausted] → logged at ERROR (TASK_FAILED)
                                                    → FAILURE state in result backend
                                                    → no further automatic retry
                                                    → web tier unaffected

Dashboard Request:
  Route handler → COMP-011 get_worker_status()
    → [broker/worker available] → WorkerStatusResult(available=True) → normal UI
    → [any exception] → caught internally → logged at WARNING
                      → WorkerStatusResult(available=False) → degraded UI widget
                      → route continues → HTTP 200 returned

Application Startup:
  COMP-002 run_startup_checks()
    → [any required config absent] → CRITICAL log → sys.exit(1) → process terminates
    → [all checks pass] → returns normally → application starts
```

### User-Facing Error Messages vs. Internal Logging

| Error Type | User-Facing Message | Internal Log |
|-----------|-------------------|-------------|
| Validation failure | Specific: `"<Field Name> is required and must not be empty."` | Not logged (expected business event) |
| Out-of-range value | Specific: `"<Field Name> must be between X and Y. Received: Z."` | Not logged |
| Worker status unavailable | Degraded UI indicator only; no error text shown to user | `WARNING: WORKER_STATUS_CHECK_FAILED: <exception>` |
| Database error during request | Generic: `"An error occurred. Please try again."` | `ERROR: <full exception with traceback>` |
| Startup configuration failure | Not shown to users (process exits before accepting traffic) | `CRITICAL: STARTUP FAILURE: Required environment variable '<NAME>' is not set.` |
| Task transient failure (retry) | Not shown to users | `WARNING: TASK_RETRY task=<name> task_id=<id> attempt=<N> reason=<error>` |
| Task terminal failure | Not shown to users | `ERROR: TASK_FAILED task=<name> task_id=<id> attempts_exhausted=3 error=<str>` |

### Retry Strategy

| Trigger | Max Retries | Delay | Backoff | Terminal State |
|---------|------------|-------|---------|----------------|
| Transient external service error in Celery task | 3 | 30 seconds (minimum, flat) | None (no exponential backoff — flat interval satisfies REQ-010; exponential backoff is a future optimization) | FAILURE recorded in result backend; `TASK_FAILED` log entry |
| Database reconnection (SQLAlchemy connection pool) | Managed by SQLAlchemy pool; not application-level | N/A | N/A | Connection error propagates to caller |

### Graceful Degradation Contract

When the Celery broker or worker status endpoint is unavailable:
- `routes/dashboard*.py` continues to serve requests normally.
- COMP-011 `get_worker_status()` returns `WorkerStatusResult(available=False)` within the configured timeout (default 1 second).
- The `1.0` second timeout ensures that a broker outage does not add more than 1 second of latency to dashboard page loads.
- Only the worker status UI widget reflects the degraded state. All other dashboard functionality (shift data, incident stats, KPIs) is unaffected.
- This behaviour is measurable: during a simulated broker outage, `GET /dashboard` must return HTTP 200 with a response time within normal parameters (not delayed by the 1-second timeout beyond the acceptable web response budget). The 1-second timeout is the designed upper bound for degradation latency.

---

*End of Architecture Design Specification — CTCOAMSHM-7*


---
## Implementation Plan

## Summary

This branch closes 8 medium-severity production-readiness gaps across infrastructure, security, process, and documentation in the ShiftOps Flask monolith (CTCOAMSHM-7). The work separates background task execution from the web process via a Celery + Redis worker architecture, replaces the Flask development server with Gunicorn, hardens credentials and CI/CD scanning, and adds centralised input validation — all as additive or internal-only changes with zero modifications to existing route contracts, schemas, or RBAC definitions. No new user-visible features are introduced.

---

## Key Requirements & Constraints

| ID | Priority | Description |
|----|----------|-------------|
| REQ-001 | P0 | Scheduled background tasks (digests, polling, retries) shall execute in a process isolated from the web-serving process; multiple concurrent Gunicorn workers must not produce duplicate executions. |
| REQ-002 | P0 | All test-suite authentication credentials shall be resolved from named environment variables; a localhost-only fallback to documented defaults is the sole permitted exception. |
| REQ-003 | P0 | All production HTTP traffic shall be served by a production-grade WSGI server with ≥120-second request timeout; the Flask development server shall never be the production entry point. |
| REQ-004 | P1 | The repository shall contain a human-readable document classifying every migration script as: applied to production, superseded (do not re-apply), or environment-specific; all future schema changes shall use the versioned migration toolchain exclusively. |
| REQ-005 | P0 | The CI/CD pipeline shall enforce a security stage before any build artifact is produced, comprising: (1) dependency CVE scan with machine-readable artifact, (2) Python SAST, and (3) full git-history secret scanning. |
| REQ-006 | P1 | The repository shall contain no tracked binary documentation files (PDF, DOCX, XLSX, PPTX, PPT); these patterns shall be permanently excluded via repository ignore configuration. |
| REQ-007 | P1 | Every merge request targeting the protected main branch shall require at least one peer-reviewer approval; authors shall be prohibited from self-approving. |
| REQ-008 | P0 | All user-submitted form input shall be validated on submission; any failure shall return a specific, field-identified, human-readable error message with no partial record persisted. |
| REQ-009 | P0 | Zero duplicate task executions shall be observed when the web-serving process is scaled to three or more concurrent workers, measured over a 24-hour observation window. |
| REQ-010 | P1 | Scheduled tasks encountering a transient external-service failure shall auto-retry up to 3 times with ≥30-second delay between attempts; retry count and final status shall be observable without manual log parsing. |
| REQ-011 | P0 | The application shall terminate immediately at startup with a logged, human-readable error when any required configuration value is absent or any critical external service is unreachable; no partial startup state is permitted. |
| REQ-012 | P1 | A failure of any non-critical background instrumentation service (e.g., worker status queries) shall not propagate to the web tier; core routes shall remain fully functional during an instrumentation outage. |
| REQ-013 | P0 | Authentication credentials shall never appear in source code, git history, CI/CD logs, or pipeline artifacts; the sole exception is an explicitly documented localhost-only developer fallback value. |

---

## Architecture Summary

The design adopts a **Process-Isolated Worker Architecture** layered on the existing Flask SSR monolith, requiring no changes to route contracts, schemas, session formats, or RBAC definitions.

**Key Design Decisions (ADRs):**

| ADR | Decision | Rationale |
|-----|----------|-----------|
| ADR-001 | Process-isolated Celery worker + Redis broker | Eliminates APScheduler co-location with Gunicorn workers, the root cause of duplicate task execution on scale-out. Distributed-lock and cron-container alternatives were rejected as fragile or lacking retry/observability primitives. |
| ADR-002 | Celery with Redis as both broker and result backend | Satisfies REQ-009/REQ-010 retry semantics natively via `autoretry_for`, `max_retries`, and `default_retry_delay` parameters; `celery.control.inspect` delivers COMP-011 worker status with a single call; lower operational footprint than RabbitMQ at "thousands of requests/day" volume. |
| ADR-003 | Gunicorn via `start.sh` as sole production entry point | Pre-existing in project context; `--timeout 120` satisfies REQ-003 out-of-the-box; pre-fork worker model is production-proven; eliminates all `app.run()` / Werkzeug dev-server code paths. |
| ADR-004 | Environment variable injection with localhost-only fallback | Consistent with existing application secret management; eliminates credential literals from source; `is_localhost` detection defaults to `False` in ambiguous cases to prevent fallback activation in shared environments. |
| ADR-005 | GitLab SAST + Secret Detection templates + `pip-audit` | Platform-native templates (no external SaaS dependency); `pip-audit` uses OSV/PyPI Advisory DB (free, current); JSON artifact satisfies machine-readable report requirement; full git-history scan is default behaviour of the Secret Detection template. |
| ADR-006 | Centralised `utils/validation.py` utility module | Pure functions with zero Flask-context dependency; `validate_form()` validates all fields in one pass (no short-circuit); minimal scope — routes add a single call before persistence, no form schema redesign required. |

**Component Structure:**

| Component | File(s) | Responsibility |
|-----------|---------|---------------|
| COMP-001 | `start.sh` | Gunicorn production entry point; 120s timeout; no dev-server fallback |
| COMP-002 | `startup_checks.py` | Pre-flight env var + DB + Redis reachability checks; `sys.exit(1)` on failure |
| COMP-003 | `services/celery_app.py` | Celery application factory; Flask-Celery binding; broker/backend config |
| COMP-004 | `services/ctask_scheduler.py` (modified) | APScheduler jobs replaced with `@celery_app.task` decorators; retry policy; structured `TASK_*` log contract |
| COMP-005 | `celeryconfig.py` | Celery Beat periodic schedule; single authoritative trigger source |
| COMP-006 | `tests/config.py` (modified) | Env-var credential resolution; localhost fallback gate; `EnvironmentError` on absent vars in CI/prod |
| COMP-007 | `migrations/README.md` | Migration classification registry; superseded-script warnings; future migration policy |
| COMP-008 | `.gitlab-ci.yml` (modified) | `security` stage before `build`; `dependency-scan` + SAST + Secret Detection jobs |
| COMP-009 | `.gitignore` (modified) | Binary documentation file exclusion patterns; `git rm --cached` one-time cleanup |
| COMP-010 | `utils/validation.py` | Pure validation functions; typed `ValidationError` descriptor; `validate_form()` multi-field pass |
| COMP-011 | `services/worker_status.py` | Safe Celery worker status query; 1s timeout; never raises; returns `available=False` on any failure |
| COMP-012 | `docker-compose.yml` (modified) | Adds `redis`, `celery-worker`, `celery-beat` services; `web` command changed to `bash start.sh`; `celery-beat` constrained to `replicas: 1` |
| COMP-013 | GitLab project settings | Protected branch: no direct pushes; 1 required approval; self-approval disabled; approvals reset on new commits |

---

## Pre-Implementation Baseline

Run the following command before making any changes and save the output as the reference baseline. All tasks must eventually leave the test suite in a state that is equal to or better than this baseline.

```bash
pytest tests/ -v --tb=short 2>&1 | tee baseline_test_results.txt; echo "Exit code: $?"
```

---

## Task Breakdown

| Task ID | Title | Dependencies | Effort (days) | Component | Type |
|---------|-------|--------------|---------------|-----------|------|
| T-001 | Verify pre-implementation test baseline and record results | — | 0.25 | — | config |
| T-002 | Append binary documentation exclusion patterns to `.gitignore` | T-001 | 0.25 | COMP-009 | config |
| T-003 | Remove tracked binary documentation files from git tracking via `git rm --cached` | T-002 | 0.25 | COMP-009 | modify |
| T-004 | Author `migrations/README.md` migration classification document | T-001 | 0.5 | COMP-007 | new |
| T-005 | Configure GitLab branch protection (no direct push to main) and MR approval rules (1 peer required, self-approval disabled) | T-001 | 0.25 | COMP-013 | config |
| T-006 | Update `CONTRIBUTING.md` and `CLAUDE.md` with env var credential setup instructions and documented localhost fallback values | T-001 | 0.25 | COMP-006 | modify |
| T-007 | Add `celery[redis]` and `gunicorn` to `requirements.txt`; remove `APScheduler` if present as a standalone entry | T-001 | 0.25 | COMP-003, COMP-001 | modify |
| T-008 | Implement Celery application factory (`services/celery_app.py`) with broker/backend config, serialiser settings, and Flask app-context binding pattern | T-007 | 0.5 | COMP-003 | new |
| T-009 | Implement Celery Beat periodic schedule configuration (`celeryconfig.py`) with all existing task triggers migrated from APScheduler, `replicas: 1` constraint noted | T-008 | 0.5 | COMP-005 | new |
| T-010 | Refactor `services/ctask_scheduler.py`: replace all `@scheduler.scheduled_job` decorators with `@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, autoretry_for=(...))` decorators; add structured `TASK_STARTED / TASK_COMPLETED / TASK_RETRY / TASK_FAILED` log statements; ensure task return values contain only status metadata (no PII) | T-008, T-009 | 1.5 | COMP-004 | modify |
| T-011 | Implement production WSGI entry point script (`start.sh`) invoking Gunicorn with `-w 1`, `-b 0.0.0.0:5000`, `--timeout 120`, `--access-logfile -`, `app:app`; no dev-server fallback path | T-007 | 0.25 | COMP-001 | new |
| T-012 | Implement application startup validator (`startup_checks.py`) with ordered checks for required env vars, database reachability, and Redis/broker reachability; `sys.exit(1)` with `CRITICAL` log on any failure | T-008 | 0.5 | COMP-002 | new |
| T-013 | Modify `app.py`: remove APScheduler initialisation and `app.run()` call; add Celery-Flask factory binding; call `run_startup_checks(app)` after config loading and before route registration | T-008, T-012 | 0.5 | COMP-002, COMP-003 | modify |
| T-014 | Implement test credential resolver in `tests/config.py`: replace all credential literals with `os.environ.get()` resolution; implement `is_localhost` detection defaulting to `False` in ambiguous cases; raise `EnvironmentError` naming the missing variable when absent in non-localhost environments | T-006 | 0.5 | COMP-006 | modify |
| T-015 | Create `utils/__init__.py` package marker and implement `utils/validation.py` with `validate_required`, `validate_not_null`, `validate_range`, `validate_max_length`, `validate_form`, and `format_error_response` pure functions; define `ValidationError` typed descriptor | T-001 | 0.5 | COMP-010 | new |
| T-016 | Audit all form-handling POST route handlers across `routes/*.py`; integrate `validate_form()` call before any `db.session` operation in each; update route templates to render field-level error messages; ensure no partial records are persisted on validation failure | T-015, T-013 | 2.0 | COMP-010 | modify |
| T-017 | Implement worker status instrumentation adapter (`services/worker_status.py`): call `celery_app.control.inspect(timeout=1.0).active()`; catch all exceptions; log at `WARNING`; return `WorkerStatusResult(available=False)` on any failure without re-raising | T-008 | 0.25 | COMP-011 | new |
| T-018 | Integrate `get_worker_status()` into `routes/dashboard*.py` route handlers; pass `WorkerStatusResult` to template context; update dashboard templates to conditionally render worker stats or degraded indicator based on `available` flag | T-017, T-013 | 0.5 | COMP-011 | modify |
| T-019 | Update `docker-compose.yml`: change `web` service command from `python app.py` to `bash start.sh`; add `redis` service (pinned image); add `celery-worker` service; add `celery-beat` service with explicit `replicas: 1` and inline comment warning against scaling; add `env_file` / `environment:` blocks using `${VAR}` syntax across all services; add `depends_on` chains | T-011, T-008, T-009, T-010 | 0.5 | COMP-012 | modify |
| T-020 | Add `security` stage to `stages:` list before `build` in `.gitlab-ci.yml`; add `dependency-scan` job (pip-audit, JSON artifact, `allow_failure: false`); include `Security/SAST.gitlab-ci.yml` and `Security/Secret-Detection.gitlab-ci.yml` templates; override both template jobs to run in `security` stage | T-007 | 0.5 | COMP-008 | modify |
| T-021 | Write unit tests for `utils/validation.py` covering all boundary cases: empty/whitespace/null inputs, range boundaries, max-length boundary, multi-error non-short-circuit behaviour of `validate_form`, and `format_error_response` structure | T-015 | 0.5 | COMP-010 | test |
| T-022 | Write unit tests for `startup_checks.py` covering: missing env var → `SystemExit(1)` with log naming the variable; DB unreachable → `SystemExit(1)`; Redis unreachable → `SystemExit(1)`; all checks pass → normal return | T-012 | 0.25 | COMP-002 | test |
| T-023 | Write unit tests for `services/worker_status.py` covering: healthy inspect → `available=True` with correct counts; `ConnectionError` → `available=False` no exception raised; timeout → `available=False` no exception raised; `None` response → `available=False` | T-017 | 0.25 | COMP-011 | test |
| T-024 | Write unit tests for `tests/config.py` credential resolver covering: env var set → value returned; env var absent + `is_localhost=True` → documented fallback; env var absent + `is_localhost=False` → `EnvironmentError` naming the variable; `CI=true` env var → `is_localhost=False` | T-014 | 0.25 | COMP-006 | test |
| T-025 | Write integration tests for form-handling route validation using Flask test client: missing required field → error response with field name, no DB record created; valid input → success response, record persisted; multiple field failures → all errors returned in single response | T-016 | 1.0 | COMP-010 | test |
| T-026 | Write integration tests for dashboard graceful degradation: mock `get_worker_status` returning `available=False`; assert dashboard route returns HTTP 200; assert core template renders without error; assert only instrumentation widget reflects degraded state | T-018 | 0.5 | COMP-011 | test |
| T-027 | Write integration tests for Celery task dispatch and retry: mock external service to fail twice then succeed; assert `TASK_RETRY` log entries at correct attempt numbers; assert task reaches `SUCCESS` state; assert `TASK_FAILED` log and `FAILURE` state when all retries are exhausted | T-010, T-019 | 0.75 | COMP-004 | test |

## Implementation Steps


### T-001: Verify pre-implementation test baseline and record results (config) —
- **Purpose**: Capture a clean test-suite pass/fail baseline before any code changes, so regressions introduced by later tasks can be detected unambiguously.
- **File(s)**: No file changes. Record output to a local scratch file (e.g. `baseline_test_results.txt`) that is **not** committed.
- **Dependencies**: None
- **Key notes**:
  - Run the full test suite exactly as CI would: activate the project virtualenv, export any required env vars (use localhost fallback values documented in `CONTRIBUTING.md` / `CLAUDE.md`), then execute the test runner.
  - Record: total tests, passed, failed, errored, skipped, and any pre-existing failures with their test IDs.
  - Pre-existing failures must be listed explicitly so they are not confused with regressions in subsequent tasks.
  - Do **not** fix any failing tests at this stage.
- **Acceptance criteria**: Establishes the baseline required before REQ-002, REQ-005, REQ-008 work begins; no REQ directly, but gates all subsequent tasks.
- **Verify**:
  ```bash
  pytest --tb=short -q 2>&1 | tee baseline_test_results.txt
  echo "Exit code: $?"
  ```

---

### T-002: Append binary documentation exclusion patterns to `.gitignore` (config) COMP-009
- **Purpose**: Prevent binary documentation files from ever being committed to the repository.
- **File(s)**: `.gitignore`
- **Dependencies**: T-001
- **Key notes**:
  - Append the following block at the end of `.gitignore`; do **not** alter existing entries:
    ```gitignore
    # Binary documentation files (REQ-006)
    *.pdf
    *.doc
    *.docx
    *.xls
    *.xlsx
    *.ppt
    *.pptx
    ```
  - Each pattern must be on its own line with the comment header above the block so the intent is clear in code review.
  - Confirm no existing `.gitignore` section already contains these patterns (search before appending to avoid duplicates).
- **Acceptance criteria**: REQ-006 — no binary doc files tracked; patterns present in `.gitignore`.
- **Verify**:
  ```bash
  grep -E '\*\.(pdf|doc|docx|xls|xlsx|ppt|pptx)' .gitignore
  # Each of the 7 patterns must appear in output
  git check-ignore -v some_test.pdf  # must print the matching rule
  ```

---

### T-003: Remove tracked binary documentation files from git tracking via `git rm --cached` (modify) COMP-009
- **Purpose**: Untrack any binary documentation files that are currently indexed in git without deleting them from the working directory.
- **File(s)**: `.gitignore` (already updated in T-002); git index only — no source file changes.
- **Dependencies**: T-002
- **Key notes**:
  - Run the command against all matching extensions. Use `--cached` so local copies are preserved:
    ```bash
    git rm --cached -r --ignore-unmatch -- '*.pdf' '*.doc' '*.docx' '*.xls' '*.xlsx' '*.ppt' '*.pptx'
    ```
  - If any files are removed from the index, commit **only** the removal with message: `chore: untrack binary documentation files (REQ-006)`.
  - If no files match, no commit is necessary — document this in the MR description.
  - Do **not** use `git rm` without `--cached`; working-directory files must not be deleted.
  - After the commit, run `git ls-files | grep -E '\.(pdf|doc|docx|xls|xlsx|ppt|pptx)$'` to confirm zero tracked matches.
- **Acceptance criteria**: REQ-006 — no tracked binary doc files remain in the repository index.
- **Verify**:
  ```bash
  git ls-files | grep -E '\.(pdf|doc|docx|xls|xlsx|ppt|pptx)$'
  # Must produce zero output
  ```

---

### T-004: Author `migrations/README.md` migration classification document (new) COMP-007
- **Purpose**: Provide a single authoritative registry that classifies every existing migration script so that DB state is unambiguous and future changes are governed by Alembic.
- **File(s)**: `migrations/README.md` (new file)
- **Dependencies**: T-001
- **Key notes**:
  - List **every** `.sql`, `.py`, or other migration file found under `migrations/` in a Markdown table with columns: `Filename | Status | Description | Applied-By | Notes`.
  - Valid `Status` values (exactly these strings): `APPLIED`, `SUPERSEDED`, `ENV-SPECIFIC`.
    - `APPLIED` — script has been run against production and must not be re-executed.
    - `SUPERSEDED` — replaced by a later migration; running it would cause errors or data loss.
    - `ENV-SPECIFIC` — only relevant to a specific environment (e.g. seeding local dev data); never run in production.
  - Include a **Policy** section stating: *"All future schema changes must be implemented as Alembic migrations. Ad-hoc SQL scripts are prohibited."*
  - Include a **How to run** section with the standard `flask db upgrade` / `alembic upgrade head` command.
  - Use a date column (`Classified-On`) set to today's date (2026-05-02) for every entry.
  - Do not invent statuses for unknown scripts — flag them `ENV-SPECIFIC` with a `Needs-review` note rather than guessing.
- **Acceptance criteria**: REQ-004 — `migrations/README.md` exists; every migration file is classified; policy statement present.
- **Verify**:
  ```bash
  # Confirm file exists and contains required table columns
  grep -E 'APPLIED|SUPERSEDED|ENV-SPECIFIC' migrations/README.md
  # List migration files vs README entries — counts must match
  ls migrations/*.sql migrations/*.py 2>/dev/null | wc -l
  grep -c '|' migrations/README.md
  ```

---

### T-005: Configure GitLab branch protection and MR approval rules (config) COMP-013
- **Purpose**: Enforce peer code review on `main` — no direct pushes, at least one non-author approval required, self-approval disabled.
- **File(s)**: GitLab project settings (UI / API — no repository file changes).
- **Dependencies**: T-001
- **Key notes**:
  - **Protected branch** (`Settings → Repository → Protected Branches`):
    - Branch: `main`
    - Allowed to merge: `Developers + Maintainers`
    - Allowed to push: `No one` (disables direct push for all roles including Maintainers)
    - Allowed to force-push: **disabled**
  - **Approval rules** (`Settings → Merge Requests → Approval Rules`):
    - Add rule: name `Peer Review`, approvals required: `1`, eligible approvers: `All Members` (or a dedicated reviewer group).
    - **Prevent approval by author**: **enabled**.
    - **Prevent approval by MR committers**: **enabled** (if available in the GitLab tier).
    - **Reset approvals on new commits**: **enabled**.
  - Document the configuration applied (GitLab tier, exact settings, date) in a comment on the implementation MR for audit purposes.
  - If GitLab API is used instead of the UI, use the `POST /projects/:id/protected_branches` and `POST /projects/:id/approval_rules` endpoints with appropriate tokens — store the token in a CI variable, never in the MR diff.
- **Acceptance criteria**: REQ-007 — MR to `main` requires ≥1 peer approval; self-approval prohibited; direct push to `main` blocked.
- **Verify**:
  ```bash
  # Via GitLab API (replace PROJECT_ID and TOKEN)
  curl --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
    "https://<gitlab-host>/api/v4/projects/<PROJECT_ID>/protected_branches/main" \
    | python3 -m json.tool
  # Confirm: push_access_levels is empty or has access_level=0
  # Confirm: merge_access_levels contains Developer/Maintainer
  ```

---

### T-006: Update `CONTRIBUTING.md` and `CLAUDE.md` with env var credential setup (modify) COMP-006
- **Purpose**: Document the required environment variables, how to set them for local development, and the explicit localhost-only fallback values, so engineers never need to hard-code credentials.
- **File(s)**: `CONTRIBUTING.md`, `CLAUDE.md`
- **Dependencies**: T-001
- **Key notes**:
  - Add a **"Credential Setup"** section to both files. Content must include:
    1. A table listing every env var the application and test suite require (e.g. `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `REDIS_URL`, `SECRET_KEY` — enumerate all from the codebase).
    2. The documented localhost fallback value for each var (e.g. `DB_HOST=localhost`, `DB_PORT=3306`, `REDIS_URL=redis://localhost:6379/0`). These are the **only** values that may ever be committed to source.
    3. A `.env.example` snippet showing the export syntax.
    4. An explicit warning: *"Never commit actual credentials. In any non-localhost environment the test suite will raise `EnvironmentError` if a required variable is absent."*
  - `CONTRIBUTING.md` should additionally include a step-by-step *"Local environment setup"* numbered list.
  - `CLAUDE.md` should include a brief *"Environment variables"* paragraph cross-referencing `CONTRIBUTING.md`.
  - Do **not** create a committed `.env` file — only `.env.example` with placeholder/fallback values.
- **Acceptance criteria**: REQ-002, REQ-013 — credentials never in source; localhost fallback values documented.
- **Verify**:
  ```bash
  grep -n 'DB_PASSWORD\|SECRET_KEY\|REDIS_URL' CONTRIBUTING.md CLAUDE.md
  # Must show documented entries, not real credential values
  git diff HEAD -- CONTRIBUTING.md CLAUDE.md  # review for no real secrets
  ```

---

### T-007: Add `celery[redis]` and `gunicorn` to `requirements.txt`; remove standalone `APScheduler` (modify) COMP-003, COMP-001
- **Purpose**: Introduce the production task-queue and WSGI server dependencies; remove the scheduler dependency being replaced.
- **File(s)**: `requirements.txt`
- **Dependencies**: T-001
- **Key notes**:
  - Add exactly these lines (pinned to latest stable at time of implementation; use `pip index versions` to confirm):
    ```
    celery[redis]>=5.3,<6.0
    gunicorn>=21.2,<23.0
    ```
  - Search for `APScheduler` (case-insensitive) in `requirements.txt`. If found as a standalone entry (not a transitive comment), **remove** that line. If `APScheduler` appears in other files (e.g. `requirements-dev.txt`), leave those untouched — only `requirements.txt` is in scope here.
  - Do **not** pin to exact patch versions at this stage — range pinning allows security patches without MR churn.
  - After editing, run `pip install -r requirements.txt` in the virtualenv and confirm no dependency conflicts.
  - The `celery[redis]` extra installs `redis` (the Python client) — do not add `redis` separately.
- **Acceptance criteria**: REQ-001 (Celery available), REQ-003 (Gunicorn available); APScheduler removed from primary dependencies.
- **Verify**:
  ```bash
  pip install -r requirements.txt
  python -c "import celery, redis, gunicorn; print('OK')"
  grep -i apscheduler requirements.txt  # must produce no output
  ```

---

### T-008: Implement Celery application factory (`services/celery_app.py`) (new) COMP-003
- **Purpose**: Create the single, importable `celery_app` instance that all task definitions and the beat schedule will reference; bind it to the Flask application context.
- **File(s)**: `services/celery_app.py` (new file)
- **Dependencies**: T-007
- **Key notes**:
  - Read `REDIS_URL` from `os.environ` (no default — absence is caught by `startup_checks.py` in T-012).
  - Instantiate: `celery_app = Celery('app', broker=REDIS_URL, backend=REDIS_URL)`.
  - Apply configuration via `celery_app.config_from_object('celeryconfig')` — this references the file created in T-009.
  - Set serialiser settings explicitly to prevent security issues:
    ```python
    celery_app.conf.update(
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        result_expires=86400,  # 24 hours in seconds (REQ — TTL ≥24h)
        timezone='UTC',
        enable_utc=True,
    )
    ```
  - Implement a `init_celery(app)` function that binds the Flask app context so tasks can call `db.session` safely:
    ```python
    def init_celery(flask_app):
        class ContextTask(celery_app.Task):
            def __call__(self, *args, **kwargs):
                with flask_app.app_context():
                    return super().__call__(*args, **kwargs)
        celery_app.Task = ContextTask
        return celery_app
    ```
  - Export only `celery_app` and `init_celery` at module level.
  - Do **not** import any Flask route modules or db models here — keep this factory side-effect-free.
- **Acceptance criteria**: REQ-001 — Celery factory importable; REQ-009 — single instance guarantees no duplicate task registration.
- **Verify**:
  ```bash
  python -c "from services.celery_app import celery_app, init_celery; print(celery_app.conf.task_serializer)"
  # Must print: json
  python -c "from services.celery_app import celery_app; print(celery_app.backend)"
  # Must print the Redis backend URL
  ```

---

### T-009: Implement Celery Beat periodic schedule configuration (`celeryconfig.py`) (new) COMP-005
- **Purpose**: Define all periodic task triggers in one place, replacing APScheduler's schedule; enforce the single-beat-instance constraint via documentation and compose config.
- **File(s)**: `celeryconfig.py` (new file, project root)
- **Dependencies**: T-008
- **Key notes**:
  - Inspect `services/ctask_scheduler.py` and enumerate every `@scheduler.scheduled_job` trigger (interval, cron expression, etc.) before writing this file.
  - Translate each APScheduler trigger to a `beat_schedule` entry:
    ```python
    beat_schedule = {
        '<original-job-id>': {
            'task': 'services.ctask_scheduler.<function_name>',
            'schedule': crontab(...) | timedelta(seconds=...),
            'options': {'expires': <seconds>},  # prevent stale task pile-up
        },
        # ... one entry per APScheduler job
    }
    ```
  - Use `crontab` from `celery.schedules` for cron-style triggers; use `timedelta` or integer seconds for interval triggers.
  - Add a top-level comment block:
    ```python
    # WARNING: celery-beat MUST run as a single instance (replicas=1).
    # Running multiple beat instances causes duplicate task scheduling (violates REQ-001, REQ-009).
    # See docker-compose.yml celery-beat service for the deploy.replicas=1 constraint.
    ```
  - Set `beat_schedule_filename = '/tmp/celerybeat-schedule'` to avoid writing the schedule database to the project root.
  - Do **not** define task function bodies here — only schedule metadata.
- **Acceptance criteria**: REQ-001 — tasks isolated to worker process; REQ-009 — single beat instance documented and enforced; all existing APScheduler jobs migrated.
- **Verify**:
  ```bash
  python -c "import celeryconfig; print(list(celeryconfig.beat_schedule.keys()))"
  # Must print all migrated job names — count must match original APScheduler job count
  python -c "from celery.schedules import crontab; import celeryconfig"  # must not raise
  ```

---

### T-010: Refactor `services/ctask_scheduler.py`: APScheduler → Celery tasks (modify) COMP-004
- **Purpose**: Replace every APScheduler job definition with a Celery task decorated with retry policy and structured logging; ensure task return values contain no PII.
- **File(s)**: `services/ctask_scheduler.py`
- **Dependencies**: T-008, T-009
- **Key notes**:
  - **Imports**: Remove all APScheduler imports (`flask_apscheduler`, `APScheduler`, etc.); add `from services.celery_app import celery_app`.
  - **Decorator replacement**: For each `@scheduler.scheduled_job(...)` function, replace with:
    ```python
    @celery_app.task(
        bind=True,
        max_retries=3,
        default_retry_delay=30,
        autoretry_for=(Exception,),
        acks_late=True,
        reject_on_worker_lost=True,
    )
    def <function_name>(self, ...):
    ```
  - `acks_late=True` + `reject_on_worker_lost=True` together implement at-most-once semantics on worker crash (REQ-009).
  - **Structured log statements** — add exactly these four log calls using Python's `logging` module (not `print`):
    - On entry: `logger.info("TASK_STARTED task_id=%s task_name=%s", self.request.id, self.name)`
    - On success before return: `logger.info("TASK_COMPLETED task_id=%s task_name=%s", self.request.id, self.name)`
    - On retry (in `except` block before `self.retry()`): `logger.warning("TASK_RETRY task_id=%s attempt=%d/%d error=%s", self.request.id, self.request.retries + 1, self.max_retries, str(exc))`
    - On terminal failure (after `max_retries` exhausted): `logger.error("TASK_FAILED task_id=%s task_name=%s error=%s", self.request.id, self.name, str(exc))`
  - **Return values**: Each task must return a dict containing only non-PII metadata, e.g. `{"status": "ok", "records_processed": n}`. No user data, emails, names, or IDs that map to individuals.
  - **Scheduler initialisation**: Remove any `scheduler = APScheduler()` instantiation and `scheduler.init_app(app)` / `scheduler.start()` calls.
  - Retain all existing business logic inside each task body unchanged — only the decorator, logging, and return value are modified.
  - Add module-level `logger = logging.getLogger(__name__)`.
- **Acceptance criteria**: REQ-001 — tasks run in worker process; REQ-010 — retry ≤3× at ≥30s; REQ-013 — no PII in return values or logs.
- **Verify**:
  ```bash
  grep -n 'APScheduler\|flask_apscheduler\|scheduler\.scheduled_job' services/ctask_scheduler.py
  # Must produce zero output
  grep -n 'TASK_STARTED\|TASK_COMPLETED\|TASK_RETRY\|TASK_FAILED' services/ctask_scheduler.py
  # Must show at least one match per log level per task
  python -c "from services.ctask_scheduler import *"  # must not raise
  ```

### T-011: Implement production WSGI entry point script (`start.sh`) (new) COMP-001

- **Purpose**: Replace the `python app.py` dev-server invocation with a production-grade Gunicorn launcher. This is the sole entrypoint for the `web` service in all non-local environments.
- **File(s)**: `start.sh`
- **Dependencies**: T-007 (`gunicorn` must be present in `requirements.txt`)
- **Key notes**:
  - File must be executable (`chmod +x start.sh`); commit with execute bit (`git update-index --chmod=+x start.sh`).
  - Use exactly `-w 1` (single worker; horizontal scale handled at the container/replica level, not the process level).
  - Bind to `0.0.0.0:5000` to be reachable inside Docker networks.
  - Set `--timeout 120` to satisfy REQ-003.
  - Pass `--access-logfile -` so access logs go to stdout and are captured by the container runtime.
  - The WSGI callable is `app:app` (module `app`, Flask instance named `app`).
  - **Do not** include any `python app.py` fallback, dev-mode flag, or conditional branch. The script must have exactly one code path.
  - Add `set -euo pipefail` at the top so any pre-Gunicorn command failure causes an immediate non-zero exit.
  - Example final form:
    ```bash
    #!/usr/bin/env bash
    set -euo pipefail
    exec gunicorn -w 1 -b 0.0.0.0:5000 --timeout 120 --access-logfile - app:app
    ```
  - Use `exec` so Gunicorn replaces the shell process and receives signals (SIGTERM) directly from the container runtime.
- **Acceptance criteria**: REQ-003 (production traffic via WSGI, `--timeout ≥120s`, dev server never used).
- **Verify**:
  ```bash
  bash -n start.sh                        # syntax check
  grep -E 'gunicorn.*-w 1.*--timeout 120' start.sh   # assert required flags present
  grep -v 'app\.run\|flask run' start.sh  # assert no dev-server path
  ```

---

### T-012: Implement application startup validator (`startup_checks.py`) (new) COMP-002

- **Purpose**: Provide an ordered, fail-fast validation gate that is called at application boot. Any missing required env var, unreachable database, or unreachable Redis broker causes `sys.exit(1)` with a `CRITICAL`-level log message that names the specific missing resource.
- **File(s)**: `startup_checks.py` (project root)
- **Dependencies**: T-008 (`services/celery_app.py` must exist so its broker URL constant is importable for Redis check)
- **Key notes**:
  - Import `logging`, `os`, `sys`. Use `logging.getLogger(__name__)` — do **not** use `print`.
  - Define a single public function `run_startup_checks(app)` that accepts the Flask app instance.
  - **Check 1 — Required env vars** (run first, before any network calls):
    - Define `REQUIRED_ENV_VARS` as a list of strings, e.g. `["DATABASE_URL", "REDIS_URL", "SECRET_KEY"]`. Adjust to match actual env var names used in the project.
    - Iterate the list; for each missing var log `CRITICAL: Required environment variable '{var}' is not set` and call `sys.exit(1)` immediately (fail on first missing var — do not accumulate).
  - **Check 2 — Database reachability**:
    - Inside `with app.app_context()`: execute `db.session.execute(text("SELECT 1"))`.
    - Wrap in `try/except Exception as e`; on failure log `CRITICAL: Database unreachable: {e}` and `sys.exit(1)`.
  - **Check 3 — Redis/broker reachability**:
    - Use `redis.Redis.from_url(os.environ["REDIS_URL"]).ping()` (import `redis`).
    - Wrap in `try/except Exception as e`; on failure log `CRITICAL: Redis broker unreachable: {e}` and `sys.exit(1)`.
  - Each check must be in strict order: env vars → DB → Redis. A failure in any check must prevent subsequent checks from running.
  - Do **not** log credential values; log only the variable name or a sanitised URL (strip password component if logging URLs).
- **Acceptance criteria**: REQ-011 (missing config/unreachable DB → immediate `sys.exit(1)` with named-var error log); verified by T-022.
- **Verify**:
  ```bash
  python -c "import startup_checks; print('import OK')"
  # Run unit tests added in T-022:
  pytest tests/test_startup_checks.py -v
  ```

---

### T-013: Modify `app.py`: remove APScheduler, bind Celery-Flask factory, call startup checks (modify) COMP-002, COMP-003

- **Purpose**: Surgically remove the APScheduler bootstrapping and `app.run()` dev-server call; wire in the Celery-Flask factory binding; and insert the startup validator call in the correct position in the application lifecycle.
- **File(s)**: `app.py`
- **Dependencies**: T-008 (`services/celery_app.py`), T-012 (`startup_checks.py`)
- **Key notes**:
  - **Remove**:
    - Any `from apscheduler...` imports.
    - Scheduler instantiation (`scheduler = BackgroundScheduler(...)` or similar).
    - `scheduler.start()` / `scheduler.shutdown()` calls and associated `atexit` hooks.
    - `app.run(...)` at the bottom of the file (Gunicorn is now the runner).
  - **Add — Celery binding**: After the Flask `app` object is created and configured, import `celery_app` from `services.celery_app` and call the factory's Flask-context binding method (e.g. `celery_app.conf.update(app.config)` plus `TaskBase.__call__` override, following the pattern established in T-008). The `celery_app` object should remain importable from `app.py` for worker process startup.
  - **Add — startup checks**: Call `run_startup_checks(app)` **after** `app.config` is fully loaded and **before** route/blueprint registration. This ensures checks fail before any route handler can accept traffic.
  - **Order of operations in `app.py`**:
    1. Create Flask `app` and load config.
    2. Call `run_startup_checks(app)`.
    3. Initialise extensions (`db`, etc.).
    4. Register blueprints / routes.
    5. _(no `app.run()`)_
  - Ensure the module-level `app` name remains `app` so `app:app` in `start.sh` resolves correctly.
  - If APScheduler was listed as an installed extension on `app` (e.g. `scheduler.init_app(app)`), remove that line.
- **Acceptance criteria**: REQ-001 (background tasks isolated from web process); REQ-003 (no dev server); REQ-011 (startup checks called).
- **Verify**:
  ```bash
  python -c "from app import app; print('Flask app loads OK')"
  grep -v 'app\.run\|apscheduler\|BackgroundScheduler' app.py
  pytest tests/ -x -q    # full suite must remain green
  ```

---

### T-014: Implement test credential resolver in `tests/config.py` (modify) COMP-006

- **Purpose**: Eliminate all hard-coded credential literals from the test configuration. Replace them with `os.environ.get()` resolution, implement `is_localhost` detection, provide documented fallback values only when running locally, and raise a descriptive `EnvironmentError` in shared/CI environments where a required variable is absent.
- **File(s)**: `tests/config.py`
- **Dependencies**: T-006 (`CONTRIBUTING.md` / `CLAUDE.md` must document which env vars are required and their localhost fallback values, so this file can reference the canonical list)
- **Key notes**:
  - **`is_localhost` detection logic** (must default to `False` in ambiguous cases):
    ```python
    import os, socket
    def _is_localhost() -> bool:
        if os.environ.get("CI"):          return False
        if os.environ.get("GITLAB_CI"):   return False
        hostname = socket.gethostname()
        return hostname in ("localhost", "127.0.0.1") or hostname.endswith(".local")
    IS_LOCALHOST = _is_localhost()
    ```
  - **Credential resolver function**:
    ```python
    def get_credential(var_name: str, localhost_fallback: str) -> str:
        value = os.environ.get(var_name)
        if value is not None:
            return value
        if IS_LOCALHOST:
            return localhost_fallback
        raise EnvironmentError(
            f"Required test credential '{var_name}' is not set. "
            f"Set it as an environment variable before running tests in non-localhost environments."
        )
    ```
  - Replace **every** existing credential literal (database URLs, passwords, API keys, tokens) in `tests/config.py` with a `get_credential(VAR_NAME, fallback)` call. The fallback values must match those documented in `CONTRIBUTING.md` (T-006).
  - Do **not** leave any string literals that contain passwords, tokens, or connection strings outside of `get_credential` calls.
  - `EnvironmentError` message must name the specific variable (verified by T-024).
  - Add a module-level comment block listing all required env vars for quick reference.
- **Acceptance criteria**: REQ-002 (credentials from env vars; localhost fallback only; hard fail in shared envs); REQ-013 (credentials never in source); verified by T-024.
- **Verify**:
  ```bash
  # Assert no literals that look like passwords remain:
  grep -rE '(password|passwd|secret|token)\s*=\s*["\'][^$\{]' tests/config.py && echo "FAIL: literals found" || echo "OK"
  pytest tests/test_config.py -v
  ```

---

### T-015: Create `utils/` package and implement `utils/validation.py` (new) COMP-010

- **Purpose**: Provide a reusable, pure-function validation library used by all form-handling routes. Centralises validation logic so route handlers stay thin and errors are uniform.
- **File(s)**: `utils/__init__.py`, `utils/validation.py`
- **Dependencies**: T-001 (baseline confirmed; no other task dependency)
- **Key notes**:
  - `utils/__init__.py`: empty file (package marker only).
  - `utils/validation.py` must define:
    - **`ValidationError` (TypedDict)**:
      ```python
      from typing import TypedDict
      class ValidationError(TypedDict):
          field: str
          message: str
      ```
    - **`validate_required(value, field_name) -> ValidationError | None`**: Returns error if `value` is `None`, empty string, or whitespace-only string (`str.strip() == ""`).
    - **`validate_not_null(value, field_name) -> ValidationError | None`**: Returns error if `value` is `None` (does **not** reject empty string — distinct from `validate_required`).
    - **`validate_range(value, field_name, min_val, max_val) -> ValidationError | None`**: Returns error if numeric `value` is outside `[min_val, max_val]` (inclusive). Handles non-numeric input as a validation error, not an exception.
    - **`validate_max_length(value, field_name, max_length) -> ValidationError | None`**: Returns error if `len(str(value)) > max_length`.
    - **`validate_form(rules: list[tuple[Callable, ...]]) -> list[ValidationError]`**: Accepts a list of `(validator_fn, *args)` tuples; calls each; collects **all** errors (does not short-circuit); returns the full list.
    - **`format_error_response(errors: list[ValidationError]) -> dict`**: Returns `{"errors": errors}`.
  - All functions must be **pure** (no side effects, no imports of Flask/DB/Celery).
  - `validate_form` must be non-short-circuiting: even if the first rule fails, all subsequent rules are evaluated and all errors collected.
  - Error messages must be human-readable and include the field name, e.g. `"'email' is required"`, `"'age' must be between 0 and 120"`.
- **Acceptance criteria**: REQ-008 (all form input validated; failure returns field-specific error); verified by T-021.
- **Verify**:
  ```bash
  python -c "from utils.validation import validate_form, format_error_response, ValidationError; print('import OK')"
  pytest tests/test_validation.py -v
  ```

---

### T-016: Audit and integrate `validate_form()` across all form-handling POST route handlers (modify) COMP-010

- **Purpose**: Ensure every form submission is validated before any database write occurs. Validation failures return field-specific error messages without persisting partial records.
- **File(s)**: `routes/*.py` (all files containing `POST` handlers that read form data), and their corresponding Jinja2 templates in `templates/`
- **Dependencies**: T-015 (`utils/validation.py`), T-013 (`app.py` must be stable before routes are exercised)
- **Key notes**:
  - **Audit step**: Run `grep -rn "request.form\|request.json" routes/` to enumerate every handler that processes user-submitted data. Document each one before editing.
  - **Integration pattern for HTML routes**:
    ```python
    from utils.validation import validate_form, validate_required, validate_max_length, format_error_response

    @bp.route("/resource", methods=["POST"])
    def create_resource():
        errors = validate_form([
            (validate_required, request.form.get("field_a"), "field_a"),
            (validate_max_length, request.form.get("field_b"), "field_b", 255),
        ])
        if errors:
            return render_template("resource_form.html", errors=errors, form=request.form), 200
        # db.session operations only reached here
        ...
    ```
  - **Integration pattern for JSON routes**: Return `jsonify(format_error_response(errors)), 422` on validation failure.
  - **No partial DB writes**: Ensure all `db.session.add()` / `db.session.commit()` calls are inside the `if not errors:` branch.
  - **Template updates**: For every affected HTML template, add a Jinja2 block that renders field-level errors. Recommended pattern:
    ```html
    {% for error in errors if error.field == 'field_a' %}
      <span class="field-error">{{ error.message }}</span>
    {% endfor %}
    ```
    Also re-populate form field `value` attributes from `form` context variable so the user does not lose their input on validation failure.
  - Preserve all existing success-path behaviour (redirect codes, redirect targets, response shapes) unchanged.
  - If a route already performs manual validation, replace it with `validate_form()` calls so logic is not duplicated.
- **Acceptance criteria**: REQ-008 (all form input validated; failure returns field-specific error message; no partial records persisted); verified by T-025.
- **Verify**:
  ```bash
  # Assert no db.session call can be reached without prior validation in modified routes:
  pytest tests/test_form_routes.py -v
  # Spot-check: submit empty form to each modified route via test client and assert no DB record is created.
  ```

---

### T-017: Implement worker status instrumentation adapter (`services/worker_status.py`) (new) COMP-011

- **Purpose**: Provide a safe, non-raising wrapper around Celery's inspect API. The adapter isolates any Celery connectivity failure from the web tier, returning a structured result object regardless of outcome.
- **File(s)**: `services/worker_status.py`
- **Dependencies**: T-008 (`services/celery_app.py` must export `celery_app`)
- **Key notes**:
  - Define `WorkerStatusResult` as a `TypedDict`:
    ```python
    from typing import TypedDict
    class WorkerStatusResult(TypedDict):
        available: bool
        worker_count: int
        active_tasks: int
        error: str | None
    ```
  - Implement `get_worker_status() -> WorkerStatusResult`:
    ```python
    import logging
    from services.celery_app import celery_app

    logger = logging.getLogger(__name__)

    def get_worker_status() -> WorkerStatusResult:
        try:
            inspect = celery_app.control.inspect(timeout=1.0)
            active = inspect.active()
            if active is None:
                raise RuntimeError("inspect.active() returned None — no workers reachable")
            worker_count = len(active)
            active_tasks = sum(len(tasks) for tasks in active.values())
            return WorkerStatusResult(available=True, worker_count=worker_count, active_tasks=active_tasks, error=None)
        except Exception as e:
            logger.warning("Worker status check failed: %s", e)
            return WorkerStatusResult(available=False, worker_count=0, active_tasks=0, error=str(e))
    ```
  - `timeout=1.0` is mandatory — the inspect call must not block the web request for more than 1 second.
  - The function must **never raise** regardless of the exception type (`ConnectionError`, `TimeoutError`, generic `Exception`). All exceptions are caught and converted to `available=False`.
  - Log at `WARNING` level — do not log at `ERROR` (worker unavailability is degraded, not a crash).
  - Do not log exception stack traces (use `logger.warning(..., e)` not `logger.exception`).
- **Acceptance criteria**: REQ-012 (instrumentation failure isolated from web tier; core routes return HTTP 200); verified by T-023.
- **Verify**:
  ```bash
  python -c "from services.worker_status import get_worker_status, WorkerStatusResult; print('import OK')"
  pytest tests/test_worker_status.py -v
  ```

---

### T-018: Integrate `get_worker_status()` into dashboard routes and templates (modify) COMP-011

- **Purpose**: Surface real-time Celery worker stats on the dashboard when available, and render a graceful degraded indicator when the worker status check fails — without breaking the page in either case.
- **File(s)**: `routes/dashboard*.py` (whichever file(s) contain the dashboard route handlers), `templates/dashboard*.html` (or equivalent template name)
- **Dependencies**: T-017 (`services/worker_status.py`), T-013 (`app.py` stable)
- **Key notes**:
  - In each dashboard route handler, import and call `get_worker_status()`:
    ```python
    from services.worker_status import get_worker_status

    @bp.route("/dashboard")
    def dashboard():
        worker_status = get_worker_status()
        return render_template("dashboard.html", worker_status=worker_status, ...)
    ```
  - `get_worker_status()` must be called **after** all other context is assembled, so a slow inspect does not delay critical page data.
  - Pass `worker_status` as a named variable in the template context; do not spread its fields as individual variables (keeps template binding explicit).
  - **Template changes**:
    - The worker stats widget must be wrapped in a conditional:
      ```html
      {% if worker_status.available %}
        <div class="worker-stats">
          Workers: {{ worker_status.worker_count }} |
          Active tasks: {{ worker_status.active_tasks }}
        </div>
      {% else %}
        <div class="worker-stats worker-stats--degraded">
          Worker instrumentation unavailable
        </div>
      {% endif %}
      ```
    - All other dashboard sections must render unconditionally — the `worker_status.available` flag must only gate the worker stats widget.
  - The route must return HTTP 200 regardless of `worker_status.available` value.
  - Do not add any `try/except` in the route handler — `get_worker_status()` already guarantees no exception propagation.
- **Acceptance criteria**: REQ-012 (instrumentation failure isolated from web tier; core routes return HTTP 200); verified by T-026.
- **Verify**:
  ```bash
  pytest tests/test_dashboard_degraded.py -v
  # Also manually: with no Celery worker running, load /dashboard — page must render HTTP 200 with degraded indicator.
  ```

---

### T-019: Update `docker-compose.yml` to add Redis, Celery worker, and Celery Beat services (modify) COMP-012

- **Purpose**: Extend the container orchestration definition to support the full production topology: Flask/Gunicorn web, Redis broker/backend, Celery worker, and Celery Beat scheduler — with correct dependency chains and environment variable injection.
- **File(s)**: `docker-compose.yml`
- **Dependencies**: T-011 (`start.sh`), T-008 (`services/celery_app.py`), T-009 (`celeryconfig.py`), T-010 (`services/ctask_scheduler.py`)
- **Key notes**:
  - **`web` service**: Change `command` from `python app.py` to `bash start.sh`. Add `depends_on: [redis]`.
  - **`redis` service** (new):
    ```yaml
    redis:
      image: redis:7.2-alpine   # pin to a specific minor version
      restart: unless-stopped
      ports:
        - "6379:6379"           # expose only for local dev; remove in production override
    ```
  - **`celery-worker` service** (new):
    ```yaml
    celery-worker:
      build: .
      command: celery -A services.celery_app worker --loglevel=info
      env_file: .env
      environment:
        - REDIS_URL=${REDIS_URL}
        - DATABASE_URL=${DATABASE_URL}
      depends_on:
        - redis
        - web        # ensures app context / migrations are ready
      restart: unless-stopped
    ```
  - **`celery-beat` service** (new):
    ```yaml
    celery-beat:
      build: .
      command: celery -A services.celery_app beat --loglevel=info --scheduler celery.beat.PersistentScheduler
      env_file: .env
      environment:
        - REDIS_URL=${REDIS_URL}
        - DATABASE_URL=${DATABASE_URL}
      depends_on:
        - redis
      restart: unless-stopped
      deploy:
        replicas: 1   # WARNING: do NOT scale above 1 — multiple beat instances cause duplicate task scheduling (REQ-009)
    ```
  - **`env_file` / `environment`**: All services that need credentials must use `env_file: .env` **and** explicit `environment:` entries using `${VAR}` syntax. Never hard-code values.
  - Ensure `.env` is in `.gitignore` (handled by T-002/T-003 scope indirectly; verify here).
  - Add the `replicas: 1` inline comment verbatim as shown above — it is a deliberate documentation constraint, not just a value.
  - Validate the final file with `docker-compose config` (no errors).
- **Acceptance criteria**: REQ-001 (tasks isolated from web; no duplicate execution on scale-out); REQ-003 (web service uses Gunicorn); REQ-009 (at-most-once via single Beat replica); REQ-013 (no credentials in source).
- **Verify**:
  ```bash
  docker-compose config       # validates YAML and variable substitution
  docker-compose up --dry-run 2>&1 | grep -E "redis|celery-worker|celery-beat|web"
  grep -v '\${' docker-compose.yml | grep -E '(password|secret|token)' && echo "FAIL: literal creds" || echo "OK"
  ```

---

### T-020: Add `security` stage to `.gitlab-ci.yml` with pip-audit, SAST, and Secret Detection (modify) COMP-008

- **Purpose**: Introduce a blocking `security` CI stage that runs before `build`, comprising three jobs: a CVE dependency scan (pip-audit), GitLab SAST, and GitLab Secret Detection. All three must pass for the pipeline to proceed.
- **File(s)**: `.gitlab-ci.yml`
- **Dependencies**: T-007 (`requirements.txt` stable so pip-audit scans the correct dependency set)
- **Key notes**:
  - **Stage ordering**: Insert `security` as the first entry in the `stages:` list, before `build` (and before `test` if present):
    ```yaml
    stages:
      - security
      - build
      - test
      - deploy
    ```
  - **Include GitLab security templates** (add to top-level `include:` block):
    ```yaml
    include:
      - template: Security/SAST.gitlab-ci.yml
      - template: Security/Secret-Detection.gitlab-ci.yml
    ```
  - **`dependency-scan` job** (pip-audit):
    ```yaml
    dependency-scan:
      stage: security
      image: python:3.11-slim
      before_script:
        - pip install pip-audit
      script:
        - pip-audit -r requirements.txt --format json --output pip-audit-report.json
      artifacts:
        paths:
          - pip-audit-report.json
        when: always          # preserve report even on failure
        expire_in: 30 days
      allow_failure: false    # blocks pipeline on any CVE finding
    ```
  - **Override SAST and Secret Detection template jobs** to run in the `security` stage (GitLab templates default to their own stage names which may differ):
    ```yaml
    sast:
      stage: security

    secret_detection:
      stage: security
    ```
  - `allow_failure: false` on `dependency-scan` is explicit — do not omit it. SAST and Secret Detection template jobs default to `allow_failure: false`; verify this is not overridden.
  - Do not add credentials, tokens, or any secrets to `.gitlab-ci.yml` — all env vars for job execution must come from GitLab CI/CD Variables (project settings), not inline values.
  - Validate YAML syntax before committing.
- **Acceptance criteria**: REQ-005 (CI `security` stage: CVE scan with artifact + SAST + git-history secret scan; blocks build); REQ-013 (credentials never in CI config).
- **Verify**:
  ```bash
  # Local YAML lint:
  python -c "import yaml; yaml.safe_load(open('.gitlab-ci.yml'))" && echo "YAML OK"
  # Structural assertions:
  grep -n 'stage: security' .gitlab-ci.yml
  grep -n 'allow_failure: false' .gitlab-ci.yml
  grep -n 'pip-audit-report.json' .gitlab-ci.yml
  grep -n 'Security/SAST' .gitlab-ci.yml
  grep -n 'Security/Secret-Detection' .gitlab-ci.yml
  ```

### T-021: Write unit tests for `utils/validation.py` (new) COMP-010

- **Purpose**: Verify all pure validation functions handle boundary conditions correctly, including multi-error non-short-circuit behaviour and correct `format_error_response` structure.
- **File(s)**: `tests/unit/test_validation.py`
- **Dependencies**: T-015 (utils/validation.py must exist)
- **Key notes**:
  - Import `validate_required`, `validate_not_null`, `validate_range`, `validate_max_length`, `validate_form`, `format_error_response`, and `ValidationError` from `utils.validation`.
  - `validate_required`: test empty string `""`, whitespace-only `"   "`, `None`, and a valid non-empty string. Expect `ValidationError` with correct `field` and `message` for failures; `None` (or no error) for success.
  - `validate_not_null`: test `None` input → error; `0`, `False`, `""` (non-None falsy) → no error (not null); valid object → no error.
  - `validate_range`: test value equal to `min` boundary (inclusive pass), value equal to `max` boundary (inclusive pass), value one below `min` → error, value one above `max` → error, value strictly inside range → pass.
  - `validate_max_length`: test string of exactly `max_length` chars → pass; string of `max_length + 1` → error; empty string → pass; `None` handling per implementation contract.
  - `validate_form`: pass a dict of field→value pairs where **multiple** fields are invalid simultaneously. Assert that **all** errors are returned in one call (no short-circuiting after first failure). Also assert that a fully valid input dict returns an empty errors list.
  - `format_error_response`: assert returned dict contains key `"errors"` whose value is a list; each element is a dict with keys `"field"` and `"message"`; assert no extra top-level keys are present.
  - No mocking required; all functions are pure.
  - Use `pytest.mark.parametrize` for boundary cases to keep the test file DRY.
- **Acceptance criteria**: REQ-008 (form input validation returns field-specific errors)
- **Verify**: `pytest tests/unit/test_validation.py -v`

---

### T-022: Write unit tests for `startup_checks.py` (new) COMP-002

- **Purpose**: Confirm that `run_startup_checks()` exits with code 1 and logs the right CRITICAL message for each failure scenario, and returns normally when all checks pass.
- **File(s)**: `tests/unit/test_startup_checks.py`
- **Dependencies**: T-012 (startup_checks.py must exist)
- **Key notes**:
  - Import `run_startup_checks` from `startup_checks`; use `pytest.raises(SystemExit)` to assert `sys.exit(1)` is called.
  - **Missing env var test**: Use `monkeypatch.delenv` to remove a required env var. Assert `SystemExit` with code `1`. Use `caplog` (level `CRITICAL`) to assert the log message names the specific missing variable (e.g., `"DATABASE_URL"` appears in the log output). Repeat for at least two distinct required variables to confirm variable naming is not hardcoded.
  - **DB unreachable test**: Patch the DB connectivity call (e.g., `sqlalchemy.engine.Engine.connect` or equivalent) to raise `OperationalError`. Assert `SystemExit(1)` and a CRITICAL log entry mentioning database reachability.
  - **Redis unreachable test**: Patch the Redis ping call (e.g., `redis.Redis.ping`) to raise `ConnectionError`. Assert `SystemExit(1)` and a CRITICAL log entry mentioning Redis/broker.
  - **All checks pass test**: Patch env vars to supply all required values; patch DB and Redis calls to return successfully. Assert `run_startup_checks()` returns without raising and no CRITICAL log is emitted.
  - Use a minimal Flask app fixture (`app.app_context()`) if `run_startup_checks` requires an app context.
  - Never rely on real network or DB connections; all external calls must be patched via `unittest.mock.patch` or `pytest-mock`.
- **Acceptance criteria**: REQ-011 (missing config/unreachable DB → `sys.exit(1)` with named-var error log)
- **Verify**: `pytest tests/unit/test_startup_checks.py -v`

---

### T-023: Write unit tests for `services/worker_status.py` (new) COMP-011

- **Purpose**: Confirm that `get_worker_status()` correctly maps Celery inspect output to `WorkerStatusResult` and **never raises** on any failure path.
- **File(s)**: `tests/unit/test_worker_status.py`
- **Dependencies**: T-017 (services/worker_status.py must exist)
- **Key notes**:
  - Import `get_worker_status` from `services.worker_status` and `WorkerStatusResult` for type assertions.
  - **Healthy inspect test**: Patch `celery_app.control.inspect().active()` to return a dict with two worker keys each containing a list of active task dicts (e.g., `{"worker1@host": [{"id": "abc"}, {"id": "def"}], "worker2@host": [{"id": "ghi"}]}`). Assert `result.available == True`, `result.worker_count == 2`, `result.active_tasks == 3`, `result.error is None`.
  - **`ConnectionError` test**: Patch `inspect().active()` to raise `ConnectionError`. Assert the function returns without raising; assert `result.available == False`. Also assert a WARNING-level log entry is emitted (use `caplog`).
  - **Timeout test**: Patch `inspect().active()` to raise `TimeoutError` (or the Celery equivalent). Same assertions as ConnectionError case.
  - **`None` response test**: Patch `inspect().active()` to return `None` (broker offline, no workers registered). Assert `result.available == False`, `result.worker_count == 0`, `result.active_tasks == 0`.
  - In all failure cases, assert no exception propagates out of `get_worker_status()` (wrap call in `try/except Exception` inside the test if needed, but prefer asserting no raise via normal return).
  - Patch at the `services.worker_status.celery_app` import reference, not the global Celery object, to avoid test pollution.
- **Acceptance criteria**: REQ-012 (instrumentation failure isolated from web tier; core routes return HTTP 200)
- **Verify**: `pytest tests/unit/test_worker_status.py -v`

---

### T-024: Write unit tests for `tests/config.py` credential resolver (new) COMP-006

- **Purpose**: Confirm that the credential resolver returns values from env vars, uses documented fallbacks only on localhost, and raises `EnvironmentError` naming the missing variable in all other environments.
- **File(s)**: `tests/unit/test_tests_config.py`
- **Dependencies**: T-014 (tests/config.py must be refactored)
- **Key notes**:
  - Import the resolver function(s) and `is_localhost` detection logic from `tests.config`. If `is_localhost` is a module-level computed bool, import it directly and override via `monkeypatch`.
  - **Env var set → value returned**: Use `monkeypatch.setenv("MY_CREDENTIAL", "secret")`. Call resolver for that credential. Assert returned value equals `"secret"`. Applies regardless of `is_localhost`.
  - **Env var absent + `is_localhost=True` → fallback**: Use `monkeypatch.delenv` to remove the variable; force `is_localhost` to `True` (patch module attribute). Assert the documented fallback value (e.g., `"localhost"`, `"5432"`) is returned without raising.
  - **Env var absent + `is_localhost=False` → `EnvironmentError`**: Remove the variable; force `is_localhost` to `False`. Assert `EnvironmentError` is raised and the exception message contains the exact variable name (e.g., `"DB_PASSWORD"` in `str(exc.value)`).
  - **`CI=true` → `is_localhost=False`**: Use `monkeypatch.setenv("CI", "true")`. Re-import or re-evaluate `is_localhost`. Assert it resolves to `False`. Then remove a required credential and assert `EnvironmentError` is raised (confirming CI hard-fail path).
  - Parameterise across at least 3 different credential variable names to guard against any variable being hardcoded as a special case.
  - These tests must themselves pass in CI without any real credentials; use `monkeypatch` exclusively.
- **Acceptance criteria**: REQ-002 (test credentials from env vars; localhost fallback only; hard fail in shared envs), REQ-013 (credentials never in source or CI logs)
- **Verify**: `pytest tests/unit/test_tests_config.py -v`

---

### T-025: Write integration tests for form-handling route validation (new) COMP-010

- **Purpose**: Confirm via Flask test client that validated POST routes reject invalid input with field-specific errors and no DB writes, and accept valid input with correct persistence.
- **File(s)**: `tests/integration/test_form_validation.py`
- **Dependencies**: T-016 (route handlers must integrate `validate_form()`), T-014 (test credential resolver)
- **Key notes**:
  - Use a `pytest` fixture that creates a Flask test client with `TESTING=True` and an in-memory or test-isolated DB session (patch `db.session` or use a rollback fixture to prevent state leakage between tests).
  - Identify at least **two** distinct form-handling POST routes (e.g., `/incidents/create`, `/handovers/create`) to test. Cover at least one HTML-response route and one JSON-response route if both exist.
  - **Missing required field → error, no DB write**:
    - POST with one required field omitted.
    - **HTML route**: assert HTTP 200; assert response body contains the field name and an error message string; assert no new DB record exists (query count before/after).
    - **JSON route**: assert HTTP 422; assert response JSON contains `{"errors": [{...}]}` with `"field"` matching the omitted field name.
  - **Valid input → success, record persisted**:
    - POST with all required fields populated with valid values.
    - Assert HTTP 302 (redirect) or HTTP 200 as appropriate for the route.
    - Assert exactly one new record exists in the relevant table.
  - **Multiple field failures → all errors in single response**:
    - POST with at least two required fields omitted or invalid simultaneously.
    - Assert all field errors are present in the response (not just the first); assert count of errors in response matches number of invalid fields.
  - Patch any external service calls (e.g., SSO lookups, email dispatch) that may be triggered within route handlers to avoid real I/O.
  - Do **not** commit DB writes during tests; use `db.session.rollback()` in teardown or use a transaction-scoped fixture.
- **Acceptance criteria**: REQ-008 (form input validated; failure returns field-specific error; no partial DB writes)
- **Verify**: `pytest tests/integration/test_form_validation.py -v`

---

### T-026: Write integration tests for dashboard graceful degradation (new) COMP-011

- **Purpose**: Confirm that the dashboard route returns HTTP 200 with full core rendering when `get_worker_status` reports unavailable, and that only the instrumentation widget reflects the degraded state.
- **File(s)**: `tests/integration/test_dashboard_degradation.py`
- **Dependencies**: T-018 (dashboard route integrates `get_worker_status`), T-014 (test credential resolver)
- **Key notes**:
  - Use a Flask test client fixture with `TESTING=True`; patch `services.worker_status.get_worker_status` (at the import site used in the dashboard route module) using `unittest.mock.patch` or `pytest-mock`.
  - **Degraded state test**:
    - Mock `get_worker_status` to return `WorkerStatusResult(available=False, worker_count=0, active_tasks=0, error="Connection refused")`.
    - GET the dashboard route (e.g., `/dashboard` or `/`).
    - Assert HTTP status code is `200`.
    - Assert the response body contains the expected core dashboard HTML landmarks (e.g., a known static heading or nav element that is always present).
    - Assert the response body contains the degraded/unavailable indicator for the worker stats widget (e.g., a specific CSS class, text string like `"Workers unavailable"`, or data-attribute defined in the template).
    - Assert the response body does **not** contain worker count or active task numbers (to confirm stats are hidden/replaced, not just appended).
  - **Available state test** (positive control):
    - Mock `get_worker_status` to return `WorkerStatusResult(available=True, worker_count=2, active_tasks=5, error=None)`.
    - Assert HTTP 200.
    - Assert response body contains `"2"` workers and `"5"` active tasks rendered within the instrumentation widget.
  - Patch any DB queries within the dashboard route that require real data (use `MagicMock` or fixture DB state as appropriate).
  - Do not test template rendering independently; test through the full route stack to catch any context-passing bugs.
- **Acceptance criteria**: REQ-012 (instrumentation failure isolated from web tier; core routes return HTTP 200)
- **Verify**: `pytest tests/integration/test_dashboard_degradation.py -v`

---

### T-027: Write integration tests for Celery task dispatch and retry (new) COMP-004

- **Purpose**: Confirm that Celery tasks emit correct structured log entries at each retry attempt, reach `SUCCESS` on eventual success, and reach `FAILURE` with a `TASK_FAILED` log when all retries are exhausted.
- **File(s)**: `tests/integration/test_celery_tasks.py`
- **Dependencies**: T-010 (tasks use `@celery_app.task` with retry policy), T-019 (docker-compose defines worker/beat services)
- **Key notes**:
  - Use Celery's `CELERY_TASK_ALWAYS_EAGER = True` and `CELERY_TASK_EAGER_PROPAGATES = False` in the test configuration so tasks execute synchronously in-process without a real broker; this avoids requiring a running Redis in unit/integration CI.
  - Alternatively, if the project uses `pytest-celery` or a Redis test fixture, document that requirement clearly in a `pytest.ini` or fixture docstring.
  - **Retry then succeed test**:
    - Patch the external service called by a representative task (e.g., the first task defined in `ctask_scheduler.py`) using `side_effect=[Exception("fail"), Exception("fail"), "success_value"]` (fail twice, succeed on third attempt).
    - Call the task directly via `.apply()` or `.delay()` depending on eager mode.
    - Use `caplog` at `INFO` level. Assert `TASK_RETRY` log entries appear exactly twice, each containing the correct attempt number (1 and 2).
    - Assert `TASK_STARTED` log appears once at the beginning.
    - Assert `TASK_COMPLETED` log appears once after the third attempt.
    - Assert the final task state is `SUCCESS`.
  - **All retries exhausted → FAILURE test**:
    - Patch the external service to always raise (e.g., `side_effect=Exception("permanent failure")`), ensuring it fails more times than `max_retries=3`.
    - Assert `TASK_RETRY` log appears exactly 3 times.
    - Assert `TASK_FAILED` log appears once after the final retry is exhausted.
    - Assert the task result state is `FAILURE`.
    - Assert no exception propagates out of the `.apply()` call (task failure must be terminal, not unhandled).
  - **Log content assertions**: Each `TASK_RETRY` log entry must include the attempt number; each `TASK_FAILED` entry must include the exception class or message. Assert these substrings are present in the captured log records.
  - **No PII in return values**: Inspect the task result `.result` dict on SUCCESS state; assert it contains only status metadata keys (e.g., `"status"`, `"task_id"`, `"duration_ms"`) and contains no fields named after PII attributes (e.g., `"email"`, `"username"`, `"token"`). Enumerate the known return keys from T-010's implementation.
  - If eager mode is used, add a module-level comment explaining why no broker is needed and how to run against a real broker for smoke testing.
- **Acceptance criteria**: REQ-001 (tasks isolated from web process), REQ-009 (at-most-once execution), REQ-010 (transient failures retry ≤3× at ≥30s intervals; terminal state observable)
- **Verify**: `pytest tests/integration/test_celery_tasks.py -v`

## Execution Waves

| Wave | Tasks | Dependencies Satisfied | Verify Command |
|------|-------|----------------------|----------------|
| **0** | T-001 | — | `pytest --tb=short > baseline.txt; echo "Exit: $?"` |
| **1** | T-002, T-004, T-005, T-006, T-007, T-015 | T-001 | `git check-ignore -v *.pdf; pip install -r requirements.txt --dry-run; python -c "import utils.validation"` |
| **2** | T-003, T-008, T-011, T-014, T-020, T-021 | T-001–T-007, T-015 | `git ls-files --error-unmatch "*.pdf" 2>&1 \| grep "error"; python -c "from services.celery_app import celery_app"; bash -n start.sh; pytest tests/test_validation.py` |
| **3** | T-009, T-012, T-017, T-024 | T-002–T-008, T-011, T-014, T-020, T-021 | `python -c "import celeryconfig"; python -c "from startup_checks import run_startup_checks"; python -c "from services.worker_status import get_worker_status"; pytest tests/test_config.py tests/test_startup_checks.py tests/test_worker_status.py` |
| **4** | T-010, T-013, T-022, T-023 | All Wave 0–3 tasks | `grep -R "scheduler.scheduled_job" services/ctask_scheduler.py; [ $? -ne 0 ] && echo "APScheduler removed"; python -c "from app import app"; pytest tests/test_startup_checks.py tests/test_worker_status.py` |
| **5** | T-016, T-018, T-019 | All Wave 0–4 tasks | `docker compose config --quiet; grep "validate_form" routes/*.py \| wc -l; grep "worker_status" routes/dashboard*.py` |
| **6** | T-025, T-026, T-027 | All Wave 0–5 tasks | `pytest tests/ -v --tb=short; diff <(grep "^FAILED\|^ERROR" baseline.txt) <(pytest --tb=line -q 2>&1 \| grep "^FAILED\|^ERROR")` |

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| **APScheduler not fully removed from `app.py`** — residual initialisation runs alongside Celery Beat, causing duplicate scheduled task execution (violates REQ-001, REQ-009) | P0 — data corruption / double processing | Medium | T-013 explicitly removes APScheduler init; T-010 replaces all decorators; post-wave-4 grep asserts zero occurrences of `scheduler.scheduled_job` and `APScheduler` imports |
| **Celery Beat scaled to `replicas > 1`** — docker-compose or orchestrator override strips the `replicas: 1` guard, causing every periodic task to fire N times | P0 — duplicate execution | Low-Medium | Inline `# DO NOT SCALE BEYOND 1 — duplicate beat execution` comment in `docker-compose.yml`; T-009 notes constraint; address in runbook |
| **Redis unavailable at container start** — `depends_on` in Compose does not wait for Redis readiness, startup validator exits before broker is live | High — service won't start | Medium | T-012 startup check catches Redis unreachability; add `healthcheck` + `depends_on: condition: service_healthy` in T-019; document retry-wait wrapper in `start.sh` if needed |
| **CI env vars absent in non-CI local runs** — `is_localhost` detection logic ambiguous; wrong branch taken silently passes or hard-fails unexpectedly | Medium — flaky tests or credential leak | Medium | T-014 defaults `is_localhost` to `False` when ambiguous; `CI=true` always forces `is_localhost=False`; T-024 covers all four branches including the `CI` env var case |
| **Binary files remain in git history after `git rm --cached`** — PDFs/docs untracked going forward but still accessible via `git log` (partial REQ-006 compliance) | Low-Medium — history exposure | High (inherent) | Explicitly out-of-scope for this plan; document in `migrations/README.md` that history purge (BFG / `git filter-repo`) is a separate, coordinated task requiring force-push and team re-clone |
| **GitLab SAST/Secret-Detection template job stage override breaks template inheritance** — override syntax error silently disables security jobs | P0 — CI security stage never runs | Medium | Test `.gitlab-ci.yml` with `gitlab-ci-lint` in T-020; validate pipeline visually in a feature branch before merging; `allow_failure: false` on `dependency-scan` ensures build blocks |
| **`startup_checks.py` tightens environment requirements** — existing dev environments without Redis set up will fail to start the web container after T-013 lands | Medium — developer productivity | High | T-006 documents localhost fallback values in `CONTRIBUTING.md`; T-002/T-006 are Wave 1, giving developers early visibility before T-013 lands in Wave 4 |
| **Form validation changes break existing passing tests** — route handlers now return 422 / re-rendered form on previously-accepted inputs | Medium — regression | Medium | T-001 baseline recorded; T-025 integration tests use Flask test client; Wave 6 diff against baseline catches regressions before merge |
| **Worker status `inspect(timeout=1.0)` adds latency to every dashboard request** | Low-Medium — UX degradation | Medium | Timeout hard-capped at 1.0 s in T-017; T-026 asserts HTTP 200 even when `available=False`; consider async fire-and-forget if p99 latency increases are observed post-deploy |
| **Credentials committed before T-020 security stage is active** — secret detection only fires after the CI stage is wired | P0 — credential exposure | Low | T-005 (branch protection) is Wave 1 — no direct push to `main` from day one; T-020 targets the CI pipeline, not the protection gate |

---

## Non-Functional Hardening

- [x] **API boundary — input validation on all new/modified endpoints:** `validate_form()` called before any `db.session` operation in every POST handler (T-016); HTML routes return re-rendered form with field errors; JSON routes return HTTP 422 `{"errors":[…]}`
- [x] **Service layer — null/empty handling for all new operations:** `validate_required` / `validate_not_null` cover empty-string and `None` inputs (T-015, T-021); `get_worker_status()` catches all exceptions and returns `available=False` without re-raising (T-017, T-023)
- [x] **Data access — query performance, indexes:** No schema changes; no new queries introduced; validation failure short-circuits before any `db.session` write, preventing partial record accumulation
- [x] **Error handling — structured error responses:** `format_error_response()` produces consistent `{field, message}` shape (T-015); Celery tasks emit `TASK_STARTED / TASK_COMPLETED / TASK_RETRY / TASK_FAILED` structured log events (T-010); startup validator logs `CRITICAL` with the named missing variable before `sys.exit(1)` (T-012)
- [x] **Logging — structured events, no PII:** Task return values contain only status metadata (T-010 spec); worker status result fields are counts and flags only — no task payload content (T-017); test credential resolver raises `EnvironmentError` naming the variable, not the value
- [x] **Security — auth checks, PII handling:** Credentials resolved exclusively from env vars (T-006, T-014); `tests/config.py` hard-fails in non-localhost environments (T-014, T-024); CI secret detection blocks build (T-020); branch protection prevents unreviewed merges to `main` (T-005)
- [x] **Tests — unit + integration:** Unit tests for all new pure functions (T-021, T-022, T-023, T-024); integration tests for form validation with Flask test client (T-025), dashboard degradation (T-026), and Celery retry lifecycle (T-027); pre/post baseline diff required at Wave 0 and Wave 6

---

## Post-Implementation Checklist

- [ ] All Wave 0 baseline tests still pass (diff `baseline.txt` against final `pytest` run — zero new `FAILED`/`ERROR` lines)
- [ ] All new unit tests pass: `tests/test_validation.py`, `tests/test_startup_checks.py`, `tests/test_worker_status.py`, `tests/test_config.py`
- [ ] All new integration tests pass: `tests/test_form_routes.py`, `tests/test_dashboard.py`, `tests/test_celery_tasks.py`
- [ ] No `APScheduler` references remain in `app.py` or `services/ctask_scheduler.py` (`grep -R "APScheduler\|scheduler\.scheduled_job" . --include="*.py"` returns empty)
- [ ] No binary doc files tracked by git (`git ls-files | grep -E "\.(pdf|doc|docx|xls|xlsx|ppt|pptx)$"` returns empty)
- [ ] `start.sh` is the sole web process entrypoint; no `app.run()` present in production code paths
- [ ] `CONTRIBUTING.md` and `CLAUDE.md` contain env var setup instructions with documented localhost defaults
- [ ] `migrations/README.md` classifies every migration script with APPLIED / SUPERSEDED / ENV-SPECIFIC
- [ ] `docker compose config` validates without error; `celery-beat` has `replicas: 1` and scaling warning comment
- [ ] `.gitlab-ci.yml` lints cleanly (`gitlab-ci-lint`); `security` stage appears before `build`; `dependency-scan` has `allow_failure: false`
- [ ] GitLab branch protection active: no direct push to `main`; ≥1 peer approval required; self-approval disabled — verified in project Settings → Repository → Protected branches
- [ ] All task return values verified to contain no PII (code review sign-off on T-010)
- [ ] Worker status timeout confirmed ≤1.0 s; dashboard p95 response time within acceptable bounds post-deploy

---

## Milestones

| Milestone | Completion Criteria | Target Wave |
|-----------|--------------------|-|
| **M1 — Foundation Locked** | Baseline recorded; `.gitignore` updated; `requirements.txt` updated with Celery/Gunicorn; `utils/validation.py` implemented; branch protection active; `CONTRIBUTING.md` updated | End of Wave 2 |
| **M2 — Celery Infrastructure Complete** | `celery_app.py`, `celeryconfig.py`, `startup_checks.py`, `worker_status.py` implemented and unit-tested; `start.sh` present; CI security stage wired | End of Wave 3 |
| **M3 — Application Wired** | `app.py` free of APScheduler and `app.run()`; all background tasks migrated with retry decorators and structured logs; `docker-compose.yml` includes all four services | End of Wave 4 |
| **M4 — Features Integrated** | Form validation active across all POST handlers; dashboard renders graceful degradation; Docker Compose stack starts end-to-end with `docker compose up` | End of Wave 5 |
| **M5 — Verified & Shippable** | All integration tests green; baseline diff shows zero regressions; post-implementation checklist fully signed off; MR peer-reviewed and approved via GitLab | End of Wave 6 |


---
## Interrogation Summary

# Requirements Summary: Archaeology & Hardening Branch

## 1. Executive Overview

This branch resolves 8 medium-severity gaps discovered during archaeology in infrastructure, security, process, and documentation. Six gaps have been fixed (Gunicorn migration, migration tracking, credential hardening, SAST/scanning, APScheduler refactoring, binary file removal), while one (Jira permissions) is deferred to external admin action, and one (branch protection) requires organizational process change upon team growth. The scope consolidates production-readiness improvements with no new feature work.

---

## 2. Functional Requirements

- **The system shall execute scheduled tasks (email digests, ServiceNow polling, retry operations) via Celery-backed workers**, eliminating single-worker constraints and enabling safe horizontal scaling of Gunicorn. *Q: [gap_architecture] APScheduler refactoring* — services/ctask_scheduler.py now dispatches to Celery; workers are managed via docker-compose; status queries use `celery.control.inspect`.

- **The system shall retrieve all test credentials from environment variables** (`TEST_SUPERADMIN_PASSWORD`, `TEST_ADMIN_PASSWORD`, `TEST_USER_PASSWORD`), with localhost-only fallback to hardcoded defaults for developer convenience. *Q: [gap_security] Credential hardening* — tests/config.py updated; CLAUDE.md and CONTRIBUTING.md now show env var pattern instead of literals.

- **The system shall run gunicorn with a 120-second timeout in production**, backed by bash start.sh entry point (not Flask development server). *Q: [gap_architecture] Gunicorn migration* — docker-compose.yml web service command changed from `python app.py` to `bash start.sh`; start.sh ends with `exec gunicorn -w 1 -b 0.0.0.0:5000 --timeout 120 --access-logfile - app:app`.

- **The system shall document the status and interplay of all ad-hoc SQL migration scripts and Alembic versioned migrations** in migrations/README.md, including: which scripts are applied to production, which are superseded (marked "Do not re-apply"), and which are environment-specific. *Q: [gap_architecture] Migration tracking* — established rule that all future schema changes go through `flask db migrate` only.

- **The system shall enforce pipeline security scanning before build**, including: (1) pip-audit dependency scan (blocks on known CVEs, JSON artifact saved), (2) GitLab SAST (Bandit-based Python static analysis), (3) GitLab Secret Detection (git history scan for committed secrets). *Q: [gap_security] SAST/scanning* — three stages added to .gitlab-ci.yml in dedicated security stage running before build.

- **The system shall not track binary documentation files in git** (*.pdf, *.docx, *.doc, *.xlsx, *.pptx removed from tracking; added to .gitignore). *Q: [gap_standards] Binary file bloat* — Confluence is single source of truth for user documentation.

- **The system shall require a minimum of 1 reviewer approval for merge requests to master**, preventing self-approval by the author. *Q: [gap_process] Branch protection* — GitLab MR approval rules configured; author cannot approve own MR; direct pushes to master blocked immediately regardless of team size. Will enforce once second team member joins.

---

## 3. Constraints & Non-Functional Requirements

- **Performance & Scalability**: Medium volume — thousands of requests per day; standard caching and indexing suffice. *Q: [constraints]* — No high-throughput or microsecond-latency requirements stated.

- **Security Posture**: 
  - Credentials must never appear in source code, git history, or CI/CD logs (except localhost-only fallbacks). *Q: [gap_security] Credential exposure*
  - All external dependencies must be scanned for known CVEs on every pipeline run. *Q: [gap_security] SAST/scanning*
  - No direct pushes to master; all changes require peer review. *Q: [gap_process] Branch protection*

- **Scalability Constraint Removal**: APScheduler and Celery Beat must not run in the same process as Gunicorn. Gunicorn can scale to multiple workers without duplicate task execution. *Q: [gap_architecture] Scaling* — documented constraint removed; safe for N workers.

- **Data Integrity**: All migration scripts must be traceable and documented to prevent schema drift across environments. *Q: [gap_architecture] Migration tracking*

---

## 4. Edge Cases & Error Handling

| Scenario | Expected Behaviour | Related Requirement |
|----------|-------------------|---------------------|
| **Empty or null user input** | System validates input and returns clear error message. | [acceptance_criteria] validations enforced |
| **Network timeout or third-party API unavailability** | Celery tasks retry up to 3 times with 30-second countdown between attempts; transient failures self-heal without operator intervention. | [edge_cases] partial failure (C strategy) |
| **User lacks required permissions (Jira, ServiceNow, audit submission)** | Request rejected immediately with permission-denied error; no silent failure or degraded mode. | [edge_cases] permission-denied scenario |
| **Startup failure (missing secrets, DB unreachable)** | Process aborts immediately with clear error log; does not start in broken state. | [edge_cases] startup failures (A strategy) |
| **Redis or non-critical scheduler status check unavailable** | Status check fails gracefully without cascading to web tier; optional instrumentation degraded but core app runs. | [edge_cases] non-critical check (D strategy) — isolated failure |
| **Partial audit-critical operation failure** | Never silently fails. Either succeeds fully, or raises exception and retries (no silent degradation for handover submissions). | [edge_cases] audit-critical handover |

---

## 5. Dependencies & Integrations

- **Message Queue**: Celery (Redis backend for task persistence and worker coordination). *Q: [dependencies] message queue* — previously APScheduler + Celery Beat; now pure Celery.

- **External APIs**: Third-party REST/GraphQL APIs (e.g., ServiceNow, Jira) for polling and task dispatch. *Q: [dependencies] integrations* — Celery retry strategy (3 retries, 30s countdown) handles transient failures.

- **Authentication/SSO**: OAuth and/or SAML provider for user authentication. *Q: [dependencies] AuthN/AuthZ* — credentials remain hardcoded in code as fallback only for localhost.

- **Database**: External database (PyMySQL in requirements.txt) with versioned migrations via Flask-Migrate/Alembic. *Q: [dependencies] external database*

- **CI/CD Pipeline**: GitLab (SAST, Secret Detection templates, MR approval rules, artifact storage). *Q: [gap_security] SAST* — no feature flag; scanning runs on every pipeline from this point forward.

- **Jira Integration** (OUT-OF-SCOPE for this branch): Board 344407 requires HiveMind service account upgrade to Developer role; currently in Jira admin queue. *Q: [gap_process] Jira permissions* — no code change; external admin action.

---

## 6. Scope Boundaries

**In Scope:**
- Gunicorn configuration and Flask dev server replacement
- Celery-backed task scheduler (APScheduler removal from Flask process)
- Environment variable injection for test and production credentials
- Migration documentation and script hygiene
- Binary file removal and .gitignore enforcement
- GitLab SAST, pip-audit, and Secret Detection integration
- MR approval rules and branch protection on master

**Out of Scope (Non-Goals):**
- Jira project permissions or board configuration — resolved via external admin.
- Production credential rotation or secret management system (e.g., HashiCorp Vault) — fallbacks to env vars assumed sufficient.
- Horizontal scaling of APScheduler to external scheduler (e.g., Chronos, Airflow) — Celery satisfies current scaling requirements.
- Load testing or performance benchmarking against "thousands of requests/day" — constraint is qualitative; no SLA or P99 latency target stated.
- Real-time audit log streaming or SIEM integration — audit-critical operations are logged; delivery mechanism not specified.

---

## 7. Acceptance Criteria

| Requirement | Acceptance Criterion |
|-------------|---------------------|
| **Celery-backed scheduler** | Given Gunicorn scaled to 3 workers with Celery workers in separate container, when email digest task triggers, then exactly one email is sent (no duplicates) and status is visible via `celery.control.inspect`. |
| **Environment variable credentials** | Given TEST_SUPERADMIN_PASSWORD set in CI/CD, when test suite runs, then tests authenticate as superadmin and no hardcoded credentials appear in stdout or artifact logs. |
| **Gunicorn startup** | Given gunicorn process starts with `bash start.sh`, when app receives first request, then request is served and shutdown timeout is 120 seconds. |
| **Migration documentation** | Given migrations/README.md exists, when developer reads script status, then they can distinguish applied (prod), superseded (do-not-reapply), and environment-specific scripts without external wiki. |
| **Security scanning** | Given .gitlab-ci.yml runs security stage before build, when a new CVE in requirements.txt is introduced, then pipeline fails with pip-audit report artifact and Secret Detection blocks commit. |
| **Binary file removal** | Given git history is clean, when developer clones repo, then no *.pdf, *.docx, *.xlsx, *.pptx files are present and .gitignore contains binary patterns. |
| **Branch protection** | Given a new MR is opened to master, when the author attempts to merge without peer review, then merge is blocked and GitLab reports "1 approval required". |
| **Input validation & error messages** | Given user submits invalid input (empty, null, or out-of-range), when system processes request, then response contains specific error message describing the validation failure. |

---

## 8. Assumptions & Risks

| Assumption | Risk Level | Rationale |
|-----------|-----------|-----------|
| Celery Redis backend is always available and monitored. If Redis goes down, scheduled tasks queue but do not execute until recovery. | **Medium** | Celery retry logic assumes Redis is transient; prolonged outage (hours) could cause task backlog or stale handover submissions. Monitoring/alerting must watch Redis uptime. |
| Environment variables are correctly populated in all non-localhost environments (dev, staging, prod). | **Medium** | If env vars are missing or typo'd in deployment, test suite or app will silently use insecure defaults or fail at startup. Deployment runbook must verify all TEST_* vars are set before container start. |
| GitLab SAST (Bandit) catches sufficient Python security issues for this app's threat model. | **Low** | Bandit is mature and free-tier; no advanced custom rules required. Static analysis is never complete, but combined with Secret Detection and pip-audit provides reasonable coverage. |
| Jira admin will complete service account role upgrade within the team's normal workflow cadence. | **Medium** | If Jira permissions remain unresolved, issue correlation will stay broken; may delay future sprint planning. Assume admin is aware but deprioritized; escalate if unresolved after 2 weeks. |
| The "thousands of requests/day" constraint is steady-state average, not peak. | **Low** | No burst or scaling scenario specified. Standard caching and indexing (assumed in-place) will suffice. If peak exceeds 10x average, reconsider. |
| Partial failure handling strategies (retry C, abort A, degrade D) are correctly scoped to their respective operations. | **Medium** | If a "non-critical" operation (D) is incorrectly classified, silent failure could go unnoticed. Requires code review to verify each Celery task and startup check is tagged correctly. |
| Second team member will join within 6 months; MR approval rule becomes enforceable at that time. | **Low** | Current single-developer project; rule enforced after hire. Assume org has hiring plan. |

---

## 9. Contradictions

**None detected.**

All Q&A answers are internally consistent. Gaps discovered (Werkzeug, migrations, credentials, SAST) are resolved via concrete commits with no conflicting guidance. Process improvements (branch protection, Jira permissions) acknowledge external dependencies and single-developer status without contradiction.

---

## 10. Open Items

1. **Jira Service Account Upgrade** (Blocker for future sprint planning)
   - Status: Awaiting Jira admin to grant HiveMind account Developer role on project linked to board 344407.
   - Owner: External (Jira admin)
   - Timeline: Target within 2 weeks to unblock issue correlation.

2. **Deployment Verification Runbook** (Before production release)
   - Requirement: Document and test that all environment variables (TEST_SUPERADMIN_PASSWORD, TEST_ADMIN_PASSWORD, TEST_USER_PASSWORD, etc.) are correctly populated in staging/prod before container start.
   - Owner: DevOps/release engineer
   - Timeline: Before first prod deployment of this branch.

3. **Redis Monitoring & Alerting** (Before scalable Celery deployment)
   - Requirement: Verify Redis uptime monitoring and alert thresholds are in place; define action plan for Redis outage (failover, manual retry dispatch).
   - Owner: Infrastructure/SRE
   - Timeline: Before scaling Gunicorn beyond 1 worker.

4. **Code Review of Error Handling Scoping** (Before merge)
   - Requirement: Review each Celery task and startup sequence to confirm they are tagged with correct failure strategy (A/C/D) per edge case strategy in Q&A.
   - Owner: Code reviewer (architecture/senior eng)
   - Timeline: As part of MR approval.

5. **Confluence Documentation Update** (Best practice)
   - Requirement: Verify ShiftOps_Admin_Guide and ShiftOps_User_Guide are present and up-to-date in Confluence; remove stale wiki pages that may still reference binary files in git.
   - Owner: Technical writer or product owner
   - Timeline: Within 1 sprint of this branch merge.
