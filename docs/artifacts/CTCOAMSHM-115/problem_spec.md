# Problem Specification — Shifthandover: Gap Remediation & Core Feature Implementation

---

## Meta

| Field | Value |
|-------|-------|
| **Ticket ID** | CTCOAMSHM-115 [J:CTCOAMSHM-115] |
| **Project** | Shifthandover (`shifthandover_v3`) |
| **Creation Date** | 2026-05-12 |
| **Status** | Draft — Pending Architecture Review |
| **Interrogation Summary** | `docs/phase-2/interrogation_summary.md` |

---

## Problem Statement

### Summary
Remediate four confirmed process and architecture gaps (branch protection, dependency pinning, container isolation, CI test integration) in the Shifthandover platform, and define requirements for a permission-gated, real-time core action feature. [J:CTCOAMSHM-115]

### User Problem
Development contributors lack enforced review gates and reproducible build guarantees: direct pushes to `develop` are unchecked, dependency range specifiers allow silent breaking changes, containerised images are silently overwritten by host bind-mounts, and the regression test suite is never executed in CI — leaving critical authentication, RBAC, and collaborative-editing logic unvalidated before each merge. [J:CTCOAMSHM-115]

### Business Value
Unchecked direct pushes and unvalidated dependency changes introduce production regressions and security exposure with no automated safety net. Closing these four gaps reduces mean-time-to-detect regressions, ensures reproducible deployments across all environments, and provides a trustworthy foundation for the real-time collaborative handover feature that is central to the platform's operational value. [J:CTCOAMSHM-115]

---

## Requirements

| ID | Type | Priority | Description | Depends On |
|----|------|----------|-------------|------------|
| REQ-001 | Functional | P0 | The system shall reject any commit pushed directly to the `develop` branch at the Git server level; only commits arriving via an approved merge request shall be accepted onto `develop`. | — |
| REQ-002 | Functional | P0 | The system shall require approval from at least one Maintainer before any merge request targeting `develop` is permitted to merge. | REQ-001 |
| REQ-003 | Functional | P0 | The system shall enforce that the Maintainer approving a merge request is not the same individual who authored that merge request. | REQ-002 |
| REQ-004 | Technical | P0 | The system shall pin all Python dependencies — including flask-sock and all remaining packages in the dependency manifest (45+ total) — to exact versions using `==` specifiers, guaranteeing identical dependency resolution across independent fresh installs. | — |
| REQ-005 | Technical | P0 | The system shall ensure that the container's application directory is populated exclusively from the image build artefact at runtime; no host filesystem bind-mount shall overwrite or shadow the application directory in any production container configuration. | — |
| REQ-006 | Technical | P0 | The system shall execute the full regression test suite — comprising all 10 pytest files covering authentication/RBAC, collaborative editing, roster scheduling, and API contracts — as a discrete, mandatory stage of the automated CI pipeline triggered on every merge request targeting `develop`. | REQ-001 |
| REQ-007 | Functional | P0 | The system shall allow an authenticated user who holds the required permissions to initiate and complete the core action end-to-end without manual intervention or external assistance. | REQ-010 |
| REQ-008 | Functional | P0 | The system shall validate all inputs prior to executing the core action and shall display a specific, user-facing error message for every distinct validation failure, preventing execution until all validations pass. | — |
| REQ-009 | Functional | P0 | The system shall handle simultaneous modification attempts by two or more users on the same resource without data loss, data corruption, or leaving the resource in an inconsistent state. | REQ-007 |
| REQ-010 | Functional | P0 | The system shall deny execution of the core action to any user who does not hold the required permissions and shall present a permission-denied error message to that user; no partial execution shall occur. | — |
| REQ-011 | Non-Functional | P0 | The system shall respond to every user-initiated interactive action within the core feature within **100 ms maximum** — measured from the moment of user input to the moment the result is visible to the initiating user — under normal system load. | REQ-007 |
| REQ-012 | Functional | P1 | The system shall continue to operate when a network timeout or dependent service unavailability is encountered during core action execution; the failure shall be logged internally and the system shall remain accessible to users, with the affected capabilities explicitly degraded rather than silently unavailable. | REQ-007 |

