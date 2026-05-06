# Roster Scheduler — Python Port Design & Implementation Plan

**Branch:** `feature/roster-scheduler-python-port`  
**Scope:** Port the roster-suite JavaScript scheduling algorithm to Python as a self-contained
service module. Integration into the Flask app follows as a separate phase.

---

## 1. What We Are Porting

The roster-suite SPA (`roster-suite/public/index.html`) contains a browser-based scheduling
engine with these key functions:

| JS Function | Purpose |
|---|---|
| `computeShufflePlanForMonth(y, m)` | Core: produce a full month of shift assignments per person, per team |
| `computeShufflePlan(applyCount)` | Interactive (incremental) version with manual-advance counter |
| `autoFixCoverageForVL(pid, day, y, m)` | Repair coverage gaps when a VL/SL is applied |
| `applyLeave()` | Mark leave codes, then call autoFixCoverage |
| `applyLeavePlanner()` | Bulk-import leave from a planner CSV/JSON |

The **primary target** is `computeShufflePlanForMonth` + `autoFixCoverageForVL`. These two
cover 90% of the business value. `applyLeavePlanner` is a secondary target (Phase 2).

---

## 2. Algorithm Deep-Dive

### 2.1 Data Model (JS → Python equivalents)

| JS Concept | Python Equivalent |
|---|---|
| `people[]` — array of `{id, name, team, role}` | `TeamMember` rows (role extended with `scheduling_role` field) |
| `shifts[pid][yk][day]` — nested dict of shift codes | `ScheduledShift` DB model (one row per person-day) |
| `reqs[team][shiftCode]` = int or `'*'` | `ShiftCoverageRequirement` DB model |
| `holidays[]` — `{date, name}` | `PublicHoliday` DB model |
| `teams[]` | `Team` model (already exists) |

### 2.2 Shift Code Mapping

Roster-suite uses: `D`, `E`, `OCN/E`, `WMO`, `WEO`, `VL`, `SL`, `PH`, `COFF`, `OFF`  
Shifthandover uses: `D`, `E`, `N`, `LE`, `G`, `HL`, `CO`, `OS`, `OF`, `VL`, `SL`

Proposed mapping (configurable per account via `AppConfig`):

| Roster-suite Code | Shifthandover Code | Notes |
|---|---|---|
| `D` | `D` | Day shift — identical |
| `E` | `E` | Evening shift — identical |
| `OCN/E` | `N` or `LE` | Oncall/Evening → Night or Late Evening |
| `WMO` | `OS` | Weekend Morning On-call → On-site weekend |
| `WEO` | `OF` | Weekend Evening On-call → Off-site weekend |
| `VL` | `VL` | Vacation Leave — identical |
| `SL` | `SL` | Sick Leave — identical |
| `PH` | `HL` | Public Holiday → Holiday Leave |
| `COFF` | `CO` | Comp-off — identical |
| `OFF` | `OF` | Off — identical |

The mapping is stored in `AppConfig` key `roster_shift_code_map` as JSON so it can be
adjusted per account without a code change.

### 2.3 Core Algorithm (`computeShufflePlanForMonth`)

```
FOR EACH team:
  1. Split members into leads (role='lead') and supports (role='support')
  2. Build a shift pool from coverage requirements:
       numD  = reqs['D']   (or 0 if '*' — resolved last)
       numE  = reqs['E']   (or 0 if '*' — resolved last)
       numN  = reqs['OCN/E'] (or 0 if '*' → clamped to 1)
       pad with 'E' until pool size == len(supports)
  3. Deterministic seed: seed = y*12 + m + (team_index * 997)
  4. rotOff = seed % len(supports)  (min 1)
  5. FOR EACH ISO week in month:
       weekOff = (rotOff + week_index) % len(supports)
       EACH support[i] gets shiftPool[(i + weekOff) % len(supports)]
  6. Leads always get 'E' on weekdays, 'OFF' on weekends
  7. Weekend split:
       wkndPairOff = seed % max(len(supports), 1)
       FOR EACH weekend day:
         orderedSupports = rotate(supports, wkndPairOff + day_index)
         first wmoCount → WMO
         next  weoCount → WEO
         rest           → OFF
  8. Protected days (VL/SL/PH/COFF) are never overwritten
```

