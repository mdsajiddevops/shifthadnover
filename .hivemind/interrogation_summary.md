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