---

## Acceptance Criteria

### REQ-001 — Branch Protection (P0)

- **AC-001a** *(happy-path)*: Given a developer with repository push access who has opened a merge request from a feature branch that receives the required approvals, when the approved merge request is merged, then the commits are successfully integrated into `develop`.
- **AC-001b** *(error-path)*: Given a developer with repository push access, when they attempt to push one or more commits directly to `develop` without a merge request, then the Git server rejects the push before any commit is recorded on `develop` and returns an error message to the developer.

### REQ-002 — Maintainer Approval Requirement (P0)

- **AC-002a** *(happy-path)*: Given a merge request targeting `develop` with at least one approval from a Maintainer who is not the author, when a team member initiates the merge, then the merge is permitted to complete.
- **AC-002b** *(error-path)*: Given a merge request targeting `develop` that has received zero Maintainer approvals, when any team member attempts to merge it, then the system blocks the merge action and indicates that at least one Maintainer approval is required.

### REQ-003 — Independent Reviewer Enforcement (P0)

- **AC-003a** *(happy-path)*: Given a merge request authored by Maintainer A, when Maintainer B (a different individual) approves the request, then the approval is counted as valid and the merge-readiness condition is satisfied.
- **AC-003b** *(error-path)*: Given a merge request authored by Maintainer A, when Maintainer A provides a self-approval, then the system does not count this as a valid approval and continues to block the merge until an independent Maintainer approves.

### REQ-004 — Exact Dependency Pinning (P0)

- **AC-004a** *(happy-path)*: Given the project's dependency manifest with all packages pinned to exact `==` versions, when a fresh install is performed in two independent isolated environments, then the installed set of packages (name and version) is identical in both environments.
- **AC-004b** *(error-path)*: Given a dependency manifest that contains a range specifier (e.g., `>=x.y`, `~=x.y`, `>x.y`) for any package, when the manifest is validated as part of the CI pipeline, then the validation step fails and identifies the package(s) with non-exact specifiers.

### REQ-005 — Container Application Directory Isolation (P0)

- **AC-005a** *(happy-path)*: Given a container started from the production image with no additional volume or bind-mount overrides, when the application starts, then the application directory contains exactly and only the files baked into the image at build time.
- **AC-005b** *(error-path)*: Given any production container configuration file that includes a host bind-mount targeting the application directory, when an automated configuration lint or review check evaluates that file, then the check fails and reports the offending bind-mount configuration.

### REQ-006 — Regression Test Suite Execution in CI (P0)

- **AC-006a** *(happy-path)*: Given a merge request targeting `develop`, when the CI pipeline executes, then all 10 regression pytest files run and their individual pass/fail/error results are reported in the pipeline output.
- **AC-006b** *(error-path)*: Given a code change that causes one or more of the 10 regression tests to fail, when the CI pipeline runs, then the regression test stage is marked as failed and the merge request is blocked from merging until the failures are resolved.
- **AC-006c** *(boundary — no test file changes)*: Given a merge request that modifies only application source code and no regression test files, when CI executes, then the full suite of 10 regression test files still runs against the modified application code and its results are reported.

### REQ-007 — Core Action Execution (P0)

- **AC-007a** *(happy-path)*: Given an authenticated user with the required permissions and all inputs provided in valid form, when the user initiates the core action, then the action completes successfully end-to-end and the user receives a confirmation of completion.
- **AC-007b** *(error-path)*: Given a core action execution that encounters an unrecoverable server-side error mid-operation, when the error occurs, then the system does not persist a partially committed state, rolls back any partial changes, and presents the user with an informative error notification.

### REQ-008 — Input Validation (P0)

