"""
Roster auto-scheduler service.

Python port of the JavaScript scheduling engine from roster-suite.
Implements the same deterministic rotation algorithm as computeShufflePlanForMonth
and autoFixCoverageForVL from roster-suite/public/index.html.

Phase 1: standalone service — no Flask routes yet.
Phase 2: routes/roster_scheduler.py Blueprint will call these functions.
"""
import json
import logging
from datetime import date

from models.models import db, TeamMember
from models.roster_scheduler_models import (
    ScheduledShift,
    ShiftCoverageRequirement,
    PublicHoliday,
)
from services.roster_scheduler_algo import (
    DEFAULT_SHIFT_MAP as _DEFAULT_SHIFT_MAP,
    PROTECTED_CODES as _PROTECTED_CODES,
    LEAVE_CODES as _LEAVE_CODES,
    days_in_month as _days_in_month,
    is_weekend as _is_weekend,
    compute_month_plan,
)

logger = logging.getLogger(__name__)


def _get_shift_map(account_id: int) -> dict[str, str]:
    """Return shift code map for account, falling back to defaults."""
    try:
        from models.app_config import AppConfig
        raw = AppConfig.get_value('roster_shift_code_map', account_id=account_id)
        if raw:
            return {**_DEFAULT_SHIFT_MAP, **json.loads(raw)}
    except Exception:
        pass
    return _DEFAULT_SHIFT_MAP


# ---------------------------------------------------------------------------
# Core: generate_month_schedule
# ---------------------------------------------------------------------------

