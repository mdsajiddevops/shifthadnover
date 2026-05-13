# Requirements Summary

## Executive Overview

This work addresses critical process, architecture, dependency, and testing gaps identified through archaeological review of a GitLab project, while simultaneously establishing functional and non-functional requirements for a core feature implementation. Three major process fixes have been completed: develop branch is now protected against direct pushes (merge-only, Maintainers approval required), code review enforcement has been implemented (two files created), and regression test suite has been integrated into CI (three fixes applied). Additional technical debt fixes include pinning flask-sock to exact version for reproducible builds and resolving docker-compose bind-mount conflicts that masked the containerised image. The feature itself requires real-time interactivity (<100ms latency), robust input validation with user-facing error messages, and graceful handling of concurrent modifications and permission-based access control.

---

## Functional Requirements

**Branch Protection & Code Review:**
- The system shall reject all direct pushes to the develop branch at the Git server level; no commits bypassing merge requests will be accepted. *(gap_process: high)*
- The system shall enforce merge request review by Maintainers only before code can be merged into develop. *(gap_process: high)*
- The system shall require an independent second reviewer (not the code author) on all merge requests. *(gap_process: medium — two files created to enforce)*

**Dependency Management:**
- The system shall pin flask-sock (and all 45+ Python dependencies) to exact versions using == specifiers to guarantee reproducible builds across fresh pip installs. *(gap_dependencies: medium)*

**Container Architecture:**
- The system shall not include bind-mounts (volumes: - .:/app) in docker-compose.yml that overwrite COPY directives from the Dockerfile; /app directory shall be populated exclusively by the image build step. *(gap_architecture: medium)*

**Testing & CI Integration:**
- The system shall execute the regression test suite (10 pytest files in tests/regression/ covering auth/RBAC, collaborative editing, roster scheduler, and API contracts) as part of the automated CI pipeline. *(gap_testing: medium — three fixes applied)*

**Feature: Core Action Execution:**
- The system shall allow users with required permissions to perform the core action end-to-end without manual intervention or assistance. *(acceptance_criteria)*
- The system shall enforce all input validations and display clear, user-facing error messages for every validation failure. *(acceptance_criteria)*

---

## Constraints & Non-Functional Requirements

**Performance:**
- Real-time latency for interactive operations: sub-100ms maximum response time from user input to visible result. *(constraints)*

**Reproducibility & Maintainability:**
- All Python dependencies must use exact version pins (== specifiers) to eliminate silent breaking-change introductions from range specifiers (e.g., >=0.2.0). *(gap_dependencies)*

**Access Control:**
- develop branch protection is enforced server-side; direct pushes are rejected by GitLab before reaching the repository. *(gap_process: high)*
- Code changes must be reviewed and approved by at least one Maintainer independent of the author. *(gap_process: medium)*

**Container Isolation:**
- Docker containers shall not have host filesystem contents visible in /app; the image filesystem shall be the sole source of truth at runtime. *(gap_architecture)*

---

## Edge Cases & Error Handling

| Scenario | Expected Behaviour | Requirement Traced |
|----------|-------------------|-------------------|
| **Empty or null input** | System displays clear validation error message and prevents action execution. | Input validation requirement |
| **Concurrent modifications** | System handles simultaneous user modifications gracefully without data corruption or race conditions. *(specific conflict resolution strategy not specified; risk noted in Assumptions)* | Core action execution |
| **Network timeout or third-party service unavailability** | System logs error silently and continues with degraded functionality; user experience degrades but system remains available. | Error handling strategy |
| **User lacking required permissions** | System prevents operation execution and displays permission-denied error message. | Access control + input validation |

---

## Dependencies & Integrations

**External Services:**
- None. *(dependencies: no external dependencies)*

**Internal/Infrastructure:**
- **GitLab** (protected branches API, CI/CD pipeline, merge request approval enforcement)
- **Python ecosystem** (flask, flask-sock==exact-pin, pytest for regression tests)
- **Git server** (enforce branch protection rules at push time)

**No external third-party integrations required.**

---

## Scope Boundaries

**Explicitly In-Scope:**
- Protecting develop branch from direct pushes and enforcing MR-only merge workflow
- Mandatory independent code review for all PRs (Maintainers only)
- Exact version pinning for all Python dependencies
- Fixing docker-compose bind-mount to prevent /app directory masking
- Integrating regression test suite into CI pipeline (three specific fixes)
- Feature: Core action implementation with input validation, error handling, concurrent modification support, and sub-100ms latency
- Feature: Permission-based access control for core action
- Feature: Graceful degradation when network timeouts occur