- **AC-008a** *(happy-path)*: Given a submission in which all required input fields contain valid, non-empty values, when the user submits the core action, then input validation passes and execution proceeds.
- **AC-008b** *(error-path — null/empty input)*: Given a submission in which one or more required input fields are empty or null, when the user attempts to submit, then the system displays a specific error message that identifies the offending field(s) by name, and prevents execution of the core action.
- **AC-008c** *(error-path — invalid format)*: Given a submission in which an input field contains a value that fails type, length, or format validation, when the user attempts to submit, then the system displays a field-level error message describing what is expected, and prevents execution.

### REQ-009 — Concurrent Modification Handling (P0)

- **AC-009a** *(happy-path — non-conflicting)*: Given two users each modifying different, non-overlapping sections of the same resource simultaneously, when both operations complete, then both modifications are preserved and neither is lost or corrupted.
- **AC-009b** *(error-path — conflicting)*: Given two users initiating conflicting modifications to the same section of the same resource simultaneously, when the conflict is detected, then the system resolves the conflict without data loss and without leaving the resource in a corrupted or inconsistent state.

### REQ-010 — Permission-Based Access Control (P0)

- **AC-010a** *(happy-path)*: Given an authenticated user who holds the required permission for the core action, when the user initiates the action, then the system permits execution to proceed.
- **AC-010b** *(error-path — insufficient permissions)*: Given an authenticated user who does not hold the required permission, when the user attempts to initiate the core action, then the system denies the request, displays a permission-denied error message, and performs no partial execution.
- **AC-010c** *(error-path — unauthenticated)*: Given a request to perform the core action that carries no valid session credential, when the request is received, then the system denies access and directs the requestor to authenticate before proceeding. [C:Api_Contracts]

### REQ-011 — Real-Time Latency (P0)

- **AC-011a** *(happy-path)*: Given normal system load, when a user initiates any interactive action within the core feature, then the system produces a visible response to that user within 100 ms of their input event.
- **AC-011b** *(boundary — load condition)*: Given a measurement taken across a statistically representative sample of interactive operations at maximum expected concurrent user count, when results are evaluated, then no individual response time in the sample exceeds 100 ms end-to-end.

### REQ-012 — Graceful Degradation on Network Failure (P1)

- **AC-012a** *(happy-path)*: Given all dependent services available and reachable, when the core action executes, then the full feature set is available to the user without any degradation notice.
- **AC-012b** *(error-path)*: Given a network timeout or service unavailability encountered during core action execution, when the error occurs, then the system logs the failure internally, keeps the user's session active, continues to serve other requests, and presents the user with a visible indication that the specific capability is temporarily degraded rather than allowing it to fail silently.

---

## Constraints

### Performance
- Interactive operations within the core feature shall respond within a **maximum of 100 ms** from user input to visible result under normal system load. [J:CTCOAMSHM-115]
- A throughput (RPS) target has not been confirmed for this specification. Performance validation methodology — including applicable percentile targets (P50, P95, P99) and whether validation is automated or manual — must be agreed with the engineering lead before implementation begins. See Open Item #6 in `docs/phase-2/interrogation_summary.md`.

### Security
- All operations subject to permission enforcement (REQ-010) shall rely on the platform's existing server-side session validation, which executes on every inbound request. [C:Api_Contracts] No path through the core feature shall bypass session validation.
- The system shall produce an auditable log entry for every permission-denial event triggered by the core action; each log entry shall include sufficient context to identify the requesting user identity and the denied operation.
- Branch protection and merge request approval enforcement (REQ-001 – REQ-003) are server-side controls that shall be resistant to bypass via client-side manipulation or direct API calls that circumvent the Git server.