def generate_month_schedule(
    team_id: int,
    account_id: int,
    year: int,
    month: int,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    Generate shift assignments for all active TeamMembers of team_id for year/month.

    Returns:
        {
          "assignments": [{"team_member_id": int, "name": str,
                           "shift_date": str, "shift_code": str}, ...],
          "warnings": [...],
          "dry_run": bool,
        }

    When dry_run=False and overwrite=False: only fills days with no existing assignment.
    When dry_run=False and overwrite=True : overwrites non-protected rows.
    When dry_run=True: nothing is written.
    """
    reqs_raw = ShiftCoverageRequirement.get_team_requirements(team_id)
    if not reqs_raw:
        reqs_raw = ShiftCoverageRequirement.default_requirements()

    holidays = PublicHoliday.get_for_month(account_id, year, month)
    existing_grid = ScheduledShift.get_month_grid(team_id, year, month)

    db_members = (
        TeamMember.query
        .filter_by(team_id=team_id, account_id=account_id, is_active=True)
        .order_by(TeamMember.id)
        .all()
    )
    if not db_members:
        return {"assignments": [], "warnings": ["No active team members found."], "dry_run": dry_run}

    members = [
        {
            "id": m.id,
            "name": m.name,
            "scheduling_role": getattr(m, 'scheduling_role', 'support'),
        }
        for m in db_members
    ]

    plan = compute_month_plan(
        year=year,
        month=month,
        members=members,
        reqs=reqs_raw,
        holidays=holidays,
        existing=existing_grid,
        team_index=0,
    )

    if not plan:
        return {"assignments": [], "warnings": ["No support members to schedule."], "dry_run": dry_run}

    assignments = [
        {
            "team_member_id": a["member_id"],
            "name": a["name"],
            "shift_date": a["shift_date"].isoformat(),
            "shift_code": a["shift_code"],
        }
        for a in plan
    ]

    if not dry_run:
        for a in plan:
            ScheduledShift.upsert(
                team_member_id=a["member_id"],
                team_id=team_id,
                account_id=account_id,
                shift_date=a["shift_date"],
                shift_code=a["shift_code"],
                source='auto',
            )
        db.session.commit()

    return {"assignments": assignments, "warnings": [], "dry_run": dry_run}


def preview_month_schedule(
    team_id: int, account_id: int, year: int, month: int
) -> dict:
    """Dry-run wrapper — returns schedule without writing."""
    return generate_month_schedule(team_id, account_id, year, month, dry_run=True)


# ---------------------------------------------------------------------------
# Coverage auto-fix (mirrors autoFixCoverageForVL)
# ---------------------------------------------------------------------------

def _auto_fix_coverage(
    team_member_id: int,
    day: date,
    team_id: int,
    account_id: int,
) -> list[dict]:
    """
    After a leave code is applied to team_member_id on day, check coverage
    requirements and reassign OFF/unassigned colleagues if a shift falls short.

    Returns list of {name, shift_code, shift_date} for each fix applied.
    """
    reqs_raw = ShiftCoverageRequirement.get_team_requirements(team_id)
    if not reqs_raw:
        reqs_raw = ShiftCoverageRequirement.default_requirements()

    all_members = (
        TeamMember.query
        .filter_by(team_id=team_id, account_id=account_id, is_active=True)
        .order_by(TeamMember.id)
        .all()
    )

    existing: dict[int, str] = {}
    for m in all_members:
        row = ScheduledShift.query.filter_by(
            team_member_id=m.id, shift_date=day
        ).first()
        existing[m.id] = row.shift_code if row else ''

    fixes: list[dict] = []
    is_wknd = _is_weekend(day)

    if is_wknd:
        needed_shift = 'OS' if day.weekday() == 5 else 'OF'
        req = reqs_raw.get(needed_shift, 1)
        if req == '*' or req == 0:
            return fixes
        req = int(req)
        current_count = sum(
            1 for m in all_members
            if m.id != team_member_id and existing.get(m.id) == needed_shift
        )
        if current_count < req:
            shortage = req - current_count
            candidates = [
                m for m in all_members
                if m.id != team_member_id and (not existing.get(m.id) or existing.get(m.id) == 'OF')
            ]
            if len(candidates) < shortage:
                opposite = 'OF' if needed_shift == 'OS' else 'OS'
                for m in all_members:
                    if m.id == team_member_id:
                        continue
                    if any(c.id == m.id for c in candidates):
                        continue
                    if existing.get(m.id) == opposite:
                        candidates.append(m)
            for m in candidates[:shortage]:
                ScheduledShift.upsert(
                    team_member_id=m.id, team_id=team_id, account_id=account_id,
                    shift_date=day, shift_code=needed_shift, source='auto'
                )
                fixes.append({"name": m.name, "shift_code": needed_shift,
                               "shift_date": day.isoformat()})
    else:
        fixed_ids: set[int] = set()
        for shift_key in ('D', 'E'):
            req = reqs_raw.get(shift_key, 0)
            if req == '*' or not req or req == 0:
                continue
            req = int(req)
            current_count = sum(
                1 for m in all_members
                if m.id != team_member_id
                and (existing.get(m.id) == shift_key
                     or (shift_key == 'E' and existing.get(m.id) == 'N'))
            )
            if current_count < req:
                shortage = req - current_count
                candidates = [
                    m for m in all_members
                    if m.id != team_member_id
                    and m.id not in fixed_ids
                    and (not existing.get(m.id) or existing.get(m.id) == 'OF')
                ]
                for m in candidates[:shortage]:
                    ScheduledShift.upsert(
                        team_member_id=m.id, team_id=team_id, account_id=account_id,
                        shift_date=day, shift_code=shift_key, source='auto'
                    )
                    fixed_ids.add(m.id)
                    fixes.append({"name": m.name, "shift_code": shift_key,
                                  "shift_date": day.isoformat()})

    db.session.commit()
    return fixes


# ---------------------------------------------------------------------------
# Leave application
# ---------------------------------------------------------------------------

def apply_leave(
    team_member_id: int,
    dates: list[date],
    leave_code: str,
    account_id: int,
    team_id: int,
    auto_fix: bool = True,
) -> dict:
    """
    Mark leave_code on the given dates (protected=True) and optionally
    trigger _auto_fix_coverage for each affected day.

    leave_code must be one of: VL, SL, HL, CO
    Returns: {"applied": [...], "coverage_fixes": [...]}
    """
    if leave_code not in _LEAVE_CODES:
        raise ValueError(f"leave_code must be one of {sorted(_LEAVE_CODES)}, got {leave_code!r}")

    applied: list[dict] = []
    coverage_fixes: list[dict] = []

    for d in dates:
        ScheduledShift.upsert(
            team_member_id=team_member_id,
            team_id=team_id,
            account_id=account_id,
            shift_date=d,
            shift_code=leave_code,
            source='manual',
        )
        applied.append({"shift_date": d.isoformat(), "shift_code": leave_code})

        if auto_fix:
            fixes = _auto_fix_coverage(team_member_id, d, team_id, account_id)
            coverage_fixes.extend(fixes)

    db.session.commit()
    return {"applied": applied, "coverage_fixes": coverage_fixes}


# ---------------------------------------------------------------------------
# Read: shift view
# ---------------------------------------------------------------------------

def get_shift_view(
    team_id: int,
    account_id: int,
    year: int,
    month: int,
) -> list[dict]:
    """
    Return the full roster grid for the month.

    [
      {
        "team_member_id": int,
        "name": str,
        "scheduling_role": str,
        "shifts": {"2026-05-01": "D", "2026-05-02": "E", ...}
      }
    ]
    """
    members = (
        TeamMember.query
        .filter_by(team_id=team_id, account_id=account_id, is_active=True)
        .order_by(TeamMember.id)
        .all()
    )
    grid = ScheduledShift.get_month_grid(team_id, year, month)
    total_days = _days_in_month(year, month)

    result = []
    for m in members:
        member_shifts = {}
        for day in range(1, total_days + 1):
            d = date(year, month, day)
            code = grid.get(m.id, {}).get(day, '')
            if code:
                member_shifts[d.isoformat()] = code
        result.append({
            "team_member_id": m.id,
            "name": m.name,
            "scheduling_role": getattr(m, 'scheduling_role', 'support'),
            "shifts": member_shifts,
        })
    return result