### 2.4 Seeded Random (for "random" mode)

The JS `seededRandInt` is only used in the interactive `computeShufflePlan(applyCount)` when
mode is `'random'`. For the automatic monthly generation (`computeShufflePlanForMonth`), the
seed is purely deterministic: `y*12 + m + (team_index * 997)`.

Python equivalent of seeded rotation:
```python
def _rotation_offset(seed: int, pool_size: int) -> int:
    return max(1, seed % pool_size) if pool_size > 0 else 0
```

For the optional random-mode (manual rotation), use Python's `random.Random(seed).randint(0, pool_size-1)`.

### 2.5 `autoFixCoverageForVL`

```
When a VL/SL is applied to person P on day D:
  IF day is a weekend:
    neededShift = 'WMO' if Saturday else 'WEO'
    count current people already on neededShift (excluding P)
    if count < requirement:
      pick candidates with OFF or unassigned on D
      fallback: swap opposite-weekend-shift people
      assign first N candidates to neededShift
  ELSE (weekday):
    check D shift count; if below req, fill from OFF/unassigned
    check E shift count; if below req, fill from OFF/unassigned
```

---

## 3. New DB Models

### 3.1 `ShiftCoverageRequirement`

```python
# models/roster_scheduler_models.py
class ShiftCoverageRequirement(db.Model):
    __tablename__ = 'shift_coverage_requirements'

    id            = db.Column(db.Integer, primary_key=True)
    team_id       = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    account_id    = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    shift_code    = db.Column(db.String(10), nullable=False)  # 'D','E','N','OS','OF'
    required_count = db.Column(db.String(4), nullable=False, default='1')
    # '0'..'N' or '*' (wildcard = fill remaining)
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('team_id', 'shift_code', name='uq_team_shift_req'),
    )
```

### 3.2 `PublicHoliday`

```python
class PublicHoliday(db.Model):
    __tablename__ = 'public_holidays'

    id         = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    date       = db.Column(db.Date, nullable=False)
    name       = db.Column(db.String(128), nullable=False)
    is_active  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('account_id', 'date', name='uq_account_holiday'),
    )
```

### 3.3 `ScheduledShift`

```python
class ScheduledShift(db.Model):
    __tablename__ = 'scheduled_shifts'

    id            = db.Column(db.Integer, primary_key=True)
    team_member_id = db.Column(db.Integer, db.ForeignKey('team_member.id'), nullable=False)
    team_id       = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    account_id    = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    shift_date    = db.Column(db.Date, nullable=False)
    shift_code    = db.Column(db.String(10), nullable=False)  # D, E, N, OS, OF, VL, SL, HL, CO
    is_protected  = db.Column(db.Boolean, default=False)  # VL/SL/HL/CO — never auto-overwritten
    source        = db.Column(db.String(16), default='auto')  # 'auto', 'manual', 'import'
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('team_member_id', 'shift_date', name='uq_member_shift_date'),
        db.Index('idx_scheduled_shift_team_date', 'team_id', 'shift_date'),
    )
```

### 3.4 `TeamMember.scheduling_role` (migration addendum)

Add one column to the existing `TeamMember` model:

```python
scheduling_role = db.Column(db.String(16), default='support')  # 'lead' or 'support'
```

This is separate from the existing `role` field (which holds job titles). The scheduling
role controls algorithm behaviour: leads always get `E` on weekdays and `OFF` on weekends.

---

## 4. New Service Module

**File:** `services/roster_scheduler_service.py`

### 4.1 Public API

```python
def generate_month_schedule(
    team_id: int,
    account_id: int,
    year: int,
    month: int,           # 1-based
    overwrite: bool = False,
) -> dict:
    """
    Returns:
        {
          "assignments": [{"team_member_id": int, "shift_date": str, "shift_code": str}, ...],
          "warnings": ["Coverage not met for D on 2026-05-12", ...],
          "dry_run": False
        }
    Persists ScheduledShift rows when overwrite=True or no rows exist.
    """

def preview_month_schedule(
    team_id: int,
    account_id: int,
    year: int,
    month: int,
) -> dict:
    """Dry-run: same shape as generate_month_schedule but nothing is written."""

def apply_leave(
    team_member_id: int,
    dates: list[date],
    leave_code: str,      # 'VL', 'SL', 'HL', 'CO'
    account_id: int,
    team_id: int,
    auto_fix: bool = True,
) -> dict:
    """
    Marks leave on the given dates (protected=True) and optionally
    calls _auto_fix_coverage for each affected day.
    Returns: {"applied": [...], "coverage_fixes": [...]}
    """

def get_shift_view(
    team_id: int,
    account_id: int,
    year: int,
    month: int,
) -> list[dict]:
    """
    Returns the full roster grid for the month.
    [{"team_member_id": int, "name": str, "role": str,
      "shifts": {"2026-05-01": "D", "2026-05-02": "E", ...}}]
    """
```