### Compatibility
- No changes introduced by this specification shall alter any existing HTTP API response schemas, session management contracts, or end-user–facing workflows. [C:Api_Contracts] All gap-remediation changes are internal to developer process and build infrastructure; the core feature is a net-new capability.
- The exact version pin for flask-sock (REQ-004) shall be verified for compatibility with the full existing dependency manifest before being applied; no cascading version changes to other dependencies are permitted as a consequence of this single pin.
- The removal or restriction of the container bind-mount (REQ-005) shall preserve functional parity with the existing production runtime environment; no application behaviour observable by end users shall change as a result.

### Accessibility
Accessibility requirements are not defined in this specification. The core action's user-interface surface has not yet been described with sufficient fidelity to establish accessibility targets. This is deferred to a subsequent specification revision once the core action is identified (see Open Item #5, `docs/phase-2/interrogation_summary.md`).

---

## Non-Goals

| Non-Goal | Rationale |
|----------|-----------|
| Refactoring, correcting, or expanding the logic of existing regression test assertions. | Only CI pipeline integration of the 10 existing test files is confirmed in scope. Modifying test correctness is a separate quality initiative requiring its own requirements and prioritisation. |
| Expanding regression test coverage beyond the 10 existing pytest files in the suite. | Additional test authorship requires dedicated scoping and resourcing; it is explicitly excluded from CTCOAMSHM-115. [J:CTCOAMSHM-115] |
| Implementing proactive retry logic, fallback service routing, or message queuing for network failures. | The agreed error-handling strategy for REQ-012 is silent internal logging with graceful degradation. Retry and queuing mechanisms introduce out-of-scope complexity. |
| Multi-step or multi-stage workflow orchestration for the core action. | The core action is confirmed as a single atomic operation. Orchestrating multi-step workflows introduces transaction-boundary and rollback complexity that is outside the agreed scope. |
| Changing the Maintainers-only approval policy to include a broader reviewer pool or a different approval count. | The Maintainers-only policy is the explicitly agreed minimum standard. Any change to the reviewer pool requires separate governance approval and is out of scope for this ticket. |

---

## Assumptions

| ID | Assumption | Risk if Wrong | Validation Required Before Implementation? |
|----|-----------|---------------|---------------------------------------------|
| A-01 | The three CI pipeline fixes correctly integrate all 10 regression pytest files into CI execution such that none are silently skipped or excluded by path filters or stage conditions. | **MEDIUM** — If any file is silently skipped, high-value areas such as authentication/RBAC and collaborative editing remain unguarded in the CI pipeline. | **Yes** — Verify via a CI dry-run that all 10 files appear individually in pipeline test-execution output before treating REQ-006 as satisfied. |
| A-02 | The two process enforcement artefacts created to govern code review fully prevent self-approval and guarantee independent Maintainer review without an exploitable bypass path. | **MEDIUM** — A configuration gap could allow single-author control of critical merges to persist, undermining REQ-002 and REQ-003. | **Yes** — Test enforcement behaviour by attempting self-approval on a canary merge request in a staging project before applying to the production repository. |
| A-03 | Silent internal logging with visible feature degradation (but no retry or user-queued fallback) on network timeout is operationally acceptable to all stakeholders. | **MEDIUM** — Stakeholders may expect retry, fallback routing, or explicit user-notification queuing; misalignment discovered post-implementation would require rework of REQ-012. | **Yes** — Confirm the degradation behaviour and user-facing messaging expectations with the product owner before implementation of REQ-012 begins. |
| A-04 | Sub-100ms maximum response latency is achievable with the current platform architecture and data access patterns under expected concurrent load, without requiring out-of-scope architectural changes. | **MEDIUM** — Latency may be infeasible without structural work outside this ticket's scope; no baseline performance measurement currently exists. | **Yes** — Conduct baseline interactive-latency measurement before committing the 100 ms target to acceptance testing criteria for REQ-011. |
| A-05 | The core action is a single atomic operation with well-defined transaction boundaries; concurrent modification handling does not require distributed coordination or multi-step saga patterns. | **MEDIUM** — If the action is compositional, rollback strategy and conflict resolution become materially more complex than assumed, affecting REQ-009 scope. | **Yes** — Confirm the atomic vs. multi-step nature of the core action with the engineering lead before architecture design begins. See Open Item #5, `docs/phase-2/interrogation_summary.md`. |
| A-06 | Pinning flask-sock to an exact version will be compatible with all other packages in the existing dependency manifest without requiring manual conflict resolution. | **LOW** — A conflict would surface immediately during install verification and is mitigated by the CI dependency validation check (AC-004a). | **No** — Compatibility is verified as a natural step of the install validation process; no separate pre-implementation gate is required. |
| A-07 | Maintainers are technically competent and consistently engaged such that Maintainer-only approval constitutes a meaningful quality gate rather than a rubber-stamp. | **LOW** — This is an explicit governance decision owned by the team; risk cannot be mitigated by system controls alone. | **No** — A governance assumption; not system-validatable. |

