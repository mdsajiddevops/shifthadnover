# Artifact Digest: CTCOAMSHM-115

_All Phase 2 artifacts approved. Resuming from implementation._

## Requirements (problem_spec.md)

- **Problem Specification — Shifthandover: Gap Remediation & Core Feature Implementation**
- ---
- **Meta**
- | Field | Value |
- |-------|-------|
- | **Ticket ID** | CTCOAMSHM-115 [J:CTCOAMSHM-115] |
- | **Project** | Shifthandover (`shifthandover_v3`) |
- | **Creation Date** | 2026-05-12 |
- | **Status** | Draft — Pending Architecture Review |
- | **Interrogation Summary** | `docs/phase-2/interrogation_summary.md` |
- ---
- **Problem Statement**
- **Summary**
- Remediate four confirmed process and architecture gaps (branch protection, dependency pinning, container isolation, CI test integration) in the Shifthandover platform, and define requirements for a permission-gated, real-time core action feature. [J:CTCOAMSHM-115]
- **User Problem**
- Development contributors lack enforced review gates and reproducible build guarantees: direct pushes to `develop` are unchecked, dependency range specifiers allow silent breaking changes, containerised images are silently overwritten by host bind-mounts, and the regression test suite is never executed in CI — leaving critical authentication, RBAC, and collaborative-editing logic unvalidated before each merge. [J:CTCOAMSHM-115]
- **Business Value**
- Unchecked direct pushes and unvalidated dependency changes introduce production regressions and security exposure with no automated safety net. Closing these four gaps reduces mean-time-to-detect regressions, ensures reproducible deployments across all environments, and provides a trustworthy foundation for the real-time collaborative handover feature that is central to the platform's operational value. [J:CTCOAMSHM-115]
- ---
- **Requirements**

## Architecture (design_spec.md)

- **Architecture Design Specification**
- **Shifthandover: Gap Remediation & Core Feature Implementation**
- ---
- **Meta**
- | Field | Value |
- |-------|-------|
- | **Ticket ID** | CTCOAMSHM-115 [J:CTCOAMSHM-115] |
- | **Project** | shifthandover_v3 |
- | **Spec Date** | 2026-05-12 |
- | **Problem Spec** | `docs/phase-2/problem_spec.md` |
- | **Status** | Draft — Pending Architecture Review |
- ---
- **Problem Spec Reference**
- See [problem_spec.md](problem_spec.md) — implements REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, REQ-010, REQ-011, REQ-012. [J:CTCOAMSHM-115]
- ---
- **Current Architecture**
- **Deployment Topology**
- The platform is a server-side rendered Flask monolith (`shifthandover_v3`) deployed behind Nginx (TLS termination) with Gunicorn as the WSGI server. [C:Api_Contracts] No dedicated REST versioning prefix exists; all routes are served from the application root, with a Swagger UI available at `/apidocs`. [C:Api_Contracts]
- **Blueprint Organisation**
- Approximately 45–48 Flask Blueprints are registered in `app.py`, each scoped to a single domain area — handover management, roster/scheduling, admin, escalation, collaboration, SSO, and reporting. [C:Api_Contracts] Route handlers are organised under a `routes/` directory, one file per blueprint domain.

## Implementation Plan (implementation_plan.md)

- **Summary**
- This implementation plan coordinates remediation of four confirmed developer-process and infrastructure gaps — branch protection, MR approval enforcement, exact dependency pinning, and container bind-mount isolation — alongside CI integration of the existing regression suite and delivery of a net-new, permission-gated CoreAction feature within the `shifthandover_v3` Flask monolith. [J:CTCOAMSHM-115] All twelve P0/P1 requirements are satisfied through GitLab configuration artefacts, CI pipeline extensions, manifest updates, and a layered Flask blueprint → service → repository implementation that reuses the platform's existing session validation, section-locking, SSE, and audit infrastructure. [C:Api_Contracts] No existing HTTP API contracts, session management behaviour, or end-user workflows are altered by any change in this plan. [C:Api_Contracts]
- ---
- **Key Requirements & Constraints**
- | ID | Priority | See |
- |----|----------|-----|
- | REQ-001 | P0 | problem_spec.md |
- | REQ-002 | P0 | problem_spec.md |
- | REQ-003 | P0 | problem_spec.md |
- | REQ-004 | P0 | problem_spec.md |
- | REQ-005 | P0 | problem_spec.md |
- | REQ-006 | P0 | problem_spec.md |
- | REQ-007 | P0 | problem_spec.md |
- | REQ-008 | P0 | problem_spec.md |
- | REQ-009 | P0 | problem_spec.md |
- | REQ-010 | P0 | problem_spec.md |
- | REQ-011 | P0 | problem_spec.md |
- | REQ-012 | P1 | problem_spec.md |
- **Mandatory validation gates before application component work begins** (see Assumptions A-01–A-05, problem_spec.md): core action identity and payload schema must be confirmed with the engineering lead; sub-100ms latency achievability must be measured against the current architecture; degradation behaviour and user-facing messaging must be confirmed with the product owner. [J:CTCOAMSHM-115]
- ---