### 4.2 Internal Helpers

```python
def _days_in_month(year: int, month: int) -> int
def _is_weekend(d: date) -> bool
def _iso_week(d: date) -> int
def _build_shift_pool(reqs: dict, num_supports: int) -> list[str]
def _rotation_offset(seed: int, pool_size: int) -> int
def _auto_fix_coverage(
    team_member_id: int, day: date, team_id: int, account_id: int,
    session: db.Session
) -> list[dict]
def _map_shift_code(code: str, account_id: int) -> str
    """Applies roster_shift_code_map from AppConfig."""
```

### 4.3 Shift Code Resolution

```python
_DEFAULT_SHIFT_MAP = {
    'D': 'D', 'E': 'E', 'OCN/E': 'N',
    'WMO': 'OS', 'WEO': 'OF',
    'VL': 'VL', 'SL': 'SL', 'PH': 'HL',
    'COFF': 'CO', 'OFF': 'OF',
}
```

Override per-account via `AppConfig.get_value('roster_shift_code_map', account_id)`.

---

## 5. New Flask Routes (Phase 2)

To be added on a separate integration branch after the service is validated standalone.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/roster/schedule?team_id=&year=&month=` | Get current month schedule |
| `POST` | `/api/roster/generate` | Generate + persist schedule `{team_id, year, month, overwrite}` |
| `POST` | `/api/roster/preview` | Dry-run — returns schedule without writing |
| `POST` | `/api/roster/leave` | Apply leave + auto-fix `{member_id, dates[], code}` |
| `GET/POST` | `/api/roster/coverage-requirements` | CRUD for `ShiftCoverageRequirement` |
| `GET/POST` | `/api/roster/holidays` | CRUD for `PublicHoliday` |
| `GET` | `/roster/auto-scheduler` | Admin page: configure + trigger generation |

All routes live in a new Blueprint `roster_scheduler_bp` under `routes/roster_scheduler.py`
with `url_prefix='/roster'`.

---

## 6. File Plan

```
services/
  roster_scheduler_service.py       ← Core algorithm (this phase)

models/
  roster_scheduler_models.py        ← 3 new models + TeamMember.scheduling_role

migrations/
  versions/<hash>_add_roster_scheduler_tables.py   ← Flask-Migrate auto-generated

tests/
  unit/
    test_roster_scheduler_service.py   ← Pure-Python unit tests (no running app)
  regression/
    test_roster_scheduler.py           ← HTTP regression tests (Phase 2)

routes/
  roster_scheduler.py               ← Blueprint (Phase 2)

templates/
  roster_scheduler/
    index.html                      ← Admin UI (Phase 2)
```

---

## 7. Implementation Phases

### Phase 1 — Algorithm Port (this branch, current work)

| Step | Task | Status |
|---|---|---|
| 1 | Create `models/roster_scheduler_models.py` with 3 new models | todo |
| 2 | Create migration for new tables + `scheduling_role` column | todo |
| 3 | Implement `services/roster_scheduler_service.py` core functions | todo |
| 4 | Write unit tests — `computeShufflePlanForMonth` equivalence | todo |
| 5 | Write unit tests — `autoFixCoverageForVL` equivalence | todo |
| 6 | Cross-validate output against JS engine for same seed/month | todo |

### Phase 2 — Flask Integration (separate branch, after Phase 1 MR)

| Step | Task |
|---|---|
| 7 | Create `routes/roster_scheduler.py` Blueprint |
| 8 | Register Blueprint in `app.py` |
| 9 | Build admin UI template |
| 10 | Write regression tests |
| 11 | MR to master |

---

## 8. Unit Test Strategy

### 8.1 Algorithm Equivalence

For a known seed, month, and team configuration, the Python output must exactly match
what the JS engine produces. We capture 3 reference outputs from the JS engine (via
browser console) for months 2026-04, 2026-05, 2026-06 and freeze them as golden fixtures.

```python
# tests/unit/test_roster_scheduler_service.py

