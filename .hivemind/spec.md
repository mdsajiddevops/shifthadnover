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