**Explicitly Out-of-Scope:**
- Refactoring existing test assertions or modifying test logic (only CI integration)
- Expanding test coverage beyond the 10 regression tests already created
- Changing the Maintainers-only code review policy (this is the agreed minimum)
- Proactive retry logic or fallback services for network failures (silent logging + degradation is the agreed strategy)
- Multi-step workflow orchestration (only atomic core action in scope)

---

## Acceptance Criteria

**Core Action Execution:**
- Given a user with required permissions and valid input, when the user initiates the core action, then the action completes successfully end-to-end without errors.

**Input Validation:**
- Given an empty, null, or invalid input value, when the user attempts to submit the action, then the system displays a specific error message and prevents execution.

**Concurrent Modifications:**
- Given two or more users attempting to modify the same resource simultaneously, when concurrent operations are initiated, then the system resolves modifications without data loss or corruption.

**Permission-Based Access:**
- Given a user without required permissions, when the user attempts the core action, then the system displays a permission-denied error and prevents execution.

**Real-Time Performance:**
- Given normal system load, when a user initiates an interactive action, then the system responds with <100ms latency from input to visible result.

**Error Resilience:**
- Given a network timeout or service unavailability during action execution, when the error occurs, then the system logs the failure and continues operating with degraded functionality.

**Branch Protection:**
- Given a developer pushing a commit directly to develop without a merge request, when the push is attempted, then the Git server rejects the push with an error message.

**Code Review Enforcement:**
- Given a merge request to develop, when the MR is created, then it requires approval from at least one Maintainer (who is not the author) before merging is permitted.

---

## Assumptions & Risks

| Assumption | Risk Level | Impact if Wrong |
|-----------|-----------|-----------------|
| The three regression test fixes are correct and comprehensively integrate all 10 pytest files into CI. | **MEDIUM** | Regression tests may still be silently skipped in CI; high-value areas (auth/RBAC, collaborative editing) remain untested in pipeline. |
| The two process files created fully enforce independent code review without reviewer collusion or bypass. | **MEDIUM** | Code review policy may be circumvented; single-author control of critical changes continues. |
| "Degraded functionality" on network timeout is operationally acceptable (specific degradation mode undefined). | **MEDIUM** | User experience may be unacceptable; stakeholders may expect retry, fallback, or queuing instead of silent failure logging. |
| Sub-100ms latency is achievable with current architecture and database design. | **MEDIUM** | Latency requirement may be infeasible; performance testing results unknown; feature may require optimization or scope reduction. |
| The core action is a single atomic operation, not a multi-step workflow. | **MEDIUM** | Concurrent modification handling may be more complex than assumed; transaction boundaries and rollback strategy not specified. |
| flask-sock==exact-pin will remain stable and compatible with rest of the codebase without requiring future version changes. | **LOW** | If flask-sock introduces critical bug fixes only in newer versions, exact pin may prevent security/stability improvements (mitigated by periodic review cycles). |
| Maintainers-only merge approval is sufficient to prevent architectural, security, and logic regressions. | **LOW** | This is an explicit decision addressing the review gap; low risk if Maintainers are technically competent and engaged. |

---

## Contradictions

**None detected.**

All answers are consistent and unambiguous:
- Gap fixes are confirmed (architecture, dependencies, testing, process).
- Branch protection decision is explicit and non-negotiable.
- Feature requirements align with acceptance criteria and edge case handling.
- No conflicting performance, security, or functional directives identified.

---

## Open Items

1. **Test Integration Details** — What are the three specific regression test fixes applied? How are they integrated into .gitlab-ci.yml (new test stage, added to existing stage, or pattern-based inclusion)?

2. **Code Review Enforcement Implementation** — What are the two files created to enforce independent code review? Are they:
   - GitLab CI pipeline rules?
   - Approval policy configuration files?
   - Custom webhook or bot integration?

3. **Concurrent Modification Strategy** — What is the specific conflict resolution approach for concurrent modifications? (Optimistic locking, last-write-wins, merge conflict UI for users, transaction rollback?)

4. **Degraded Functionality Definition** — When a network timeout occurs and the system "continues with degraded functionality," what specific features remain available and what is disabled? Are there user-facing warnings?

5. **Core Action Name & Workflow** — The requirements reference "the core action" without naming it. What is the specific user operation being implemented? (e.g., roster update, collaborative edit submission, RBAC policy change, handover acknowledgment?)

6. **Performance Validation** — Will sub-100ms latency be verified by automated performance tests, load tests, or manual testing? What is the acceptance criteria for passing performance validation (P50, P95, P99 percentiles)?

7. **Docker-Compose Resolution** — Was the bind-mount removed entirely, made conditional (development-only), or separated into dev and prod compose files? What is the production-safe approach?

8. **Flask-Sock Exact Version** — What is the pinned version number for flask-sock (e.g., flask-sock==0.2.4)? Is there a documented reason for selecting this version?