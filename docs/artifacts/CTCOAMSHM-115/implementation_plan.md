## Summary

This implementation plan coordinates remediation of four confirmed developer-process and infrastructure gaps — branch protection, MR approval enforcement, exact dependency pinning, and container bind-mount isolation — alongside CI integration of the existing regression suite and delivery of a net-new, permission-gated CoreAction feature within the `shifthandover_v3` Flask monolith. [J:CTCOAMSHM-115] All twelve P0/P1 requirements are satisfied through GitLab configuration artefacts, CI pipeline extensions, manifest updates, and a layered Flask blueprint → service → repository implementation that reuses the platform's existing session validation, section-locking, SSE, and audit infrastructure. [C:Api_Contracts] No existing HTTP API contracts, session management behaviour, or end-user workflows are altered by any change in this plan. [C:Api_Contracts]

---

## Key Requirements & Constraints

| ID | Priority | See |
|----|----------|-----|
| REQ-001 | P0 | problem_spec.md |
| REQ-002 | P0 | problem_spec.md |
| REQ-003 | P0 | problem_spec.md |
| REQ-004 | P0 | problem_spec.md |
| REQ-005 | P0 | problem_spec.md |
| REQ-006 | P0 | problem_spec.md |
| REQ-007 | P0 | problem_spec.md |
| REQ-008 | P0 | problem_spec.md |
| REQ-009 | P0 | problem_spec.md |
| REQ-010 | P0 | problem_spec.md |
| REQ-011 | P0 | problem_spec.md |
| REQ-012 | P1 | problem_spec.md |

**Mandatory validation gates before application component work begins** (see Assumptions A-01–A-05, problem_spec.md): core action identity and payload schema must be confirmed with the engineering lead; sub-100ms latency achievability must be measured against the current architecture; degradation behaviour and user-facing messaging must be confirmed with the product owner. [J:CTCOAMSHM-115]

---

## Architecture Summary

| COMP-ID | Name | File Path | See |
|---------|------|-----------|-----|
| COMP-001 | Protected Branch Rule | GitLab project settings; `docs/ops/branch-protection.md` | design_spec.md |
| COMP-002 | MR Approval Policy | `.gitlab/approval_rules.yml`, `CODEOWNERS` | design_spec.md |
| COMP-003 | CI Regression Test Stage | `.gitlab-ci.yml` | design_spec.md |
| COMP-004 | Dependency Pin Validator | `scripts/validate_pins.py` | design_spec.md |
| COMP-005 | Python Dependency Manifest | `requirements.txt` | design_spec.md |
| COMP-006 | Production Container Compose Configuration | `docker-compose.prod.yml`, `docker-compose.yml`, `docker-compose.override.yml` | design_spec.md |
| COMP-007 | CoreAction Blueprint | `routes/core_action.py`, `app.py` | design_spec.md |
| COMP-008 | CoreAction Service | `services/core_action_service.py` | design_spec.md |
| COMP-009 | CoreAction Input Validator | `validators/core_action_validator.py` | design_spec.md |
| COMP-010 | Permission Guard Decorator | `decorators/permission_guard.py` | design_spec.md |
| COMP-011 | CoreAction Repository | `repositories/core_action_repository.py` | design_spec.md |
| COMP-012 | CoreAction Data Model | `models/core_action.py` | design_spec.md |
| COMP-013 | Section Lock Coordinator | `services/section_lock_coordinator.py` | design_spec.md |
| COMP-014 | CoreAction SSE Publisher | `services/sse_publisher.py` | design_spec.md |
| COMP-015 | Degradation Logger | `services/degradation_logger.py` | design_spec.md |
| COMP-016 | Audit Log Writer | `services/audit_log_writer.py` | design_spec.md |
| COMP-017 | CoreAction Audit Log Model | `models/core_action_audit.py` | design_spec.md |

For full component responsibilities, data flows, ADRs, naming conventions, and security considerations, see design_spec.md.

---

## Pre-Implementation Baseline

Run the following against the current `develop` branch and commit all output to `docs/baseline/` before the first implementation task begins:

```bash
# 1. Record installed package set before any dependency changes (REQ-004 baseline)
pip install -r requirements.txt && pip freeze > docs/baseline/freeze_$(date +%Y%m%d).txt

# 2. Run existing non-regression tests; record pass/fail counts as the pre-change baseline
pytest --ignore=tests/regression/ -v --tb=short 2>&1 | tee docs/baseline/tests_existing.log

# 3. Run regression suite standalone; record actual current state (failures expected — document as-is)
pytest tests/regression/ -v --tb=short 2>&1 | tee docs/baseline/tests_regression.log

# 4. Record current docker-compose bind-mount state (REQ-005 baseline)
grep -n "volumes" docker-compose.yml >> docs/baseline/compose_state.txt
```

The latency baseline required by Assumption A-04 is recorded as part of T-003 (see Task Breakdown) via manual timing or request-profiling against a populated development instance; results must be committed to `docs/baseline/latency_baseline.txt` before T-042 is opened.

---

## Task Breakdown

| Task ID | Title | Dependencies | Effort (days) | Component | Type |
|---------|-------|--------------|---------------|-----------|------|
| T-001 | Confirm core action identity, payload schema, and transaction boundaries with engineering lead | — | 0.5 | — | config |
| T-002 | Confirm degradation behaviour and user-facing messaging expectations with product owner | — | 0.5 | — | config |
| T-003 | Establish and record interactive latency baseline on current develop branch | — | 1.0 | — | test |
| T-004 | Configure GitLab protected branch rule: reject all direct pushes to develop | — | 0.5 | COMP-001 | config |
| T-005 | Create branch-protection operational documentation (docs/ops/branch-protection.md) | T-004 | 0.5 | COMP-001 | new |
| T-006 | Create .gitlab/approval_rules.yml (min 1 Maintainer, self-approval disabled) and CODEOWNERS | T-004 | 1.0 | COMP-002 | config |
| T-007 | Verify self-approval enforcement via canary merge request in staging project | T-006 | 0.5 | COMP-002 | test |
| T-008 | Audit all 45+ packages and update requirements.txt with exact == version pins | — | 1.5 | COMP-005 | modify |
| T-009 | Create scripts/validate_pins.py: scan requirements.txt and exit non-zero on any non-== specifier | T-008 | 0.5 | COMP-004 | new |
| T-010 | Create docker-compose.prod.yml: production compose file with no /app bind-mount | — | 0.5 | COMP-006 | new |
| T-011 | Modify docker-compose.yml and create docker-compose.override.yml: isolate bind-mount to dev override | T-010 | 0.5 | COMP-006 | modify |
| T-012 | Update .gitlab-ci.yml: add regression-tests stage, pin-lint step, and compose-lint step | T-006, T-009, T-010, T-011 | 1.0 | COMP-003 | modify |
| T-013 | Verify CI dry-run: confirm all 10 regression files appear individually in pipeline output; confirm pin-lint and compose-lint steps execute | T-012 | 0.5 | COMP-003 | test |
| T-014 | Create CoreAction ORM data model: models/core_action.py (core_action_records table schema) | T-001 | 0.5 | COMP-012 | new |
| T-015 | Create CoreAction Audit Log ORM model: models/core_action_audit.py (core_action_audit_entries table schema) | T-001 | 0.5 | COMP-017 | new |
| T-016 | Create Alembic migration for core_action_records table | T-014 | 0.5 | COMP-012 | migration |
| T-017 | Create Alembic migration for core_action_audit_entries table | T-015 | 0.5 | COMP-017 | migration |
| T-018 | Create CoreAction Input Validator: validators/core_action_validator.py (per-field type, length, format, nullability rules; structured field-keyed error map) | T-001 | 1.0 | COMP-009 | new |
| T-019 | Create Permission Guard Decorator: decorators/permission_guard.py (CORE_ACTION_EXECUTE check; 403 short-circuit before business logic) | — | 0.5 | COMP-010 | new |
| T-020 | Create Section Lock Coordinator: services/section_lock_coordinator.py (acquire/release wrapper over existing SectionLock model) | T-014 | 1.0 | COMP-013 | new |
| T-021 | Create Degradation Logger utility: services/degradation_logger.py (structured internal log entry; typed degradation signal return) | — | 0.5 | COMP-015 | new |
| T-022 | Create Audit Log Writer service: services/audit_log_writer.py (append-only writes for permission-denial and action-lifecycle events) | T-015, T-016, T-017 | 1.0 | COMP-016 | new |
| T-023 | Create CoreAction SSE Publisher service: services/sse_publisher.py (write HandoverChange-compatible event record to DB for SSE delivery) | T-014 | 0.5 | COMP-014 | new |
| T-024 | Create CoreAction Repository: repositories/core_action_repository.py (DB create/update/rollback within single transaction boundary) | T-014, T-016 | 1.0 | COMP-011 | new |
| T-025 | Create CoreAction Service: services/core_action_service.py (atomic orchestration: lock → write → audit → SSE publish; degradation handling) | T-002, T-018, T-019, T-020, T-021, T-022, T-023, T-024 | 2.0 | COMP-008 | new |
| T-026 | Create CoreAction Blueprint: routes/core_action.py (route definitions, request intake, HTTP status/error-body mapping, response serialisation) | T-025 | 1.0 | COMP-007 | new |
| T-027 | Register core_action_bp blueprint in app.py | T-026 | 0.5 | COMP-007 | modify |
| T-028 | Unit tests: CoreAction Input Validator — all validation rules; 100% branch coverage; exact error message assertions (tests/unit/validators/test_core_action_validator.py) | T-018 | 1.0 | COMP-009 | test |
| T-029 | Unit tests: Permission Guard Decorator — permissioned session, unpermissioned session, no session (tests/unit/decorators/test_permission_guard.py) | T-019 | 0.5 | COMP-010 | test |
| T-030 | Unit tests: Section Lock Coordinator — acquire unlocked, acquire locked, release by owner, release by non-owner (tests/unit/services/test_section_lock_coordinator.py) | T-020 | 0.5 | COMP-013 | test |
| T-031 | Unit tests: Degradation Logger — structured log output per exception category; degradation signal contract (tests/unit/services/test_degradation_logger.py) | T-021 | 0.5 | COMP-015 | test |
| T-032 | Unit tests: Audit Log Writer — permission_denied entry fields; action_completed entry fields; append-only enforcement (tests/unit/services/test_audit_log_writer.py) | T-022 | 0.5 | COMP-016 | test |
| T-033 | Unit tests: Dependency Pin Validator script — exits non-zero for >=, ~=, > specifiers; reports all offenders; exits zero for all-== manifest (tests/unit/scripts/test_validate_pins.py) | T-009 | 0.5 | COMP-004 | test |
| T-034 | Integration tests: session validation and permission guard — 401 (no session), 403 (insufficient role), 403 triggers audit entry (tests/integration/test_core_action_auth.py) | T-027, T-029 | 1.0 | COMP-007 | test |
| T-035 | Integration tests: input validation error responses — 422 per field; field name in response body; invalid UUID format (tests/integration/test_core_action_validation.py) | T-027, T-028 | 1.0 | COMP-009 | test |
| T-036 | Integration tests: CoreAction happy path — 200; core_action_records row status=completed; core_action_audit_entries row event_type=action_completed (tests/integration/test_core_action_happy_path.py) | T-027, T-030, T-031, T-032 | 1.5 | COMP-008 | test |
| T-037 | Integration tests: concurrent lock conflict — 409 with locked_by; no core_action_records row inserted for denied request (tests/integration/test_core_action_concurrency.py) | T-027, T-030 | 1.0 | COMP-013 | test |
| T-038 | Integration tests: DB failure degradation — simulated timeout at COMP-011 → 503; no core_action_records row persisted; internal log captured (tests/integration/test_core_action_degradation.py) | T-027, T-031 | 1.0 | COMP-015 | test |
| T-039 | Integration tests: CI pin-lint stage — pipeline with deliberately injected >= specifier exits non-zero and names the offending package | T-012, T-033 | 0.5 | COMP-004 | test |
| T-040 | E2E tests: full CoreAction user journeys — happy path, permission denial, empty-field validation, concurrent lock conflict, mid-operation rollback | T-034, T-035, T-036, T-037, T-038 | 2.0 | COMP-007 | test |
| T-041 | E2E tests: branch protection enforcement (direct push rejected) and self-approval blocking (MR author self-approval not counted) | T-007, T-013 | 0.5 | COMP-001 | test |
| T-042 | Performance validation: verify sub-100ms interactive latency against REQ-011 acceptance criteria; compare against T-003 baseline | T-003, T-040 | 1.0 | COMP-008 | test |

## Implementation Steps


### T-001: Confirm core action identity, payload schema, and transaction boundaries with engineering lead (config) —

