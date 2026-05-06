"""
Pure-Python scheduling algorithm — no Flask, no SQLAlchemy.

This module contains all math/logic that can be unit-tested without a running
application. roster_scheduler_service.py imports from here and adds DB I/O.
"""
import calendar
from datetime import date

# ---------------------------------------------------------------------------
# Shift code mapping
# ---------------------------------------------------------------------------

DEFAULT_SHIFT_MAP: dict[str, str] = {
    'D':     'D',
    'E':     'E',
    'OCN/E': 'N',
    'WMO':   'OS',
    'WEO':   'OF',
    'VL':    'VL',
    'SL':    'SL',
    'PH':    'HL',
    'COFF':  'CO',
    'OFF':   'OF',
}

PROTECTED_CODES = frozenset({'VL', 'SL', 'HL', 'CO', 'PH'})
LEAVE_CODES = frozenset({'VL', 'SL', 'HL', 'CO'})


# ---------------------------------------------------------------------------
# Date helpers (mirrors JS dim / dow / isWknd / isoWeek)
# ---------------------------------------------------------------------------

def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def is_weekend(d: date) -> bool:
    return d.weekday() >= 5  # Saturday=5, Sunday=6


def iso_week(d: date) -> int:
    return d.isocalendar()[1]


def weeks_in_month(year: int, month: int) -> list[int]:
    """Sorted list of ISO week numbers that contain weekdays in this month."""
    weeks: list[int] = []
    for day in range(1, days_in_month(year, month) + 1):
        d = date(year, month, day)
        if not is_weekend(d):
            wn = iso_week(d)
            if wn not in weeks:
                weeks.append(wn)
    return sorted(weeks)


# ---------------------------------------------------------------------------
# Shift pool builder (mirrors JS numD / numE / numOcn logic)
# ---------------------------------------------------------------------------

def build_shift_pool(reqs: dict, num_supports: int) -> list[str]:
    """
    Build an ordered pool of shift codes sized exactly num_supports.

    reqs keys: 'D', 'E', 'N', 'OS', 'OF'  (already mapped from roster-suite codes)
    Values: int or '*' (wildcard = fill remaining slots).

    Matches the JS logic in computeShufflePlanForMonth lines 3503-3519.
    """
    ns = num_supports
    d_req = reqs.get('D', 0)
    e_req = reqs.get('E', 0)
    n_req = reqs.get('N', 0)

    num_d = 0 if d_req == '*' else min(int(d_req) if d_req else 0, ns)
    num_e = 0 if e_req == '*' else min(int(e_req) if e_req else 0, ns - num_d)
    num_n = 0 if n_req == '*' else min(
        1 if n_req == '*' else (int(n_req) if n_req else 0),
        ns - num_d - num_e
    )

    if d_req == '*':
        num_d = ns - num_e - num_n
    if e_req == '*':
        num_e = ns - num_d - num_n
    if n_req == '*':
        num_n = 1

    num_d = max(0, num_d)
    num_e = max(0, num_e)
    num_n = max(0, num_n)

    if e_req == '*' or not e_req or e_req == 0:
        while num_d + num_e + num_n < ns:
            num_e += 1

    num_d = min(num_d, ns)
    num_e = min(num_e, ns - num_d)
    num_n = min(num_n, ns - num_d - num_e)

    pool = ['D'] * num_d + ['E'] * num_e + ['N'] * num_n
    if e_req == '*' or not e_req or e_req == 0:
        while len(pool) < ns:
            pool.append('E')
    else:
        while len(pool) < ns:
            pool.append('OF')
    return pool[:ns]


def rotation_offset(seed: int, pool_size: int) -> int:
    """Deterministic rotation offset — mirrors JS: (seed % ns) || 1."""
    if pool_size <= 0:
        return 0
    off = seed % pool_size
    return off if off != 0 else 1


def month_seed(year: int, month: int, team_index: int = 0) -> int:
    """Mirrors JS: seed = y*12 + m + (teamIndex * 997)."""
    return year * 12 + month + (team_index * 997)