GOLDEN_2026_05 = {
    # team_member_id → {date_str: shift_code}
    # captured from JS engine with seed y=2026, m=5, team_index=0
    ...
}

def test_generate_matches_golden_may_2026(db_session, seed_team_members, seed_coverage_reqs):
    result = generate_month_schedule(team_id=1, account_id=1, year=2026, month=5, overwrite=False)
    for assignment in result["assignments"]:
        expected = GOLDEN_2026_05.get(assignment["team_member_id"], {})
        assert assignment["shift_code"] == expected.get(assignment["shift_date"])
```

### 8.2 Coverage Invariants

```python
def test_weekdays_never_have_weekend_codes(generated_schedule):
    for a in generated_schedule["assignments"]:
        d = date.fromisoformat(a["shift_date"])
        if d.weekday() < 5:  # Monday–Friday
            assert a["shift_code"] not in ('OS', 'OF', 'WMO', 'WEO')

def test_weekends_never_have_weekday_codes(generated_schedule):
    for a in generated_schedule["assignments"]:
        d = date.fromisoformat(a["shift_date"])
        if d.weekday() >= 5:  # Saturday–Sunday
            assert a["shift_code"] not in ('D', 'E', 'N', 'LE')

def test_protected_days_not_overwritten(db_session, member_with_vl):
    result = generate_month_schedule(..., overwrite=True)
    vl_assignment = next(a for a in result["assignments"]
                         if a["team_member_id"] == member_with_vl.id
                         and a["shift_date"] == "2026-05-15")
    assert vl_assignment["shift_code"] == "VL"
```

### 8.3 Auto-Fix Tests

```python
def test_auto_fix_adds_wmo_when_coverage_short(db_session, team_with_3_supports):
    # After applying VL to the only WMO-assigned member on a Saturday:
    result = apply_leave(team_member_id=support_a.id, dates=[date(2026, 5, 3)],
                         leave_code='VL', auto_fix=True, ...)
    assert any(f["shift_code"] == "OS" for f in result["coverage_fixes"])
```

---

## 9. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| JS seed arithmetic doesn't match Python integer semantics | Low | JS uses `%` with same integers; Python `%` matches for positive values |
| ISO week boundary differs between JS `Date` and Python `isocalendar()` | Medium | Unit test cross-validates week numbers for all days in 6 months |
| `scheduling_role` migration conflicts with existing `role` column | Low | Added as a new nullable column with default; no data changed |
| `ShiftCoverageRequirement` has no data yet — schedules default to all-E | Low | Seed data migration provides sensible defaults (`D:1, E:*, N:1`) |
| `ScheduledShift` conflicts with existing `RosterAssignment` model | Low | Two models serve different purposes; `ScheduledShift` is code-based scheduler output, `RosterAssignment` is time-based assignment |

---

## 10. Shift Code Reconciliation Decision

The following shift codes are **new** additions to shifthandover (from roster-suite):

| Code | Meaning | Shifthandover Column(s) Affected |
|---|---|---|
| `WMO` / `OS` | Weekend Morning On-call | `ScheduledShift.shift_code` only |
| `WEO` / `OF` | Weekend Evening On-call | `ScheduledShift.shift_code` only |

These codes are already defined in `shift_swap_leave.py` (`OS`, `OF`) so no new enum is
needed. The `HandoverSummary.shift_code` field (String(8)) can hold them without schema change.

---

## 11. Open Questions (to confirm before Phase 2)

1. Should `generate_month_schedule` be triggerable by `account_admin` only, or also by `team_admin`?
2. Should the scheduler overwrite manual entries made via the existing roster-upload CSV flow, or leave them protected?
3. Do we need an undo stack (JS has one) — or is the DB audit log sufficient for rollback?
4. Leave planner import format — CSV columns from roster-suite or a new shifthandover format?