- **Purpose**: Eliminate ambiguity in the CoreAction domain before any model or service code is written. Specifically: confirm the exact fields and types of `payload` (JSONB), whether `resource_id` FK target is resolved (Open Item #5), the exact transaction boundary (single DB transaction vs. saga), and the rollback trigger conditions for `status=rolled_back`. [C:space/page-title]
- **File(s)**: No code files. Output: a recorded decision in the project wiki or Jira as a comment on the relevant epic, and update the artifact reference if the `resource_id` FK target is resolved. [J:PROJ-123]
- **Dependencies**: None
- **Key notes**:
  - Clarify whether `payload` has a fixed schema or is fully free-form JSONB; this directly affects `COMP-009` (CoreAction Input Validator). [R:validators/core_action_validator.py]
  - Confirm `version` field increment semantics — is it application-managed or DB trigger-managed? [R:models/core_action.py]
  - Confirm whether the audit write and SSE publish (COMP-016, COMP-014) fall inside or outside the same DB transaction as the core_action_records write (COMP-011). This determines error handling in COMP-008.
  - Confirm the exact `status` lifecycle transitions: `pending → completed`, `pending → failed`, `failed → rolled_back` — are any other transitions valid?
  - All decisions must be written down (wiki page or Jira comment) before T-014, T-018, or T-025 begin.
- **Acceptance criteria**: Unblocks T-014, T-015, T-018, T-025. No REQ directly tested here, but this step is a prerequisite gate for REQ-007, REQ-008, REQ-009.
- **Verify**: Confirm the decision record exists and is linked from the epic. Engineering lead signs off (comment or approval on the decision doc).

---

### T-002: Confirm degradation behaviour and user-facing messaging expectations with product owner (config) —

- **Purpose**: Pin down the exact degradation contract — what the HTTP response body looks like on a 503, what the user-visible message is, whether the session must remain active post-failure, and whether partial state (e.g. lock acquired but DB write failed) must be explicitly reversed before responding. [R:services/degradation_logger.py]
- **File(s)**: No code files. Output: recorded product decision (wiki or Jira comment) covering: (1) 503 response body schema, (2) user-facing message string(s), (3) whether lock must be released on DB failure, (4) which exceptions trigger degradation vs. 500.
- **Dependencies**: None
- **Key notes**:
  - REQ-012 states "log internally, degrade explicitly, keep session active" — confirm what "degrade explicitly" means in the response body (e.g. `{"error": "service_unavailable", "message": "...user-facing string...","retry_after": N}`).
  - Confirm whether the degradation logger (COMP-015) is expected to emit a typed signal that the blueprint (COMP-007) maps to an HTTP status, or whether the service layer (COMP-008) directly returns a 503. This affects the interface contract for T-021 and T-025.
  - Confirm whether REQ-012 degradation applies only to DB timeout or also to SSE publish failure and audit write failure.
  - Decision must be written down before T-021 or T-025 begin.
- **Acceptance criteria**: Unblocks T-021, T-025. Required for REQ-012.
- **Verify**: Confirm the decision record exists and product owner has signed off.

---

### T-003: Establish and record interactive latency baseline on current develop branch (test) —

- **Purpose**: Capture a pre-implementation p50/p95/p99 latency measurement for the current `develop` branch so that T-042 has a concrete baseline to compare against the REQ-011 sub-100 ms acceptance criterion.
- **File(s)**: `docs/perf/baseline-YYYY-MM-DD.md` (new) — record methodology, tool, environment, and results.
- **Dependencies**: None
- **Key notes**:
  - Use a consistent, reproducible load tool (e.g. `locust`, `k6`, or `wrk`). Record the exact command and seed data used.
  - Run against the `develop` branch in an environment as close to production as possible (ideally the staging compose stack with `docker-compose.prod.yml` once available, but any consistent env is acceptable here).
  - Measure the request-to-visible-result round trip for the nearest equivalent interactive action currently in the codebase. If no equivalent exists, measure a representative DB-read endpoint.
  - Record: p50, p95, p99 latencies; concurrency level; number of requests; DB and app server version.
  - The baseline document must be committed to the repository so T-042 can reference it without relying on ephemeral CI artefacts.
- **Acceptance criteria**: Prerequisite for REQ-011 / T-042. Baseline is committed and reviewable.
- **Verify**:
  ```bash
  git log --oneline docs/perf/baseline-*.md   # confirms file is committed
  cat docs/perf/baseline-*.md | grep -E "p50|p95|p99"  # confirms metrics are recorded
  ```

---

### T-004: Configure GitLab protected branch rule: reject all direct pushes to develop (config) COMP-001

- **Purpose**: Enforce REQ-001 at the Git server layer — no commit may land on `develop` except via an approved and merged MR. [R:docs/ops/branch-protection.md]
- **File(s)**: GitLab project settings (UI or GitLab API call — no repository file). Document the exact API call or UI steps in `docs/ops/branch-protection.md` (created in T-005).
- **Dependencies**: None
- **Key notes**:
  - In GitLab: **Settings → Repository → Protected Branches**: set `develop` to **Allowed to push: No one**, **Allowed to merge: Maintainers**, **Allowed to force push: disabled**.
  - If configuring via API, use `PUT /projects/:id/protected_branches` with `push_access_level: 0` (No one) and `merge_access_level: 40` (Maintainers).
  - Ensure the rule applies to all users including Owner-role accounts — verify this in the GitLab UI after applying.
  - This setting is a prerequisite for T-006 (approval rules) and T-041 (E2E test of branch protection enforcement).
- **Acceptance criteria**: REQ-001. Direct push to `develop` is rejected with a pre-receive error for all users.
- **Verify**:
  ```bash
  # From a local clone with push access:
  git checkout develop
  echo "test" >> README.md && git add . && git commit -m "test direct push"
  git push origin develop
  # Expected: remote: GitLab: You are not allowed to push code to protected branches on this project.
  # Exit code must be non-zero.
  ```

---

### T-005: Create branch-protection operational documentation (docs/ops/branch-protection.md) (new) COMP-001

- **Purpose**: Provide a durable, auditable record of the branch protection configuration so future maintainers can reproduce, verify, or modify it without relying on tribal knowledge.
- **File(s)**: `docs/ops/branch-protection.md` (new)
- **Dependencies**: T-004
- **Key notes**:
  - Document must include: (1) the exact GitLab UI path or API call used to configure the rule, (2) the resulting effective settings (push: No one, merge: Maintainers, force push: disabled), (3) how to verify the rule is active, (4) the procedure for emergency hotfix (temporary override process, who can authorise, how to re-apply protection after).
  - Use a structured Markdown format with sections: `## Configuration`, `## Verification`, `## Emergency Override Procedure`.
  - This file is itself protected by the branch rule just configured — it can only be merged via MR, reinforcing the process.
- **Acceptance criteria**: REQ-001 (documentation of enforcement). Ops team can reproduce the configuration from this document alone.
- **Verify**:
  ```bash
  # File exists and has all required sections:
  grep -E "## Configuration|## Verification|## Emergency Override Procedure" docs/ops/branch-protection.md
  # Must return all three lines.
  ```

---

### T-006: Create .gitlab/approval_rules.yml (min 1 Maintainer, self-approval disabled) and CODEOWNERS (config) COMP-002

- **Purpose**: Enforce REQ-002 and REQ-003 — every MR targeting `develop` must have at least one approval from a Maintainer who is not the MR author.
- **File(s)**: `.gitlab/approval_rules.yml` (new), `CODEOWNERS` (new or modify if exists)
- **Dependencies**: T-004
- **Key notes**:
  - `.gitlab/approval_rules.yml`: set `approvals_required: 1`, `approver_type: maintainer`, `prevent_author_approval: true`, `prevent_committer_approval: true` (prevents any committer on the branch from self-approving).
  - `CODEOWNERS`: assign `*` to the Maintainer group so all files require Maintainer review. Use the format `* @group/maintainers` (adjust group path to match your GitLab namespace).
  - In GitLab project settings, ensure **"Prevent approval by merge request author"** and **"Prevent approval by commits' authors"** are both enabled at the project level — `.gitlab/approval_rules.yml` alone is insufficient if project-level overrides exist.
  - If the project uses GitLab Premium/Ultimate, use Approval Rules API (`POST /projects/:id/approval_rules`) to enforce this programmatically and include the API call in `docs/ops/branch-protection.md`.
  - Both files must be committed to `develop` via MR (not direct push) as a self-demonstrating enforcement of T-004.
- **Acceptance criteria**: REQ-002, REQ-003. MRs without Maintainer approval cannot merge; MR author's own approval does not count toward the required count.
- **Verify**:
  ```bash
  # Confirm files exist with expected keys:
  grep "approvals_required" .gitlab/approval_rules.yml
  grep "prevent_author_approval" .gitlab/approval_rules.yml
  grep "maintainers" CODEOWNERS
  ```

---

### T-007: Verify self-approval enforcement via canary merge request in staging project (test) COMP-002

- **Purpose**: Confirm that the approval rules configured in T-006 actually block a Maintainer from approving their own MR before T-041 runs full E2E validation.
- **File(s)**: No production files. Uses a scratch/canary MR in a staging GitLab project or a dedicated test branch.
- **Dependencies**: T-006
- **Key notes**:
  - Create a test MR as a Maintainer user (User A) against the `develop` branch in a staging project with the same approval rules applied.
  - Attempt to approve the MR as User A (the author). GitLab must reject this with "You cannot approve your own merge request."
  - Attempt to merge without approval — GitLab must block with "Approval rules not met."
  - Have a second Maintainer (User B) approve — confirm merge is now possible.
  - Record the result (pass/fail) in a comment on the canary MR and link it from the task.
  - If the staging project does not have GitLab Premium features parity with production, note the gap and test in a production-equivalent environment.
- **Acceptance criteria**: REQ-002, REQ-003. Self-approval is demonstrably blocked.
- **Verify**:
  ```
  # Manual verification checklist:
  # [ ] User A created MR
  # [ ] User A approval attempt → rejected by GitLab
  # [ ] Merge attempt without approval → blocked
  # [ ] User B (Maintainer, non-author) approval → accepted
  # [ ] Merge succeeds after User B approval
  ```

---

### T-008: Audit all 45+ packages and update requirements.txt with exact == version pins (modify) COMP-005

- **Purpose**: Satisfy REQ-004 — every Python dependency must be pinned to an exact `==` version to ensure deterministic builds and eliminate supply-chain drift.
- **File(s)**: `requirements.txt` (modify)
- **Dependencies**: None
- **Key notes**:
  - Run `pip freeze` in a clean virtualenv against the current working environment to capture all transitive dependencies at their current resolved versions.
  - Replace every non-`==` specifier (`>=`, `~=`, `>`, `<=`, `!=`, unpinned) with an exact `==` pin at the currently-installed version.
  - For each package changed, verify the pinned version passes the full test suite (run `pytest` locally) before committing — a specifier change that breaks tests must be resolved before this task is complete.
  - Do not add or remove packages; only change specifier syntax and pin to exact versions.
  - There are 45+ packages to audit — use `pip list --format=freeze` to generate the full set and diff against `requirements.txt` to catch any missing entries.
  - If any package was previously unpinned (no version specifier), add the currently installed version as the pin.
  - Commit the result. The T-009 validator script will enforce this constraint going forward.
- **Acceptance criteria**: REQ-004. `requirements.txt` contains exactly one `==` specifier per package; no `>=`, `~=`, `>`, or bare package names remain.
- **Verify**:
  ```bash
  # No non-== specifiers remain:
  grep -P "^[^#].*(?<!==)[~><!]" requirements.txt
  # Must return no output (zero matches).

  # Count of pinned packages (expect 45+):
  grep -cP "==" requirements.txt
  ```

---

### T-009: Create scripts/validate_pins.py: scan requirements.txt and exit non-zero on any non-== specifier (new) COMP-004

- **Purpose**: Create an automated, CI-executable guard that enforces REQ-004 on every future MR — any requirements change that introduces an imprecise specifier will fail the pipeline.
- **File(s)**: `scripts/validate_pins.py` (new)
- **Dependencies**: T-008
- **Key notes**:
  - The script must accept an optional `--requirements` argument defaulting to `requirements.txt` relative to the project root, so it is usable in CI without path assumptions.
  - Parse each non-comment, non-blank line. A valid line matches `<package_name>==<version>` exactly. Flag any line containing `>=`, `~=`, `>`, `<=`, `!=`, or a bare package name with no specifier at all.
  - Collect **all** offending lines (do not short-circuit on first failure) and print each offending package name and its current specifier to stdout.
  - Exit with code `1` if any offenders are found; exit `0` if all lines are `==`-pinned.
  - Do not use third-party libraries in the script itself — only the Python standard library — so it can run in a minimal CI image without pre-installing dependencies.
  - Example output for a failing run:
    ```
    ERROR: Non-exact pin detected:
      flask>=2.0.0
      requests~=2.28
    Failing: 2 package(s) require exact == pinning.
    ```
- **Acceptance criteria**: REQ-004. Script exits non-zero and names all offenders when any non-`==` specifier is present; exits zero for a fully-pinned manifest.
- **Verify**:
  ```bash
  # Happy path (all == pins):
  python scripts/validate_pins.py --requirements requirements.txt
  # Expected exit code 0.

  # Failure path (inject a bad specifier):
  echo "badpkg>=1.0.0" >> /tmp/test_reqs.txt
  python scripts/validate_pins.py --requirements /tmp/test_reqs.txt
  # Expected: non-zero exit and "badpkg>=1.0.0" named in output.
  echo $?  # Must be 1.
  ```

---

### T-010: Create docker-compose.prod.yml: production compose file with no /app bind-mount (new) COMP-006

- **Purpose**: Satisfy REQ-005 — no host bind-mount may overwrite `/app` in any production container configuration. The production compose file must use only image-baked application code.
- **File(s)**: `docker-compose.prod.yml` (new)
- **Dependencies**: None
- **Key notes**:
  - `docker-compose.prod.yml` must not contain any `volumes:` entry that mounts a host path to `/app` (or any subdirectory of `/app`) in the application service.
  - Any named volumes (e.g. for persistent data like a DB data directory) are acceptable provided they do not overwrite application code paths.
  - The file must be self-contained and usable as `docker compose -f docker-compose.prod.yml up` without requiring `docker-compose.override.yml`.
  - Set `restart: unless-stopped` on the application service for production resilience.
  - Do not expose debug ports (e.g. no `5678` debugpy port) in this file.
  - Environment variables must be sourced from a `.env` file reference or environment injection — no hardcoded secrets.
  - This file is the reference target for the `compose-lint` CI step added in T-012, which will assert the absence of `/app` bind-mounts programmatically.
- **Acceptance criteria**: REQ-005. `docker-compose.prod.yml` contains no host→`/app` bind-mount volume entry.
- **Verify**:
  ```bash
  # No /app bind-mount present:
  grep -E "^\s+-\s+\..*:/app" docker-compose.prod.yml
  # Must return no output.

  # File is valid compose syntax:
  docker compose -f docker-compose.prod.yml config --quiet
  # Must exit 0.
  ```

### T-011: Modify docker-compose.yml and create docker-compose.override.yml: isolate bind-mount to dev override (modify) [COMP-006]

- **Purpose**: Remove the `/app` bind-mount from the base `docker-compose.yml` so production-equivalent runs are safe by default, and relocate the bind-mount exclusively into `docker-compose.override.yml`, which Docker Compose applies automatically in local dev but never in CI or production. [R:docker-compose.yml]
- **File(s)**:
  - `docker-compose.yml` (modify)
  - `docker-compose.override.yml` (create)
- **Dependencies**: T-010 must be complete so that `docker-compose.prod.yml` already defines the bind-mount-free production baseline before the base file is altered.
- **Key notes**:
  - In `docker-compose.yml`, remove every `volumes:` entry that mounts the host path into `/app` inside any service. Retain named volumes (e.g. postgres data volume) untouched.
  - `docker-compose.override.yml` must declare only the delta: a `volumes:` stanza for each app service that re-adds `.:/app` for live-reload during development. Example:
    ```yaml
    services:
      app:
        volumes:
          - .:/app
    ```
  - Add a comment block at the top of `docker-compose.override.yml` stating: *"Dev-only override. Never deploy this file to production."*
  - Confirm `docker-compose.prod.yml` has no bind-mount (already enforced by T-010) [COMP-006]; the three-file system (`docker-compose.yml` + `docker-compose.override.yml` for dev, `docker-compose.yml` + `docker-compose.prod.yml` for prod) must be documented in `docs/ops/branch-protection.md` or an adjacent runbook entry.
  - Run `docker compose config` (base only) and `docker compose -f docker-compose.yml -f docker-compose.prod.yml config` to assert no bind-mount appears before committing.
- **Acceptance criteria**: REQ-005 — No host bind-mount may overwrite `/app` in any production container config.
- **Verify**:
  ```bash
  # Confirm no /app bind-mount in base or prod configs
  docker compose -f docker-compose.yml config | grep -c '/app' && echo "FAIL: bind-mount in base" || echo "OK"
  docker compose -f docker-compose.yml -f docker-compose.prod.yml config | grep -c '/app' && echo "FAIL: bind-mount in prod" || echo "OK"
  # Confirm override wires it back for dev
  docker compose config | grep '/app'   # should appear exactly once per app service
  ```

---

### T-012: Update .gitlab-ci.yml: add regression-tests stage, pin-lint step, and compose-lint step (modify) [COMP-003]

- **Purpose**: Extend the CI pipeline with three new mandatory blocking steps: (1) a `regression-tests` stage that runs all 10 regression pytest files individually, (2) a `pin-lint` step that invokes `scripts/validate_pins.py`, and (3) a `compose-lint` step that validates the production compose file is free of bind-mounts — all blocking MR merge to `develop`. [COMP-003]
- **File(s)**:
  - `.gitlab-ci.yml` (modify)
- **Dependencies**: T-006 (approval rules in place so the pipeline is gated by MR policy), T-009 (`scripts/validate_pins.py` exists), T-010 (`docker-compose.prod.yml` exists), T-011 (compose split complete).
- **Key notes**:
  - Add `regression-tests` to the `stages:` list; position it after `test` (or equivalent existing stage) and before `deploy`.
  - **`pin-lint` job**:
    ```yaml
    pin-lint:
      stage: regression-tests
      script:
        - python scripts/validate_pins.py
      rules:
        - if: '$CI_MERGE_REQUEST_TARGET_BRANCH_NAME == "develop"'
    ```
    Must exit non-zero on any non-`==` specifier and block the pipeline. [COMP-004]
  - **`compose-lint` job**:
    ```yaml
    compose-lint:
      stage: regression-tests
      script:
        - docker compose -f docker-compose.yml -f docker-compose.prod.yml config | python -c "import sys; cfg=sys.stdin.read(); assert '/app' not in cfg, 'bind-mount found in prod config'"
      rules:
        - if: '$CI_MERGE_REQUEST_TARGET_BRANCH_NAME == "develop"'
    ```
    [COMP-006]
  - **`regression-tests` job**: Must invoke pytest such that each of the 10 regression files appears as a distinct test collection item in output. Use `--verbose` or `pytest tests/regression/` with no `--tb=no` suppression. The job must be set `allow_failure: false`. [COMP-003]
  - Ensure all three new jobs are tagged with the correct runner tag used by the project (confirm from existing jobs in `.gitlab-ci.yml`).
  - Do not use `only:` syntax — use `rules:` to align with existing pipeline style.
- **Acceptance criteria**: REQ-004 (pin-lint enforces == pins), REQ-005 (compose-lint enforces no bind-mount), REQ-006 (all 10 regression files run as blocking stage).
- **Verify**: See T-013 (CI dry-run task).

---

### T-013: Verify CI dry-run: confirm all 10 regression files appear individually in pipeline output; confirm pin-lint and compose-lint steps execute (test) [COMP-003]

- **Purpose**: Validate the `.gitlab-ci.yml` changes from T-012 are functionally correct by observing a real pipeline execution: all 10 regression pytest files appear individually in stdout, and both `pin-lint` and `compose-lint` jobs appear as passed stages.
- **File(s)**: No files created. Observational step against the CI pipeline.
- **Dependencies**: T-012 must be merged (or pushed to a feature branch that targets `develop`) to trigger the pipeline.
- **Key notes**:
  - Push the T-012 branch as an MR targeting `develop`. Do not bypass approval rules — this MR is itself a canary for the pipeline.
  - In the GitLab pipeline UI, navigate to the `regression-tests` stage and confirm:
    1. Each of the 10 regression files is listed as a distinct `PASSED` or `FAILED` collection item in the `regression-tests` job log (look for `tests/regression/test_*.py` lines under pytest's collection output).
    2. `pin-lint` job is present and exits `0` (requirements.txt should already be fully pinned per T-008).
    3. `compose-lint` job is present and exits `0`.
  - If any regression file is missing from the collection log, check for `conftest.py` import errors or missing `__init__.py` that silently skip discovery.
  - Record pipeline URL and screenshot in the MR description as audit evidence.
- **Acceptance criteria**: REQ-006 — All 10 regression pytest files execute as a mandatory blocking CI stage.
- **Verify**:
  ```bash
  # Locally reproduce collection to confirm 10 files discovered
  pytest tests/regression/ --collect-only -q 2>&1 | grep "tests/regression/test_" | wc -l
  # Must print 10
  ```

---

### T-014: Create CoreAction ORM data model: models/core_action.py (core_action_records table schema) (new) [COMP-012]

- **Purpose**: Define the SQLAlchemy ORM model for the `core_action_records` table, establishing the authoritative schema for all CoreAction persistence operations. [COMP-012]
- **File(s)**:
  - `models/core_action.py` (create)
- **Dependencies**: T-001 — payload schema and transaction boundaries must be confirmed before column definitions are finalised.
- **Key notes**:
  - Use the project's existing declarative `Base` (import from `models/base.py` or equivalent — confirm path from existing model files in the repo).
  - Column spec (all fields mandatory unless noted):

    | Column | Type | Constraints |
    |--------|------|-------------|
    | `id` | UUID | PK, default `uuid4`, non-nullable |
    | `resource_id` | UUID | non-nullable, indexed |
    | `section_id` | VARCHAR(128) | non-nullable |
    | `actor_user_id` | VARCHAR(128) | non-nullable |
    | `status` | VARCHAR(32) | CHECK IN `('pending','completed','failed','rolled_back')`, non-nullable |
    | `payload` | JSONB | non-nullable |
    | `version` | INT | default `1`, non-nullable |
    | `created_at` | TIMESTAMPTZ | server_default `now()`, non-nullable |
    | `completed_at` | TIMESTAMPTZ | nullable |
    | `failure_reason` | TEXT | nullable |

  - FK: `actor_user_id` → `users` table (confirm FK column name with engineering lead per T-001). FK to target resource table is deferred (Open Item #5) — add a `# TODO: FK to resource table pending Open Item #5` comment on `resource_id`. [COMP-012]
  - Add a `__repr__` for debuggability.
  - Do **not** define the Alembic migration here; that is T-016.
  - Import and register the model in `models/__init__.py` so Alembic's `env.py` auto-discovers it.
- **Acceptance criteria**: REQ-007, REQ-009 — CoreAction records persist with correct schema to support atomic orchestration.
- **Verify**:
  ```bash
  python -c "from models.core_action import CoreActionRecord; print(CoreActionRecord.__table__.columns.keys())"
  # Must list all 10 columns without import error
  ```

---

### T-015: Create CoreAction Audit Log ORM model: models/core_action_audit.py (core_action_audit_entries table schema) (new) [COMP-017]

- **Purpose**: Define the SQLAlchemy ORM model for the `core_action_audit_entries` table, enforcing the append-only audit trail for permission-denial and action-lifecycle events. [COMP-017]
- **File(s)**:
  - `models/core_action_audit.py` (create)
- **Dependencies**: T-001 — event type vocabulary and actor identity fields must be confirmed.
- **Key notes**:
  - Column spec:

    | Column | Type | Constraints |
    |--------|------|-------------|
    | `id` | UUID | PK, default `uuid4`, non-nullable |
    | `core_action_id` | UUID | nullable FK → `core_action_records.id` |
    | `event_type` | VARCHAR(64) | CHECK IN `('permission_denied','lock_denied','action_initiated','action_completed','action_failed','action_rolled_back')`, non-nullable |
    | `actor_user_id` | VARCHAR(128) | non-nullable |
    | `resource_id` | UUID | nullable |
    | `denied_operation` | VARCHAR(128) | nullable |
    | `details` | JSONB | nullable |
    | `recorded_at` | TIMESTAMPTZ | server_default `now()`, non-nullable |

  - **Append-only enforcement**: Do not define `update()` or `delete()` methods on the model. Add a SQLAlchemy event listener using `@event.listens_for(CoreActionAuditEntry, 'before_update')` and `before_delete` that raise `RuntimeError("CoreActionAuditEntry is append-only")` to prevent ORM-level mutation. [COMP-017]
  - `core_action_id` FK is nullable — denial events are written before any `core_action_records` row exists. [COMP-016]
  - Register in `models/__init__.py`.
- **Acceptance criteria**: REQ-010 — Permission denials produce audit entries; REQ-007 — Action lifecycle events are durably recorded.
- **Verify**:
  ```bash
  python -c "
  from models.core_action_audit import CoreActionAuditEntry
  from sqlalchemy import event
  listeners = event.Events._key_to_collection.get(('CoreActionAuditEntry', 'before_update'), [])
  print('append-only guard registered:', len(list(listeners)) > 0)
  print('columns:', CoreActionAuditEntry.__table__.columns.keys())
  "
  ```

---

### T-016: Create Alembic migration for core_action_records table (migration) [COMP-012]

- **Purpose**: Produce the Alembic revision that creates the `core_action_records` table in the database, including all constraints, indexes, and the CHECK constraint on `status`. [COMP-012]
- **File(s)**:
  - `alembic/versions/<revision_id>_create_core_action_records.py` (create via `alembic revision --autogenerate`)
- **Dependencies**: T-014 — ORM model must exist and be importable before `--autogenerate` can detect it.
- **Key notes**:
  - Run `alembic revision --autogenerate -m "create_core_action_records"` from the project root. Review the generated file — **do not commit autogenerate output blindly**; verify:
    1. `op.create_table('core_action_records', ...)` is present.
    2. CHECK constraint `status IN ('pending','completed','failed','rolled_back')` is explicitly present. Autogenerate may not emit CHECK constraints depending on SQLAlchemy version — add manually if absent.
    3. An index on `resource_id` is included (add `op.create_index(...)` manually if autogenerate omits it).
    4. `down_revision` correctly chains to the previous head migration.
  - The `downgrade()` function must call `op.drop_table('core_action_records')`.
  - Do not create the `core_action_audit_entries` table in this migration — that is T-017.
  - Run `alembic upgrade head` against the test database to confirm the migration applies cleanly and is reversible.
- **Acceptance criteria**: REQ-007, REQ-009 — Database table exists with correct schema for CoreAction persistence.
- **Verify**:
  ```bash
  alembic upgrade head
  alembic downgrade -1
  alembic upgrade head   # confirm idempotent round-trip
  psql $TEST_DATABASE_URL -c "\d core_action_records"
  # Confirm all columns and CHECK constraint appear
  ```

---

### T-017: Create Alembic migration for core_action_audit_entries table (migration) [COMP-017]

- **Purpose**: Produce the Alembic revision that creates the `core_action_audit_entries` table, including the nullable FK to `core_action_records.id` and the CHECK constraint on `event_type`. [COMP-017]
- **File(s)**:
  - `alembic/versions/<revision_id>_create_core_action_audit_entries.py` (create via `alembic revision --autogenerate`)
- **Dependencies**: T-015 (ORM model must be importable), T-016 (`core_action_records` table must exist first so the FK can resolve — set `down_revision` to T-016's revision ID).
- **Key notes**:
  - `down_revision` must point to the T-016 migration, making this migration a direct dependent in the chain.
  - Verify the generated file includes:
    1. `op.create_table('core_action_audit_entries', ...)`.
    2. `FOREIGN KEY (core_action_id) REFERENCES core_action_records(id)` with `ondelete='SET NULL'` (nullable FK — denial events must not be blocked by missing action rows).
    3. CHECK constraint `event_type IN ('permission_denied','lock_denied','action_initiated','action_completed','action_failed','action_rolled_back')` — add manually if autogenerate omits it.
    4. Index on `core_action_id` and `actor_user_id` for audit query performance.
  - `downgrade()` must `op.drop_table('core_action_audit_entries')` (before `core_action_records` is touched in T-016's downgrade — order is already enforced by the revision chain).
  - Do **not** add an `UPDATE` or `DELETE` trigger in this migration — append-only enforcement is handled at the ORM layer (T-015).
- **Acceptance criteria**: REQ-010 — Audit table exists and correctly references `core_action_records` with nullable FK to support denial-event recording.
- **Verify**:
  ```bash
  alembic upgrade head
  alembic downgrade base
  alembic upgrade head
  psql $TEST_DATABASE_URL -c "\d core_action_audit_entries"
  # Confirm FK, CHECK constraint, and indexes appear
  ```

---

### T-018: Create CoreAction Input Validator: validators/core_action_validator.py (new) [COMP-009]

- **Purpose**: Implement stateless per-field input validation for the `POST /core-action` request payload, returning a structured `{field: message}` error map so the blueprint can emit precise 422 responses. [COMP-009]
- **File(s)**:
  - `validators/core_action_validator.py` (create)
- **Dependencies**: T-001 — payload schema and per-field rules (type, length, format, nullability) must be confirmed before validation logic is written.
- **Key notes**:
  - Expose a single public function: `validate_core_action_input(data: dict) -> dict[str, str]`. Returns an empty dict on success; returns `{field_name: human_readable_message}` for each failing field. [COMP-009]
  - Rules per field (per Data Models section):
    - `resource_id`: required, non-null, must be a valid UUID v4 string (use `uuid.UUID(val, version=4)`). Error key: `"resource_id"`.
    - `section_id`: required, non-null, string, max length 128. Error key: `"section_id"`.
    - `payload`: required, non-null, must be a dict/object (not a scalar or list). Error key: `"payload"`.
  - Collect **all** field errors before returning — do not short-circuit on the first failure. This ensures clients receive the complete error map in a single request.
  - Do not perform database lookups or permission checks in this validator — those are handled by COMP-010 and COMP-013 respectively.
  - Error messages must be deterministic string literals (not f-strings with dynamic content beyond the field name) to allow exact assertion in T-028. [COMP-009]
  - Keep the module import-free of Flask/SQLAlchemy so it is independently unit-testable.
- **Acceptance criteria**: REQ-008 — All inputs validated before execution; field-specific errors returned per failure.
- **Verify**:
  ```bash
  python -m pytest tests/unit/validators/test_core_action_validator.py -v
  # T-028 must pass; run T-028 immediately after this task to confirm
  ```

---

### T-019: Create Permission Guard Decorator: decorators/permission_guard.py (new) [COMP-010]

- **Purpose**: Implement a reusable Flask decorator that checks whether the authenticated session holds the `CORE_ACTION_EXECUTE` permission and short-circuits with a 403 JSON response before any business logic executes. Unauthenticated requests receive 401. [COMP-010]
- **File(s)**:
  - `decorators/permission_guard.py` (create)
- **Dependencies**: None (pure decorator; no model or migration required). Confirm the project's session/auth mechanism (session object shape, permission constant name `CORE_ACTION_EXECUTE`) from existing permission guards in the codebase before writing.
- **Key notes**:
  - Decorator signature: `@require_permission("CORE_ACTION_EXECUTE")` — parameterised so it can be reused for future permissions.
  - Logic sequence:
    1. If no valid session → return `jsonify({"error": "Unauthorized"})`, HTTP 401.
    2. If session exists but `CORE_ACTION_EXECUTE` not in `session.permissions` (or equivalent) → return `jsonify({"error": "Forbidden"})`, HTTP 403.
    3. Otherwise → call the wrapped function.
  - The decorator must **not** write audit log entries itself — that is COMP-016's responsibility. The service layer (COMP-008) calls the audit log writer after a 403. [COMP-010]
  - Use `functools.wraps(f)` to preserve the wrapped function's `__name__` and `__doc__` (required for Flask route registration to work correctly with multiple decorated routes).
  - The 403 response body must include `{"error": "Forbidden"}` as an exact literal — test T-029 asserts on this. [COMP-010]
  - Do not import SQLAlchemy models or start DB sessions in this file.
- **Acceptance criteria**: REQ-010 — Core action denied to users lacking `CORE_ACTION_EXECUTE`; no partial execution possible.
- **Verify**:
  ```bash
  python -m pytest tests/unit/decorators/test_permission_guard.py -v
  # All three cases: permissioned, unpermissioned, no session
  ```

---

### T-020: Create Section Lock Coordinator: services/section_lock_coordinator.py (new) [COMP-013]

- **Purpose**: Implement an acquire/release abstraction over the existing `SectionLock` model so the CoreAction Service (COMP-008) has a single, tested entry point for concurrency control without embedding locking SQL directly in the orchestration layer. [COMP-013]
- **File(s)**:
  - `services/section_lock_coordinator.py` (create)
- **Dependencies**: T-014 — `CoreActionRecord` model must exist (the coordinator records the winning `core_action_id` on the lock row). Confirm the existing `SectionLock` model's file path and column schema from the repository before writing.
- **Key notes**:
  - Expose two public functions:
    - `acquire_lock(section_id: str, resource_id: UUID, actor_user_id: str, db_session) -> dict | None`
      - Attempts a `SELECT ... FOR UPDATE NOWAIT` (or equivalent optimistic lock) on the `section_locks` table for `(section_id, resource_id)`.
      - Returns `{"lock_id": UUID, "section_id": str, "expires_at": datetime}` on success.
      - Returns `None` if the row is already locked (existing `locked_by` is set and not expired) — the caller (COMP-008) is responsible for issuing the 409 response.
    - `release_lock(lock_id: UUID, actor_user_id: str, db_session) -> bool`
      - Returns `True` if the lock was released by the owning actor.
      - Returns `False` if `lock_id` not found or `actor_user_id` does not match `locked_by` — no exception raised; caller handles the 403/404 branch.
  - All DB operations must use the `db_session` passed in — **do not import a global `db` session** — to ensure the coordinator participates in the caller's transaction boundary. [COMP-013]
  - Lock expiry: read expiry duration from application config (`LOCK_TTL_SECONDS`, default `300`). Do not hard-code.
  - `acquire_lock` must be atomic: use a single `UPDATE ... WHERE locked_by IS NULL OR expires_at < now() RETURNING *` pattern (or equivalent) to avoid TOCTOU races. [REQ-009]
- **Acceptance criteria**: REQ-009 — Simultaneous modification of the same resource causes no data loss or inconsistency.
- **Verify**:
  ```bash
  python -m pytest tests/unit/services/test_section_lock_coordinator.py -v
  # Four cases: acquire unlocked, acquire already-locked, release by owner, release by non-owner
  ```

### T-021: Create Degradation Logger utility (new) COMP-015

- **Purpose**: Provide a reusable, structured mechanism to capture dependency failures (DB timeouts, service errors), emit a machine-readable internal log entry, and return a typed degradation signal that the calling service can branch on — ensuring session continuity during partial failures. [R:services/degradation_logger.py]
- **File(s)**: `services/degradation_logger.py`
- **Dependencies**: None
- **Key notes**:
  - Define a `DegradationSignal` dataclass or named-tuple with fields: `degraded: bool`, `category: str` (e.g. `"db_timeout"`, `"service_unavailable"`), `detail: str`, `original_exception_type: str`.
  - Define a `log_degradation(exc: Exception, context: dict) -> DegradationSignal` function. Use Python's `logging` module at `ERROR` level with a structured payload (JSON-serialisable dict) containing: `timestamp`, `exception_type`, `exception_message`, `context`. Do NOT surface the raw traceback in the return value — internal log only.
  - Map exception categories deterministically: `sqlalchemy.exc.TimeoutError` → `"db_timeout"`, `requests.Timeout` → `"service_unavailable"`, catch-all → `"unknown_error"`.
  - The function must never raise; wrap the logging call itself in a bare `except` to prevent the logger from becoming a secondary failure point.
  - Return value must be importable and type-checkable by `services/core_action_service.py` [R:services/core_action_service.py] without circular imports. [C:COMP-015]
- **Acceptance criteria**: REQ-012 (log internally, degrade explicitly, keep session active).
- **Verify**:
  ```bash
  pytest tests/unit/services/test_degradation_logger.py -v
  ```

---

### T-022: Create Audit Log Writer service (new) COMP-016

- **Purpose**: Provide an append-only writer that persists `permission_denied` and action-lifecycle audit entries to `core_action_audit_entries`, enforcing that no existing row is ever mutated. [R:services/audit_log_writer.py]
- **File(s)**: `services/audit_log_writer.py`
- **Dependencies**: T-015 (`models/core_action_audit.py`), T-016 (migration for `core_action_records`), T-017 (migration for `core_action_audit_entries`)
- **Key notes**:
  - Expose two public functions: `write_permission_denied(actor_user_id, resource_id, denied_operation, details, db_session)` and `write_action_lifecycle(core_action_id, event_type, actor_user_id, resource_id, details, db_session)`.
  - Both functions must only ever call `db_session.add(new_entry)` — never `db_session.query(...).update(...)` or `db_session.merge(...)`. Enforce this with a docstring/comment contract and a runtime guard: if an `id` is supplied externally, raise `ValueError`.
  - `event_type` for lifecycle must be one of the CHECK-constraint values: `'permission_denied'`, `'lock_denied'`, `'action_initiated'`, `'action_completed'`, `'action_failed'`, `'action_rolled_back'`. [C:COMP-017] Validate against this set and raise `ValueError` for unknown values.
  - `core_action_id` is nullable — `permission_denied` entries are written before a `core_action_records` row exists. [C:COMP-017]
  - `recorded_at` must be set server-side to `datetime.utcnow()` — never accept it as a caller argument.
  - Do NOT call `db_session.commit()` inside this service; the caller (CoreAction Service, T-025) owns the transaction boundary. [C:COMP-008]
- **Acceptance criteria**: REQ-010 (audit denial), REQ-007 (audit lifecycle).
- **Verify**:
  ```bash
  pytest tests/unit/services/test_audit_log_writer.py -v
  ```

---

### T-023: Create CoreAction SSE Publisher service (new) COMP-014

- **Purpose**: Write a `HandoverChange`-compatible event record to the DB so that the existing SSE poll/delivery mechanism picks it up and broadcasts a `core_action_change` event to subscribed clients without requiring a direct socket connection from this service. [R:services/sse_publisher.py]
- **File(s)**: `services/sse_publisher.py`
- **Dependencies**: T-014 (`models/core_action.py`)
- **Key notes**:
  - Expose `publish_core_action_event(core_action_id, event_type, resource_id, actor, db_session)`.
  - The record written must be schema-compatible with the existing `HandoverChange` model/table (field names, types) — confirm the exact table name and column mapping with the engineering lead before implementation (this is part of Open Item #5 alignment referenced in the data model). [C:COMP-014]
  - Populate: `core_action_id`, `event_type`, `resource_id`, `actor`, `timestamp` (server-set UTC). The `event_type` field value must be the string `"core_action_change"` for SSE client routing.
  - Do NOT call `db_session.commit()`; the parent transaction in CoreAction Service (T-025) owns commit/rollback. [C:COMP-008]
  - If DB write fails, the function must propagate the exception upward — the degradation handling layer in T-025 will catch and route it. Do not swallow exceptions here.
  - The `GET /core-action/stream` SSE endpoint shape is: `{core_action_id, event_type, resource_id, actor, timestamp}` plus heartbeat events. [C:COMP-007]
- **Acceptance criteria**: REQ-007 (end-to-end action completion visible to client), REQ-009 (consistent broadcast on success).
- **Verify**:
  ```bash
  pytest tests/unit/services/test_sse_publisher.py -v
  ```

---

### T-024: Create CoreAction Repository (new) COMP-011

- **Purpose**: Encapsulate all DB reads and writes for `core_action_records` within a single transaction boundary, providing create, status-update, and rollback operations to the service layer without exposing ORM internals. [R:repositories/core_action_repository.py]
- **File(s)**: `repositories/core_action_repository.py`
- **Dependencies**: T-014 (`models/core_action.py`), T-016 (Alembic migration for `core_action_records`)
- **Key notes**:
  - Expose: `create_record(resource_id, section_id, actor_user_id, payload, db_session) -> CoreActionRecord`, `mark_completed(record_id, db_session) -> CoreActionRecord`, `mark_failed(record_id, failure_reason, db_session) -> CoreActionRecord`, `mark_rolled_back(record_id, db_session) -> CoreActionRecord`.
  - `create_record` sets `status='pending'`, `version=1`, `created_at=utcnow()`. [C:COMP-012]
  - `mark_completed` sets `status='completed'`, `completed_at=utcnow()`. [C:COMP-012]
  - Status transitions must be guarded: `mark_completed` may only be called on a record currently in `'pending'` status; raise `InvalidStateTransitionError` (define locally) otherwise.
  - All mutations use `db_session.add()` / attribute assignment — never raw SQL. Do NOT call `db_session.commit()` or `db_session.rollback()` inside the repository; commit/rollback ownership belongs to CoreAction Service. [C:COMP-008]
  - `resource_id` must be stored as a UUID type, not a string — use `uuid.UUID` conversion on input if the caller passes a string.
  - The `payload` field must accept a plain `dict` and store it as JSONB. [C:COMP-012]
- **Acceptance criteria**: REQ-007, REQ-009 (atomic writes, no data loss).
- **Verify**:
  ```bash
  pytest tests/integration/test_core_action_happy_path.py -v -k "repository"
  ```

---

### T-025: Create CoreAction Service (new) COMP-008

- **Purpose**: Orchestrate the full CoreAction execution pipeline — permission check → lock acquire → DB record create → audit log → SSE publish → commit — as a single atomic unit, with structured degradation handling on any dependency failure. [R:services/core_action_service.py]
- **File(s)**: `services/core_action_service.py`
- **Dependencies**: T-002 (degradation behaviour confirmed), T-018 (validator), T-019 (permission guard), T-020 (lock coordinator), T-021 (degradation logger), T-022 (audit log writer), T-023 (SSE publisher), T-024 (repository)
- **Key notes**:
  - Expose `execute_core_action(resource_id, section_id, payload, actor_user_id, db_session) -> dict`.
  - **Execution order (must be strictly followed)**:
    1. Validate inputs via `CoreActionValidator.validate()` — raise `ValidationError` (422) on failure before any lock or DB work.
    2. Permission is checked at the decorator level (T-019) before this function is called — do not re-check inside.
    3. Acquire section lock via `SectionLockCoordinator.acquire()` — on `LockConflictError`, write a `lock_denied` audit entry (no commit yet) and re-raise as 409.
    4. Call `CoreActionRepository.create_record()` with `status='pending'`.
    5. Write `action_initiated` audit entry via `AuditLogWriter`.
    6. Attempt business logic execution (payload processing — placeholder hook for future expansion).
    7. Call `CoreActionRepository.mark_completed()`.
    8. Write `action_completed` audit entry.
    9. Call `SSEPublisher.publish_core_action_event()`.
    10. Call `db_session.commit()` — **this is the only commit call in the entire pipeline**.
    11. Return serialised success dict matching the 200 response shape. [C:COMP-007]
  - **Degradation path**: Wrap steps 4–9 in a `try/except`. On any `SQLAlchemyError` or timeout: call `db_session.rollback()`, call `DegradationLogger.log_degradation()`, return a typed `DegradationSignal` that the blueprint (T-026) maps to HTTP 503. [C:COMP-015] Session must remain active (do not invalidate the user session). [C:REQ-012]
  - **Rollback path**: On non-DB exceptions post-record-creation: call `mark_rolled_back()`, write `action_rolled_back` audit entry, commit audit only, raise for blueprint to map to 500.
  - All inter-service calls receive the same `db_session` instance — no new sessions opened within this service.
  - Sub-100 ms interactive latency is a hard acceptance criterion [C:REQ-011]; avoid any synchronous external HTTP calls inside this method.
- **Acceptance criteria**: REQ-007, REQ-009, REQ-010, REQ-011, REQ-012.
- **Verify**:
  ```bash
  pytest tests/integration/test_core_action_happy_path.py tests/integration/test_core_action_degradation.py tests/integration/test_core_action_concurrency.py -v
  ```

---

### T-026: Create CoreAction Blueprint (new) COMP-007

- **Purpose**: Define all HTTP routes for the CoreAction feature, handle request intake and session extraction, map service-layer outcomes to correct HTTP status codes and standardised error bodies, and register the SSE stream endpoint. [R:routes/core_action.py]
- **File(s)**: `routes/core_action.py`
- **Dependencies**: T-025 (`services/core_action_service.py`)
- **Key notes**:
  - Create a Flask `Blueprint` named `core_action_bp` with `url_prefix='/core-action'`. [C:COMP-007]
  - Implement all four endpoints from the API spec: [C:COMP-007]
    - `POST /core-action` → calls `execute_core_action`; applies `@permission_guard` decorator.
    - `POST /core-action/<resource_id>/lock` → calls `SectionLockCoordinator.acquire()` directly; applies `@permission_guard`.
    - `DELETE /core-action/<resource_id>/lock/<lock_id>` → calls `SectionLockCoordinator.release()`; applies `@permission_guard`.
    - `GET /core-action/stream` → session-authenticated SSE stream; returns `text/event-stream` with `core_action_change` and `heartbeat` events.
  - HTTP status mapping (must be exact): `ValidationError` → 422, `LockConflictError` → 409 with `{locked_by}` in body, `DegradationSignal.degraded=True` → 503, unauthenticated → 401, `@permission_guard` denial → 403, not found → 404, unhandled → 500. [C:COMP-007]
  - 422 error body must include field-keyed error map: `{"errors": {"field_name": "message"}}`. [C:REQ-008]
  - 409 body must include `locked_by` field. [C:COMP-007]
  - All responses must be JSON (`flask.jsonify`) except the SSE stream endpoint.
  - Extract `actor_user_id` from the session object — never from the request body.
  - Obtain a `db_session` via the application's session factory (use the existing pattern in the codebase — do not create ad-hoc sessions).
  - Do NOT put business logic in the blueprint; all orchestration lives in COMP-008. [C:COMP-008]
- **Acceptance criteria**: REQ-007, REQ-008, REQ-010, REQ-011.
- **Verify**:
  ```bash
  pytest tests/integration/test_core_action_auth.py tests/integration/test_core_action_validation.py tests/integration/test_core_action_happy_path.py -v
  ```

---

### T-027: Register core_action_bp blueprint in app.py (modify) COMP-007

- **Purpose**: Wire the `core_action_bp` Flask blueprint into the application factory so that all CoreAction routes are reachable at runtime and in the test client. [R:app.py]
- **File(s)**: `app.py`
- **Dependencies**: T-026 (`routes/core_action.py`)
- **Key notes**:
  - Import `core_action_bp` from `routes.core_action` and call `app.register_blueprint(core_action_bp)` inside the application factory function, following the same pattern used for existing blueprint registrations in `app.py`. [R:app.py]
  - Registration must occur after all extensions (SQLAlchemy, session middleware, etc.) are initialised on the `app` instance — do not register before `db.init_app(app)` or equivalent.
  - Confirm no URL prefix collision with existing blueprints by running `flask routes | grep core-action` after registration.
  - Do not modify any other blueprint registration, middleware, or config — this is a minimal, surgical change.
- **Acceptance criteria**: REQ-007 (routes reachable end-to-end).
- **Verify**:
  ```bash
  flask routes | grep "core-action"
  pytest tests/integration/test_core_action_auth.py -v -k "test_no_session_returns_401"
  ```

---

### T-028: Unit tests — CoreAction Input Validator (test) COMP-009

- **Purpose**: Achieve 100% branch coverage on `validators/core_action_validator.py`, asserting exact error message strings for every validation rule so that regressions in error copy are caught immediately. [R:tests/unit/validators/test_core_action_validator.py]
- **File(s)**: `tests/unit/validators/test_core_action_validator.py`
- **Dependencies**: T-018 (`validators/core_action_validator.py`)
- **Key notes**:
  - Test cases must cover every branch in the validator, grouped by field:
    - `resource_id`: missing → error; non-UUID format → error; valid UUID string → passes.
    - `section_id`: missing → error; empty string → error; >128 characters → error; exactly 128 characters → passes; valid short string → passes. [C:COMP-009]
    - `payload`: missing → error; non-object (string, list, int) → error; empty dict `{}` → passes; populated dict → passes.
    - All three fields valid simultaneously → no errors returned (empty map).
  - Assert the **exact error message string** for each failure case — do not use `assertIn` with partial strings; use `assertEqual`. This prevents silent copy drift.
  - Assert the error map **key** is exactly the field name (e.g., `"resource_id"`, `"section_id"`, `"payload"`). [C:COMP-009]
  - Assert that the return type on failure is a `dict` (not a list, not an exception).
  - Assert that a fully valid input returns either an empty dict `{}` or `None` — document which in a comment.
  - Do not import Flask app or DB — this is a pure-unit test with no fixtures beyond the validator class itself.
  - Enforce coverage gate: add `# pragma: no branch` only where genuinely unreachable; all real branches must be exercised.
- **Acceptance criteria**: REQ-008 (field-specific errors validated at unit level).
- **Verify**:
  ```bash
  pytest tests/unit/validators/test_core_action_validator.py -v --cov=validators/core_action_validator --cov-report=term-missing --cov-fail-under=100
  ```

---

### T-029: Unit tests — Permission Guard Decorator (test) COMP-010

- **Purpose**: Verify that `decorators/permission_guard.py` correctly short-circuits to 403 before any business logic executes when permission is absent, and allows pass-through when `CORE_ACTION_EXECUTE` is present. [R:tests/unit/decorators/test_permission_guard.py]
- **File(s)**: `tests/unit/decorators/test_permission_guard.py`
- **Dependencies**: T-019 (`decorators/permission_guard.py`)
- **Key notes**:
  - Three test cases (minimum):
    1. **Permissioned session**: mock session contains `CORE_ACTION_EXECUTE` → wrapped function is called exactly once; return value is the wrapped function's return value; HTTP status is not 403.
    2. **Unpermissioned session**: mock session present but lacks `CORE_ACTION_EXECUTE` → wrapped function is **never called** (use `unittest.mock.Mock` and assert `call_count == 0`); response status is 403. [C:COMP-010]
    3. **No session**: session object absent or empty → wrapped function is **never called**; response status is 401.
  - Use Flask's test request context (`app.test_request_context`) to provide a realistic `flask.session` mock without starting the full app.
  - Assert that the 403 response body contains a recognisable error field (e.g. `{"error": "forbidden"}` or equivalent) — pin the exact key/value so API contract regressions are caught.
  - Assert that **no side effects** (DB writes, lock acquisition) occur on the 403/401 path — verify by ensuring the mock for the inner function has `call_count == 0`.
  - Do not test audit log writing here — that is covered in T-032. This test is purely decorator behaviour.
- **Acceptance criteria**: REQ-010 (permission denial; no partial execution).
- **Verify**:
  ```bash
  pytest tests/unit/decorators/test_permission_guard.py -v --cov=decorators/permission_guard --cov-report=term-missing
  ```

---

### T-030: Unit tests — Section Lock Coordinator (test) COMP-013

- **Purpose**: Verify all four behavioural branches of `services/section_lock_coordinator.py`: acquiring an unlocked resource, attempting to acquire an already-locked resource, releasing a lock by its owner, and rejecting a release attempt by a non-owner. [R:tests/unit/services/test_section_lock_coordinator.py]
- **File(s)**: `tests/unit/services/test_section_lock_coordinator.py`
- **Dependencies**: T-020 (`services/section_lock_coordinator.py`)
- **Key notes**:
  - Four test cases (minimum):
    1. **Acquire unlocked**: mock `SectionLock` query returns `None` → `acquire()` creates and returns a new lock object with correct `resource_id`, `section_id`, `actor_user_id`, and `expires_at` fields.
    2. **Acquire locked**: mock `SectionLock` query returns an existing active lock → `acquire()` raises `LockConflictError` (or equivalent); assert the exception carries the `locked_by` identity of the existing lock holder. [C:COMP-013]
    3. **Release by owner**: mock lock exists and `actor_user_id` matches `lock.actor_user_id` → `release()` deletes/deactivates the lock and returns a confirmation; assert `db_session.delete` or equivalent is called.
    4. **Release by non-owner**: mock lock exists but `actor_user_id` does not match → `release()` raises a `PermissionError` or domain-specific equivalent; assert the lock record is **not** deleted (`db_session.delete` is not called).
  - Use `unittest.mock.MagicMock` for `db_session` and the `SectionLock` model to keep the test fully in-memory. [C:COMP-013]
  - Do not call `db_session.commit()` assertions here — the coordinator does not own commits (per T-025 design). Verify this by asserting `db_session.commit.call_count == 0` in all four cases.
  - Assert `expires_at` on the acquired lock is set to a future timestamp (UTC) — use `datetime.utcnow() + timedelta(...)` comparison with a small tolerance.
- **Acceptance criteria**: REQ-009 (concurrent lock safety validated at unit level).
- **Verify**:
  ```bash
  pytest tests/unit/services/test_section_lock_coordinator.py -v --cov=services/section_lock_coordinator --cov-report=term-missing
  ```

### T-031: Unit tests: Degradation Logger (new) [COMP-015]

- **Purpose**: Verify that `services/degradation_logger.py` emits a correctly structured internal log entry for every recognised exception category and returns a well-typed degradation signal that callers can interrogate without catching raw exceptions. [R:services/degradation_logger.py]
- **File(s)**: `tests/unit/services/test_degradation_logger.py`
- **Dependencies**: T-021 (Degradation Logger implementation must exist)
- **Key notes**:
  - Parameterise tests across at minimum three exception categories: network timeout, DB connection error, and a generic unexpected exception — assert that the log record's `category` field is distinct for each.
  - Capture log output using `pytest`'s `caplog` fixture at `logging.ERROR` level; assert the log record contains `exception_type`, `message`, and a non-null `timestamp` field.
  - Assert the returned degradation signal object exposes a boolean `degraded` attribute set to `True` in all failure cases and a string `reason` field that is non-empty. The signal must not re-raise the original exception. [C:COMP-015]
  - Do **not** mock the logger itself — only mock the dependency that raises the exception, to keep the logger's emission path under real test.
  - Test that a `None`/no-exception invocation (non-degraded path) returns `degraded=False` and logs nothing at ERROR level.
- **Acceptance criteria**: REQ-012 (log internally, degrade explicitly, keep session active)
- **Verify**:
  ```bash
  pytest tests/unit/services/test_degradation_logger.py -v --tb=short
  ```

---

### T-032: Unit tests: Audit Log Writer (new) [COMP-016]

- **Purpose**: Verify that `services/audit_log_writer.py` persists audit entries with all required fields for both `permission_denied` and `action_completed` event types, and that the append-only constraint is respected (no update or delete path exists). [R:services/audit_log_writer.py]
- **File(s)**: `tests/unit/services/test_audit_log_writer.py`
- **Dependencies**: T-022 (Audit Log Writer implementation), T-016, T-017 (migrations must have run so the ORM models are consistent)
- **Key notes**:
  - Use an in-process SQLite test DB (or `pytest-mock` to stub the session) — the unit test must not require a live Postgres instance.
  - **`permission_denied` entry assertions**: `event_type == 'permission_denied'` [C:COMP-017], `actor_user_id` non-null, `denied_operation` non-null, `core_action_id` is `None` (denial precedes record creation), `recorded_at` is a non-null timezone-aware datetime.
  - **`action_completed` entry assertions**: `event_type == 'action_completed'` [C:COMP-017], `core_action_id` is a non-null UUID that matches the `CoreActionRecord` under test, `actor_user_id` non-null, `recorded_at` non-null.
  - **Append-only enforcement**: Assert the writer class exposes no `update`, `delete`, or `overwrite` method. Use `assert not hasattr(writer, 'update')` style checks in addition to a test that calls the writer twice and asserts two distinct rows exist with ascending `recorded_at`, neither modifying the other.
  - All six `event_type` CHECK values are enumerated in the model [C:COMP-017]; cover at least `permission_denied` and `action_completed` explicitly and assert that passing an unknown event type raises a `ValueError` before any DB write.
- **Acceptance criteria**: REQ-010 (permission denial recorded), REQ-007 (action lifecycle recorded)
- **Verify**:
  ```bash
  pytest tests/unit/services/test_audit_log_writer.py -v --tb=short
  ```

---

### T-033: Unit tests: Dependency Pin Validator script (new) [COMP-004]

- **Purpose**: Confirm that `scripts/validate_pins.py` correctly identifies non-`==` specifiers, reports all offenders (not just the first), and exits zero only when every line in `requirements.txt` uses exact `==` pinning. [R:scripts/validate_pins.py]
- **File(s)**: `tests/unit/scripts/test_validate_pins.py`
- **Dependencies**: T-009 (validate_pins.py implementation must exist)
- **Key notes**:
  - Drive the script via `subprocess.run` or by importing its `main()` function so the exit code is observable.
  - Write temporary `requirements.txt` files using `tmp_path` fixture for isolation.
  - **Cases to cover**:
    1. All-`==` manifest → exit code 0, no output to stderr.
    2. Single `>=` specifier → exit code non-zero; offending package name appears in stdout/stderr.
    3. Single `~=` specifier → exit code non-zero; offending package name appears.
    4. Single `>` specifier → exit code non-zero; offending package name appears.
    5. Mixed manifest (two non-`==` and several valid `==`) → exit code non-zero; **both** offenders are named in output (tests "reports all offenders" requirement). [C:COMP-004]
    6. Empty file → exit code 0 (no packages, no violations).
    7. Comment lines (`# foo`) and blank lines must not produce false positives.
  - Do not test against the real `requirements.txt` to keep the test hermetic.
- **Acceptance criteria**: REQ-004 (all 45+ packages pinned to exact `==`); CI gate confirmed by T-039.
- **Verify**:
  ```bash
  pytest tests/unit/scripts/test_validate_pins.py -v --tb=short
  ```

---

### T-034: Integration tests: session validation and permission guard (new) [COMP-007]

- **Purpose**: Confirm that the `POST /core-action` endpoint correctly enforces authentication and the `CORE_ACTION_EXECUTE` permission check before any business logic executes, and that a permission denial produces an audit entry. [C:COMP-010]
- **File(s)**: `tests/integration/test_core_action_auth.py`
- **Dependencies**: T-027 (blueprint registered in `app.py`), T-029 (Permission Guard unit tests passing — confirms decorator contract)
- **Key notes**:
  - Stand up the Flask app in test mode with a real test Postgres DB (use `pytest` fixture with transaction rollback teardown).
  - **Case 1 — no session cookie**: `POST /core-action` with no auth cookie → assert HTTP 401; assert response body contains an `error` key; assert **no** `CoreActionAuditEntry` row is inserted (unauthenticated calls are not audited — confirm this expectation with T-001 outcome).
  - **Case 2 — authenticated but insufficient role**: supply a valid session for a user without `CORE_ACTION_EXECUTE` → assert HTTP 403 [C:COMP-010]; assert response body `error` field is non-empty.
  - **Case 3 — 403 triggers audit entry**: for the insufficient-role case, assert exactly one `CoreActionAuditEntry` row exists with `event_type='permission_denied'`, `actor_user_id` matching the test user, and `denied_operation` non-null. [C:COMP-017]
  - Ensure business logic is never reached: mock `core_action_service.execute` and assert it is **not** called in the 401 and 403 cases.
  - Use a dedicated low-privilege test user fixture; do not reuse any admin seed account.
- **Acceptance criteria**: REQ-010 (deny without partial execution), REQ-003 (permission audit trail)
- **Verify**:
  ```bash
  pytest tests/integration/test_core_action_auth.py -v --tb=short
  ```

---

### T-035: Integration tests: input validation error responses (new) [COMP-009]

- **Purpose**: Confirm that the `POST /core-action` endpoint returns HTTP 422 with a field-keyed error body for every class of validation failure, and that the field name is always present in the response. [C:COMP-009]
- **File(s)**: `tests/integration/test_core_action_validation.py`
- **Dependencies**: T-027 (blueprint registered), T-028 (validator unit tests passing — confirms field rule contract)
- **Key notes**:
  - Use a permissioned session fixture for all cases (auth must pass so validation is reached).
  - **Cases to cover** (at minimum):
    1. Missing `resource_id` → 422; response body `errors.resource_id` present.
    2. `resource_id` is not a valid UUID (e.g. `"not-a-uuid"`) → 422; `errors.resource_id` describes format violation. [C:COMP-009]
    3. Missing `section_id` → 422; `errors.section_id` present.
    4. `section_id` exceeds 128 characters → 422; `errors.section_id` present. [C:COMP-009]
    5. Missing `payload` → 422; `errors.payload` present.
    6. `payload` is not a JSON object (e.g. a string) → 422; `errors.payload` present.
    7. Multiple simultaneous invalid fields → 422; **all** offending field keys present in `errors` map (not just the first). [C:COMP-009]
  - Assert HTTP status is exactly 422 (not 400) for all validation failures.
  - Assert no `CoreActionRecord` or `CoreActionAuditEntry` rows are written during validation failures.
  - Keep test DB clean between cases using per-test transaction rollback.
- **Acceptance criteria**: REQ-008 (validate all inputs; show field-specific error per failure)
- **Verify**:
  ```bash
  pytest tests/integration/test_core_action_validation.py -v --tb=short
  ```

---

### T-036: Integration tests: CoreAction happy path (new) [COMP-008]

- **Purpose**: Verify the end-to-end successful execution path: authenticated permissioned user submits a valid request; receives HTTP 200 with a fully populated response body; a `core_action_records` row with `status='completed'` is persisted; and a `core_action_audit_entries` row with `event_type='action_completed'` is written. [C:COMP-008]
- **File(s)**: `tests/integration/test_core_action_happy_path.py`
- **Dependencies**: T-027 (blueprint), T-030 (Section Lock Coordinator tests), T-031 (Degradation Logger tests), T-032 (Audit Log Writer tests)
- **Key notes**:
  - Use a permissioned user session fixture; supply a valid UUID `resource_id`, a `section_id` ≤128 chars, and a non-empty `payload` object. [C:COMP-009]
  - **Response body assertions** (HTTP 200): fields `status`, `core_action_id` (valid UUID), `resource_id` (echoes request), `section_id` (echoes request), `completed_at` (ISO 8601 timezone-aware), `actor` (matches session user) are all present and non-null. [C:COMP-007]
  - **DB persistence assertions**:
    - Exactly one `CoreActionRecord` row with `id == core_action_id`, `status='completed'`, `actor_user_id` matching the session user, `payload` matching the request payload, `completed_at` non-null. [C:COMP-012]
    - Exactly one `CoreActionAuditEntry` row with `event_type='action_completed'`, `core_action_id` matching the record, `actor_user_id` matching the session user. [C:COMP-017]
  - Assert the section lock is **released** after completion (no orphaned `SectionLock` row for the test `section_id`). [C:COMP-013]
  - Run the happy path twice with different `resource_id` values in the same test session to confirm no cross-request state leakage.
- **Acceptance criteria**: REQ-007 (authenticated permissioned user can complete end-to-end), REQ-009 (no data loss or inconsistency)
- **Verify**:
  ```bash
  pytest tests/integration/test_core_action_happy_path.py -v --tb=short
  ```

---

### T-037: Integration tests: concurrent lock conflict (new) [COMP-013]

- **Purpose**: Confirm that when two simultaneous requests target the same `resource_id`/`section_id`, the second request receives HTTP 409 with a `locked_by` field, and no `core_action_records` row is inserted for the rejected request. [C:COMP-013]
- **File(s)**: `tests/integration/test_core_action_concurrency.py`
- **Dependencies**: T-027 (blueprint), T-030 (Section Lock Coordinator tests)
- **Key notes**:
  - Simulate concurrency deterministically: acquire the section lock manually via `POST /core-action/<resource_id>/lock` with a first-user session, then immediately attempt `POST /core-action` with a second-user session targeting the same `resource_id` and `section_id`. [C:COMP-007]
  - **Case 1 — 409 response**: assert HTTP 409; assert response body contains `locked_by` field whose value is non-null and corresponds to the first user; assert `error` or `detail` field is non-empty. [C:COMP-007]
  - **Case 2 — no spurious record**: after the 409, query `core_action_records` filtered by `resource_id` — assert zero rows with `actor_user_id` matching the second user. [C:COMP-012]
  - **Case 3 — lock release restores access**: release the lock via `DELETE /core-action/<resource_id>/lock/<lock_id>` as the first user; then retry `POST /core-action` as the second user — assert HTTP 200. [C:COMP-007]
  - Do not use `threading` or `asyncio` to manufacture concurrency in tests; the deterministic acquire-then-attempt pattern is sufficient and avoids test flakiness.
  - Verify the `SectionLock` row is cleaned up after each scenario using teardown assertions.
- **Acceptance criteria**: REQ-009 (simultaneous modification causes no data loss or inconsistency)
- **Verify**:
  ```bash
  pytest tests/integration/test_core_action_concurrency.py -v --tb=short
  ```

---

### T-038: Integration tests: DB failure degradation (new) [COMP-015]

- **Purpose**: Confirm that when the CoreAction Repository [C:COMP-011] raises a DB timeout, the endpoint returns HTTP 503, no `core_action_records` row is persisted, and the degradation logger captures a structured internal log entry. [C:COMP-015]
- **File(s)**: `tests/integration/test_core_action_degradation.py`
- **Dependencies**: T-027 (blueprint), T-031 (Degradation Logger tests)
- **Key notes**:
  - Inject the DB failure via `unittest.mock.patch` on the repository's write method to raise a `sqlalchemy.exc.OperationalError` (simulating a DB timeout). Patch at the repository layer [C:COMP-011], not at the SQLAlchemy engine, to keep the test deterministic.
  - **HTTP response assertions**: status 503; response body contains an `error` or `detail` field; response body does **not** expose raw exception traceback or DB internals (no stack trace leakage).
  - **No-persistence assertion**: query `core_action_records` for the test `resource_id` — assert zero rows. The transaction must have been rolled back. [C:COMP-011]
  - **Internal log assertion**: use `caplog` at `logging.ERROR` to assert one log record was emitted by the degradation logger containing `exception_type` and `message` fields. [C:COMP-015]
  - **Session continuity**: assert the test session cookie remains valid after the 503 by making a subsequent authenticated GET request that returns 200 (satisfies REQ-012 "keep session active"). [C:COMP-015]
  - Cover a second case: simulate a timeout that fires **after** the lock is acquired — assert the lock is also released (no orphaned `SectionLock` row). [C:COMP-013]
- **Acceptance criteria**: REQ-012 (log internally, degrade explicitly, keep session active)
- **Verify**:
  ```bash
  pytest tests/integration/test_core_action_degradation.py -v --tb=short
  ```

---

### T-039: Integration tests: CI pin-lint stage (new) [COMP-004]

- **Purpose**: Confirm that the CI `pin-lint` step in `.gitlab-ci.yml` fails the pipeline and names the offending package when a non-`==` specifier is present in `requirements.txt`. [C:COMP-003]
- **File(s)**: `tests/integration/test_pin_lint_ci.py` (or a dedicated CI test script executed in a throwaway GitLab pipeline)
- **Dependencies**: T-012 (`.gitlab-ci.yml` with `pin-lint` step), T-033 (unit tests for validate_pins.py)
- **Key notes**:
  - The integration test strategy is a **canary pipeline**: create a temporary Git branch, inject a deliberate `>=` violation into a copy of `requirements.txt` (e.g. `requests>=2.28.0`), push to the GitLab staging project, and assert the pipeline job named `pin-lint` exits non-zero. [C:COMP-003]
  - Use the GitLab API (pipeline polling) or `gitlab-runner exec` locally to observe the job outcome; assert the job log output contains the offending package name (`requests` in the example).
  - After asserting failure, push a corrected branch (`requests==2.28.2`) and assert the `pin-lint` job exits zero on that branch.
  - If running locally without GitLab access, the fallback is to execute `scripts/validate_pins.py` directly against a temp file in a subprocess and assert exit code, but the canonical integration form must target the actual CI job. [C:COMP-004]
  - Clean up the canary branch regardless of test outcome (use `try/finally` or a pytest `autouse` fixture).
  - This test is expected to be slow (pipeline round-trip); mark with `@pytest.mark.slow` and exclude from default local test runs via `pytest.ini` `filterwarnings` or a marker flag.
- **Acceptance criteria**: REQ-004 (pinning enforced at CI gate), REQ-006 (blocking CI stage executes on every MR)
- **Verify**:
  ```bash
  pytest tests/integration/test_pin_lint_ci.py -v -m slow --tb=short
  ```

---

### T-040: E2E tests: full CoreAction user journeys (new) [COMP-007]

- **Purpose**: Validate all five critical CoreAction user journeys through the full stack (browser/HTTP client → Flask → DB) without any mocking, confirming the integrated system meets all primary requirements end-to-end. [C:COMP-007]
- **File(s)**: `tests/e2e/test_core_action_e2e.py`
- **Dependencies**: T-034, T-035, T-036, T-037, T-038 (all integration tests must be passing — confirms each subsystem is stable before E2E composition)
- **Key notes**:
  - Target a running instance of the full stack (Docker Compose with `docker-compose.prod.yml` [C:COMP-006]) — no mocks, no stubs, no patching. The DB must be fully migrated (Alembic `heads` applied). [C:COMP-003]
  - **Journey 1 — Happy path**: permissioned user authenticates, submits valid `POST /core-action`, receives 200 with all response fields populated, DB row confirmed `status='completed'`, audit entry confirmed. [C:COMP-008, C:COMP-012, C:COMP-017]
  - **Journey 2 — Permission denial**: user without `CORE_ACTION_EXECUTE` submits `POST /core-action` → 403; no `core_action_records` row; one `core_action_audit_entries` row with `event_type='permission_denied'`. [C:COMP-010, C:COMP-017]
  - **Journey 3 — Empty-field validation**: permissioned user submits `POST /core-action` with `section_id` omitted → 422; `errors.section_id` in response body; no DB rows created. [C:COMP-009]
  - **Journey 4 — Concurrent lock conflict**: first permissioned user acquires lock; second permissioned user attempts same `resource_id`/`section_id` → 409 with `locked_by`; second user's `core_action_records` row absent. [C:COMP-013]
  - **Journey 5 — Mid-operation rollback**: use a test-mode endpoint or DB trigger to force a failure after lock acquire but before `core_action_records` write; assert 503 response, no persisted record, no orphaned lock, structured log entry present. [C:COMP-011, C:COMP-015]
  - Each journey must be fully independent — use unique `resource_id` UUIDs per journey and truncate test-owned rows in teardown.
  - Assert SSE stream (`GET /core-action/stream`) emits a `core_action_change` event with the correct `core_action_id` within 2 seconds of Journey 1 completion. [C:COMP-014]
  - Tag with `@pytest.mark.e2e`; exclude from unit/integration runs via `pytest.ini`.
- **Acceptance criteria**: REQ-007, REQ-008, REQ-009, REQ-010, REQ-012 (all P0/P1 functional requirements covered by live journeys)
- **Verify**:
  ```bash
  docker compose -f docker-compose.prod.yml up -d
  pytest tests/e2e/test_core_action_e2e.py -v -m e2e --tb=short
  docker compose -f docker-compose.prod.yml down
  ```

### T-041: E2E Tests: Branch Protection Enforcement and Self-Approval Blocking (test) COMP-001

- **Purpose**: Provide end-to-end automated verification that (1) direct pushes to `develop` are rejected at the Git server level and (2) an MR author's own approval is never counted toward the required Maintainer quorum — the two GitLab policy controls that protect the merge gate. [R:docs/ops/branch-protection.md] [R:.gitlab/approval_rules.yml]

- **File(s)**:
  - `tests/e2e/test_branch_protection.py` ← create new

- **Dependencies**: T-007 (self-approval canary MR verified in staging project), T-013 (CI dry-run confirming pipeline stages execute correctly)

- **Key notes**:
  - **Authentication**: Tests must authenticate against the GitLab API using a scoped CI/CD variable `GITLAB_E2E_TOKEN` (Maintainer role, `api` scope). Never hard-code credentials. Read the token from `os.environ["GITLAB_E2E_TOKEN"]` and skip the test with `pytest.skip` if absent, so the suite is safe in local runs without credentials.
  - **Project targeting**: Read `GITLAB_PROJECT_ID` (or the staging mirror project ID used in T-007) from the environment. All API calls (`python-gitlab` or raw `requests` to `https://<host>/api/v4/projects/<id>/...`) must target the staging/test project, never production.
  - **Direct-push rejection test** (`test_direct_push_rejected`):
    1. Clone the repo to a `tempfile.TemporaryDirectory`.
    2. Checkout `develop`, write a dummy commit (`echo timestamp > .e2e-probe`), attempt `git push origin develop` using the test token credentials.
    3. Assert the `git push` process exits non-zero.
    4. Assert stderr contains `pre-receive` or `protected branch` text (GitLab's standard rejection message). [C:docs/ops/branch-protection.md]
    5. Call the GitLab Commits API to confirm the probe commit is **not** present on `develop`.
  - **Self-approval blocking test** (`test_self_approval_not_counted`):
    1. Using `GITLAB_E2E_TOKEN` (the author identity), open a new MR from a temporary branch targeting `develop` via `POST /api/v4/projects/<id>/merge_requests`.
    2. Attempt to approve the MR as the same user via `POST /api/v4/projects/<id>/merge_requests/<iid>/approve`.
    3. Retrieve approval state via `GET /api/v4/projects/<id>/merge_requests/<iid>/approvals`.
    4. Assert `approvals_left > 0` (the self-approval was not counted) and `approved == false`. [R:.gitlab/approval_rules.yml]
    5. Clean up: close the MR via `PUT .../merge_requests/<iid>` with `state_event=close` and delete the temporary branch.
  - Both tests must be idempotent — a failed mid-run cleanup must not leave state that breaks subsequent runs. Use `pytest` fixtures with `yield` + teardown to guarantee cleanup.
  - Mark tests with `@pytest.mark.e2e` and `@pytest.mark.gitlab` so they are excluded from the standard unit/integration run and invoked explicitly in CI with `-m "e2e and gitlab"`.
  - Do **not** rely on `time.sleep` polling; use a short retry loop (max 5 × 2 s) when waiting for GitLab async state updates.

- **Acceptance criteria**: REQ-001 (direct pushes to `develop` rejected), REQ-002 (≥1 Maintainer approval required), REQ-003 (approving Maintainer must not be MR author)

- **Verify**:
  ```bash
  # Requires GITLAB_E2E_TOKEN and GITLAB_PROJECT_ID set in environment
  pytest tests/e2e/test_branch_protection.py -v -m "e2e and gitlab" \
    --tb=short 2>&1 | tee tests/e2e/branch_protection_results.txt

  # Both test_direct_push_rejected and test_self_approval_not_counted must show PASSED
  grep -E "PASSED|FAILED|ERROR" tests/e2e/branch_protection_results.txt
  ```

---

### T-042: Performance Validation — Sub-100 ms Interactive Latency vs REQ-011 Baseline (test) COMP-008

- **Purpose**: Formally verify that `POST /core-action` (the primary interactive endpoint of COMP-007/COMP-008) responds within the 100 ms acceptance threshold defined in REQ-011, measured end-to-end from HTTP request dispatch to HTTP response receipt, and confirm there is no statistically significant regression against the baseline captured in T-003. [R:services/core_action_service.py]

- **File(s)**:
  - `tests/performance/test_core_action_latency.py` ← create new
  - `tests/performance/conftest.py` ← create new (shared fixtures: authenticated session, seeded test resource)
  - `tests/performance/baseline.json` ← create new (written by T-003; read here for regression comparison)

- **Dependencies**: T-003 (interactive latency baseline recorded and committed to `tests/performance/baseline.json`), T-040 (full E2E suite passing, confirming the endpoint is functionally correct before performance is asserted)

- **Key notes**:
  - **Tooling**: Use `pytest-benchmark` (or `locust` in headless single-user mode) rather than raw `time.time()` so statistical output (min, mean, p95, p99, stddev) is captured in a machine-readable report. If using `pytest-benchmark`, configure `--benchmark-json=tests/performance/latest_run.json` in `pytest.ini` or via `addopts`.
  - **Test environment**: Tests must run against a locally started application server (e.g., `flask run` or `gunicorn` with 1 worker) seeded with a clean database. Do **not** run against staging/production. Use a `conftest.py` session-scoped fixture that starts the server as a subprocess, waits for `/healthz`, and tears it down on session exit.
  - **Authenticated fixture**: The `conftest.py` must create a test user with `CORE_ACTION_EXECUTE` permission, obtain a session cookie via the login endpoint, and pass that cookie to all timed requests — matching real user conditions from REQ-011. [R:decorators/permission_guard.py]
  - **What to measure** (`test_core_action_post_latency`):
    - Seed a valid `resource_id` (UUID) and `section_id` (≤128 chars) in the test DB before each iteration. [R:models/core_action.py]
    - Send `POST /core-action` with a valid authenticated payload for **N=100 iterations** (configurable via env var `PERF_ITERATIONS`, default 100).
    - Record wall-clock latency per request (from `requests.Session.post()` call start to `.elapsed.total_seconds() * 1000` ms).
    - Assert **p95 ≤ 100 ms** (the REQ-011 threshold). Fail the test if any percentile assertion is violated.
  - **Baseline regression check** (`test_no_latency_regression_vs_baseline`):
    - Load `tests/performance/baseline.json` (written by T-003 against the `develop` branch before this feature was merged).
    - Compare the current run's p95 against `baseline["p95_ms"]`.
    - Fail if current p95 exceeds `baseline["p95_ms"] * 1.15` (15% regression tolerance). This tolerance is a pragmatic allowance for environment variance; tighten if CI environment is stable.
    - Emit a human-readable summary line: `Current p95={X:.1f}ms  Baseline p95={Y:.1f}ms  Delta={Z:+.1f}ms  Status=PASS/FAIL`.
  - **Load conditions**: All measurements are single-user sequential (no concurrency), matching REQ-011's definition of "normal load" for interactive actions. Concurrent-load testing is out of scope for this task.
  - **CI integration**: Add a `performance` stage to `.gitlab-ci.yml` (after the `regression-tests` stage from T-012) that runs this file. Gate the stage as `allow_failure: false` so a p95 breach breaks the pipeline. Persist `latest_run.json` as a GitLab artifact with a 30-day expiry for trend analysis.
  - **Output**: On failure, print the full latency percentile table (min, p50, p95, p99, max) to stdout so engineers can diagnose without re-running locally.

- **Acceptance criteria**: REQ-011 (every interactive action responds within 100 ms under normal load); implicitly validates COMP-008 (CoreAction Service) and COMP-007 (CoreAction Blueprint) meet the latency budget end-to-end.

- **Verify**:
  ```bash
  # Start the app server locally against a test DB before running
  export DATABASE_URL="postgresql://localhost/coreaction_perf_test"
  export PERF_ITERATIONS=100

  pytest tests/performance/test_core_action_latency.py -v \
    --benchmark-json=tests/performance/latest_run.json \
    --tb=short 2>&1 | tee tests/performance/perf_results.txt

  # Both test_core_action_post_latency and test_no_latency_regression_vs_baseline must show PASSED
  grep -E "PASSED|FAILED|ERROR" tests/performance/perf_results.txt

  # Confirm p95 value is within threshold
  python - <<'EOF'
  import json
  data = json.load(open("tests/performance/latest_run.json"))
  baseline = json.load(open("tests/performance/baseline.json"))
  p95 = data["benchmarks"][0]["stats"]["ops"]  # adjust key per benchmark output schema
  print(f"p95={p95:.1f}ms  threshold=100ms  baseline={baseline['p95_ms']:.1f}ms")
  EOF
  ```

## Execution Waves

| Wave | Tasks | Dependencies Satisfied | Verify Command |
|------|-------|----------------------|----------------|
| **0** | T-001, T-002, T-003, T-004, T-008, T-010, T-019, T-021 | None — fully independent | `git log --oneline docs/ops/branch-protection.md; python -m pytest tests/regression/baseline/ -q` |
| **1** | T-005, T-006, T-009, T-011, T-014, T-015, T-018, T-029, T-031 | All W0 complete | `cat .gitlab/approval_rules.yml; python scripts/validate_pins.py; python -c "from models.core_action import CoreActionRecord"` |
| **2** | T-007, T-012, T-016, T-017, T-020, T-023, T-028, T-033 | All W0–W1 complete | `alembic heads; python -m pytest tests/unit/validators/ tests/unit/scripts/ tests/unit/decorators/ -q` |
| **3** | T-013, T-022, T-024, T-030, T-039 | All W0–W2 complete | `python -m pytest tests/unit/services/test_section_lock_coordinator.py tests/unit/services/test_audit_log_writer.py -q; git push origin HEAD:develop` (expect rejection) |
| **4** | T-025, T-032, T-041 | All W0–W3 complete | `python -m pytest tests/unit/services/test_audit_log_writer.py -q; python -c "from services.core_action_service import CoreActionService"` |
| **5** | T-026 | T-025 (W4) | `python -m pytest tests/unit/ -q; python -c "from routes.core_action import core_action_bp"` |
| **6** | T-027 | T-026 (W5) | `python -c "from app import app; rules=[r.rule for r in app.url_map.iter_rules()]; assert any('core-action' in r for r in rules)"` |
| **7** | T-034, T-035, T-036, T-037, T-038 | All W0–W6 complete | `python -m pytest tests/integration/ -q` |
| **8** | T-040 | All W7 complete | `python -m pytest tests/e2e/ -q` |
| **9** | T-042 | T-003 (W0), T-040 (W8) | `python -m pytest tests/performance/ -q --latency-threshold=100` |

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Open Item #5 unresolved** — FK `core_action_records.resource_id` target table is TBD; migration T-016 may require rework if resolved late | High — Alembic migration and model must be rewritten; cascade rules unknown | Medium | Resolve in T-001 before T-014/T-016 begin; explicitly add target table to T-001 scope |
| **Atomic orchestration exceeds 100 ms** — lock acquire + DB write + audit write + SSE publish are 4 sequential DB round-trips; REQ-011 acceptance threshold is tight | High — REQ-011 is P0; failure blocks release | Medium | Capture baseline (T-003) early; instrument each step in COMP-008; add DB indexes at W2; gate on T-042 before ship |
| **Package incompatibility on exact pin** — pinning all 45+ packages to `==` may expose previously masked version conflicts | High — broken environment blocks all dev and CI | Low–Medium | Run full test suite immediately after T-008 in an isolated venv; resolve conflicts before T-012 lands the pin-lint gate |
| **Existing `SectionLock` model coupling** — COMP-013 wraps an existing model with undocumented behaviour; undiscovered edge cases (lock expiry, orphan locks) may surface under concurrency tests | Medium — data inconsistency possible; T-037 may reveal gaps late | Medium | Review SectionLock source before T-020 begins; document acquire/release contracts in T-005 equivalent; T-030/T-037 must cover expiry path |
| **GitLab config drift** — branch protection (COMP-001) and approval rules (COMP-002) live in GitLab UI/API, not in application repo; can be silently changed by any Owner | High — all governance controls can be bypassed | Low | T-041 E2E enforces both controls on every MR; store canonical config in `docs/ops/branch-protection.md` (T-005) and alert on GitLab audit log changes |
| **Audit log append-only not enforced at DB level** — only application-level; a direct DB connection or misconfigured service can DELETE rows | High — audit integrity undermined; compliance risk | Low | Add `RULE` or trigger to block DELETE/UPDATE on `core_action_audit_entries` in T-017 migration; document in T-032 assertions |
| **SSE DB-poll fan-out under load** — `GET /core-action/stream` heartbeats and event polling hit DB on every connected client; no mention of connection limit or debounce | Medium — DB saturation at moderate concurrency | Low–Medium | Confirm HandoverChange polling interval before T-023; add connection count to T-042 load scenario |
| **GitLab tier / version incompatibility** — self-approval blocking (REQ-003) requires GitLab Premium or a specific GitLab version | High — REQ-003 silently unenforced | Low | Verify GitLab tier in T-006 before writing `approval_rules.yml`; T-007 canary MR is the hard gate |
| **Baseline latency already near threshold** — if T-003 measures current develop at ≥ 80 ms, the new atomic service will almost certainly exceed REQ-011 | High — architectural change required post-implementation | Low | Run T-003 at sprint start; if ≥ 80 ms, escalate immediately and consider async write path before T-025 design is finalised |

---

## Non-Functional Hardening

- [x] **API boundary — input validation on all new endpoints:** `POST /core-action`, `POST /core-action/<id>/lock`, `DELETE /core-action/<id>/lock/<lid>` all pass through COMP-009 validator before reaching service layer; 422 with field-keyed error map returned on failure (T-018, T-035)
- [ ] **API boundary — UUID format enforcement:** `resource_id` path params on lock and delete routes must be validated as well as body UUIDs; confirm COMP-009 covers path params or add a separate route-level guard
- [ ] **Service layer — null/empty handling:** COMP-008 must handle `None` returns from COMP-013 (lock not found), COMP-016 (audit write failure in degraded state), and COMP-014 (SSE publish skipped); each must produce a defined typed signal, not an unhandled exception
- [ ] **Data access — indexes:** Add index on `core_action_records(resource_id, status)` and `core_action_audit_entries(core_action_id, recorded_at)` in T-016/T-017 migrations; verify via `EXPLAIN ANALYZE` on integration test DB
- [ ] **Data access — transaction boundary:** Confirm COMP-011 wraps lock-acquire + record-insert in a single transaction; a commit between them creates a window where a record exists without a lock
- [ ] **Error handling — structured error responses:** All error paths (401, 403, 404, 409, 422, 500, 503) return `{error, code, detail}` shape; no raw exception tracebacks leak to clients
- [ ] **Error handling — rollback completeness:** On any exception after lock acquire in COMP-008, the Section Lock must be released before the error response is sent; verify in T-036/T-037
- [ ] **Logging — structured events, no PII:** `degradation_logger` and `audit_log_writer` must not log `payload` field contents (may contain PII); log `core_action_id` and `event_type` only; enforce in T-031/T-032 assertions
- [ ] **Logging — degradation signal contract:** Every exception category in COMP-015 must emit a typed signal consumed by COMP-008; untyped/bare exceptions must not propagate to the HTTP layer
- [ ] **Security — auth check ordering:** COMP-010 permission guard must execute before any DB read or business logic; confirmed by T-029 unit tests and T-034 integration tests
- [ ] **Security — session cookie scope:** `GET /core-action/stream` SSE endpoint requires the same session auth as action endpoints; confirm COMP-010 is applied to the stream route in T-027
- [ ] **Tests — branch coverage:** T-028 requires 100% branch coverage on COMP-009 validator; CI must enforce with `--cov-fail-under=100` scoped to `validators/`
- [ ] **Tests — unit + integration for every new component:** Each of COMP-009 through COMP-017 has a corresponding unit test task; all integration tests target a real test DB (not mocks) for T-034 through T-038

---

## Post-Implementation Checklist

- [ ] All 10 existing regression test files pass on the post-implementation branch (`pytest tests/regression/ -q`)
- [ ] All new unit tests pass with required coverage (`pytest tests/unit/ --cov=. --cov-fail-under=90 -q`)
- [ ] All integration tests pass against a clean test DB with applied migrations (`pytest tests/integration/ -q`)
- [ ] All E2E journeys pass (T-040): happy path, permission denial, empty-field validation, concurrent lock conflict, mid-operation rollback
- [ ] Performance validation passes: p95 latency < 100 ms confirmed against T-003 baseline (T-042)
- [ ] Pin-lint CI gate rejects a deliberately injected `>=` specifier (T-039)
- [ ] Branch protection E2E: direct push to `develop` rejected; self-approval not counted (T-041)
- [ ] No raw exception tracebacks appear in any error response body (manual spot-check of 500/503 paths)
- [ ] No PII appears in application logs under degradation or audit scenarios
- [ ] Alembic `heads` shows exactly one head; no branching migration history
- [ ] `docker-compose.prod.yml` starts without `/app` bind-mount; confirmed by `docker inspect` on running container
- [ ] All NFR hardening checklist items above marked complete
- [ ] Open Item #5 (`resource_id` FK target) documented and either resolved in migration or explicitly deferred with a tracking ticket

---

## Milestones

| Milestone | Completion Criteria | Wave Gate |
|-----------|--------------------|-----------| 
| **M1 — Governance Enforced** | Branch protection active (direct push rejected in live test); approval rules deployed; canary MR confirms self-approval blocked | End of W2 (T-004–T-007 done) |
| **M2 — Dependency & Container Hygiene** | All 45+ pins exact `==`; CI pin-lint and compose-lint stages blocking; prod compose verified no bind-mount | End of W3 (T-008–T-013, T-039 done) |
| **M3 — Data Layer Ready** | Both Alembic migrations applied; ORM models importable; single Alembic head confirmed | End of W2 (T-014–T-017 done) |
| **M4 — Service Components Complete** | All COMP-009 through COMP-016 implemented; all unit tests passing; no component depends on a stub | End of W4 (T-018–T-024, T-028–T-033 done) |
| **M5 — Feature End-to-End Callable** | `POST /core-action` registered in app; returns 200 on valid authenticated request in dev environment | End of W6 (T-025–T-027 done) |
| **M6 — Full Verified** | All integration and E2E tests passing; sub-100 ms latency confirmed; all post-implementation checklist items checked | End of W9 (T-034–T-042 done) |