# ---------------------------------------------------------------------------
# Core schedule computation (pure — no DB)
# ---------------------------------------------------------------------------

def compute_month_plan(
    year: int,
    month: int,
    members: list[dict],  # [{"id": int, "name": str, "scheduling_role": "lead"|"support"}]
    reqs: dict,           # {"D": int|"*", "E": int|"*", "N": int|"*", "OS": int|"*", "OF": int|"*"}
    holidays: set[int],   # set of day-ints that are public holidays
    existing: dict[int, dict[int, str]],  # {member_id: {day: shift_code}} — protected days
    team_index: int = 0,
) -> list[dict]:
    """
    Pure scheduling computation.  No DB reads or writes.

    Returns:
        [{"member_id": int, "name": str, "shift_date": date, "shift_code": str}, ...]
    """
    leads    = [m for m in members if m.get("scheduling_role") == "lead"]
    supports = [m for m in members if m.get("scheduling_role") != "lead"]

    if not supports:
        return []

    ns = len(supports)
    seed = month_seed(year, month, team_index)
    pool = build_shift_pool(reqs, ns)
    week_nums = weeks_in_month(year, month)
    rot_off = rotation_offset(seed, ns)

    # Weekday per-ISO-week assignment
    week_assign: dict[int, dict[int, str]] = {}
    for wi, wn in enumerate(week_nums):
        week_off = (rot_off + wi) % ns
        week_assign[wn] = {supports[pi]["id"]: pool[(pi + week_off) % ns] for pi in range(ns)}

    # Weekend counts
    wmo_req = reqs.get('OS', reqs.get('WMO', 1))
    weo_req = reqs.get('OF', reqs.get('WEO', 1))
    wmo_count = (ns // 2) if wmo_req == '*' else min(int(wmo_req) if wmo_req else 0, ns)
    weo_count = (ns - wmo_count) if weo_req == '*' else min(int(weo_req) if weo_req else 0, ns - wmo_count)
    wmo_count = max(0, wmo_count)
    weo_count = max(0, weo_count)

    wknd_pair_off = seed % max(ns, 1)
    sat_days = [d for d in range(1, days_in_month(year, month) + 1) if date(year, month, d).weekday() == 5]
    sun_days = [d for d in range(1, days_in_month(year, month) + 1) if date(year, month, d).weekday() == 6]

    def _weekend_assign(day: int) -> dict[int, str]:
        dow = date(year, month, day).weekday()
        day_list = sat_days if dow == 5 else sun_days
        wi = day_list.index(day) if day in day_list else 0
        w_off = (wknd_pair_off + wi) % max(ns, 1)
        ordered = [supports[(i + w_off) % ns] for i in range(ns)]
        result: dict[int, str] = {}
        for m in ordered[:wmo_count]:
            result[m["id"]] = 'OS'
        for m in ordered[wmo_count:wmo_count + weo_count]:
            result[m["id"]] = 'OF'
        for m in ordered[wmo_count + weo_count:]:
            result[m["id"]] = 'OF'
        return result

    assignments: list[dict] = []
    total_days = days_in_month(year, month)

    for member in leads + supports:
        mid = member["id"]
        is_lead = member.get("scheduling_role") == "lead"
        for day in range(1, total_days + 1):
            d = date(year, month, day)
            existing_code = existing.get(mid, {}).get(day, '')

            if existing_code in PROTECTED_CODES:
                code = existing_code
            elif day in holidays:
                code = 'HL'
            elif is_weekend(d):
                if is_lead:
                    code = 'OF'
                else:
                    code = _weekend_assign(day).get(mid, 'OF')
            else:
                if is_lead:
                    code = 'E'
                else:
                    wn = iso_week(d)
                    code = week_assign.get(wn, {}).get(mid, 'E')

            assignments.append({
                "member_id": mid,
                "name": member["name"],
                "shift_date": d,
                "shift_code": code,
            })

    return assignments