---

## Edge Cases

| ID | Scenario | Expected Behaviour | Related Requirement |
|----|----------|--------------------|---------------------|
| EC-01 | A required input field is submitted as an empty string or null value. | The system rejects the submission, displays a field-specific error message identifying the empty/null field, and prevents the core action from executing. | REQ-008 |
| EC-02 | A user's authenticated session expires while they are completing the core action input form and then attempts to submit. | The system detects the expired session on submission, denies the request, preserves the user's entered data where technically feasible, and redirects the user to re-authenticate before retrying. | REQ-010 [C:Api_Contracts] |
| EC-03 | Two users simultaneously attempt to acquire an edit lock on the same resource section. | The system grants the lock to exactly one user; the second request is denied or queued with an informative message. Neither user's data is lost or corrupted. | REQ-009 [C:Api_Contracts] |
| EC-04 | A network timeout occurs after the core action has been partially processed server-side but before a response is delivered to the client. | The server does not persist any partial state; the operation is treated as uncommitted and rolled back; the failure is logged internally; the user may safely retry the action without risk of duplication or corruption. | REQ-012, REQ-009 |
| EC-05 | A developer pushes a single-character typo fix directly to `develop`, perceiving the change as too trivial to warrant a merge request. | The Git server rejects the push regardless of the perceived risk of the change. No exception to branch protection is granted for change size or author seniority. | REQ-001 |
| EC-06 | A new regression test file is added to the test suite directory but the CI pipeline configuration does not yet reference it, resulting in a potential coverage gap. | The CI stage's test-discovery mechanism detects and executes the new file automatically, or an explicit configuration audit check identifies and reports the gap; the pipeline does not silently pass with a reduced test count. | REQ-006 |

---

## Backward Compatibility

**No breaking changes** are introduced by any requirement in this specification.

- **Branch protection and MR enforcement (REQ-001 – REQ-003):** These are Git server–level workflow controls that alter the developer commit process. They do not affect any HTTP API contract, response schema, session behaviour, or end-user–facing application functionality. [C:Api_Contracts]
- **Exact dependency pinning (REQ-004):** Applying `==` specifiers to packages already present in the dependency manifest does not change the effective installed package set if those packages were previously resolving to the same versions in practice. Compatibility is verified by install validation (AC-004a).
- **Container configuration correction (REQ-005):** Removing the host bind-mount restores the runtime environment to match the image build artefact as originally intended. No application-level API or data schema changes result.
- **CI regression test integration (REQ-006):** Adding the test suite to the CI pipeline does not alter application behaviour. It may cause previously hidden failures to surface and block merges — which is the intended outcome.
- **Core feature (REQ-007 – REQ-012):** The core feature is a net-new capability. It shall not modify any existing API response formats, session management behaviour, or data structures used by existing platform features. All additions are strictly additive. [C:Api_Contracts]

---

## Dependencies

| Dependency | Type | Purpose | Notes |
|------------|------|---------|-------|
| GitLab — Branch Protection | Infrastructure | Server-side enforcement of REQ-001: rejection of direct pushes to `develop`. | Requires Maintainer-level access to GitLab project settings to configure protected branch rules. |
| GitLab — Merge Request Approval Rules | Infrastructure | Enforcement of REQ-002 and REQ-003: mandatory Maintainer approval and self-approval prevention. | Requires approval policy configuration in GitLab project settings; configuration artefacts confirmed as open item in `docs/phase-2/interrogation_summary.md`, Open Item #2. |
| GitLab — CI/CD Pipeline | Infrastructure | Automated execution of the regression test suite per REQ-006 on every merge request targeting `develop`. | Pipeline configuration must be updated to include the regression test stage; the three specific CI fixes are detailed in `docs/phase-2/interrogation_summary.md`, Open Item #1. |
| Python Dependency Manifest | Internal | The authoritative package list that must be audited and updated to satisfy REQ-004. | All 45+ package entries must be migrated to `==` specifiers; the specific pinned version of flask-sock is an open item (`docs/phase-2/interrogation_summary.md`, Open Item #8). |
| Platform Session Validation | Internal | REQ-010 permission enforcement for the core action depends on the existing server-side session validation mechanism that runs on every inbound request. [C:Api_Contracts] | No changes to session validation logic are in scope; the core feature consumes this capability as-is. |
| Platform Section-Lock and Draft-Persistence Model | Internal | REQ-009 concurrent modification handling depends on the existing section-locking primitives already present in the collaborative editing model. [C:Api_Contracts] | The specific conflict-resolution strategy for the core action must be compatible with this existing model; the resolution approach is an open item (`docs/phase-2/interrogation_summary.md`, Open Item #3). |

**No external third-party service integrations are required by this specification.** [J:CTCOAMSHM-115]

---

## Glossary

| Term | Definition |
|------|------------|
| **Core Action** | The primary user-facing operation that is the subject of REQ-007 through REQ-012. The specific operation name and workflow have not yet been confirmed; see Open Item #5 in `docs/phase-2/interrogation_summary.md`. |
| **Develop Branch** | The `develop` Git branch that serves as the integration target for all feature branches in the Shifthandover project. |
| **Merge Request (MR)** | A request to integrate commits from a feature branch into `develop`; the unit of code review in the project's GitLab workflow. |
| **Maintainer** | A GitLab project role with elevated privileges, including the authority to approve merge requests and administer project-level settings. |
| **RBAC** | Role-Based Access Control — the mechanism by which the platform restricts operations to users holding specific roles or permissions. |
| **SSE (Server-Sent Events)** | A unidirectional HTTP streaming mechanism used by the platform to push real-time change notifications from server to connected clients in collaborative editing sessions. [C:Api_Contracts] |
| **Section Lock** | A per-section concurrency control primitive within the collaborative editing model that prevents simultaneous modification of the same handover section by multiple users. [C:Api_Contracts] |
| **Regression Test Suite** | The collection of 10 pytest files covering authentication/RBAC, collaborative editing, roster scheduling, and API contract validation, intended to execute in the CI pipeline on every merge request. |
| **Exact Version Pin** | A Python package version specifier using the `==` operator (e.g., `flask-sock==0.2.4`) that constrains installation to exactly one package version, eliminating resolution variability introduced by range operators. |
| **Bind-Mount** | A Docker volume configuration that maps a directory from the host filesystem into a running container, potentially overwriting files already present in the container image at the same path. |
| **CI/CD** | Continuous Integration / Continuous Deployment — the automated pipeline that builds, tests, and validates code changes on every merge request before they are integrated into `develop`. |
| **Degraded Functionality** | A defined system state in which a subset of features dependent on an unavailable service is non-operational, while the system itself remains accessible and serving requests. Users shall receive visible indication of degradation rather than encountering silent failure. |
| **Fernet** | A symmetric authenticated encryption scheme used by the platform for local credential and secret storage. [C:Api_Contracts] |