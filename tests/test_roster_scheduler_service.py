"""
Unit tests for services/roster_scheduler_algo.py

Tests the pure-Python scheduling algorithm WITHOUT a running app or database.
All DB-touching functions live in roster_scheduler_service.py; this file only
tests the self-contained algo module.

Run:
    pytest tests/test_roster_scheduler_service.py -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import date
import pytest

from services.roster_scheduler_algo import (
    days_in_month,
    is_weekend,
    iso_week,
    weeks_in_month,
    build_shift_pool,
    rotation_offset,
    month_seed,
    compute_month_plan,
    DEFAULT_SHIFT_MAP,
    PROTECTED_CODES,
    LEAVE_CODES,
)


# ---------------------------------------------------------------------------
# days_in_month
# ---------------------------------------------------------------------------

class TestDaysInMonth:
    def test_may_2026(self):
        assert days_in_month(2026, 5) == 31

    def test_february_leap(self):
        assert days_in_month(2024, 2) == 29

    def test_february_non_leap(self):
        assert days_in_month(2025, 2) == 28

    def test_april(self):
        assert days_in_month(2026, 4) == 30


# ---------------------------------------------------------------------------
# is_weekend
# ---------------------------------------------------------------------------

class TestIsWeekend:
    def test_saturday(self):
        assert is_weekend(date(2026, 5, 2)) is True

    def test_sunday(self):
        assert is_weekend(date(2026, 5, 3)) is True

    def test_monday(self):
        assert is_weekend(date(2026, 5, 4)) is False

    def test_friday(self):
        assert is_weekend(date(2026, 5, 1)) is False


# ---------------------------------------------------------------------------
# iso_week
# ---------------------------------------------------------------------------

class TestIsoWeek:
    def test_known_week(self):
        assert iso_week(date(2026, 5, 4)) == 19  # Monday of ISO week 19

    def test_consistency_across_week(self):
        assert iso_week(date(2026, 5, 4)) == iso_week(date(2026, 5, 8))

    def test_cross_month_boundary(self):
        assert iso_week(date(2026, 5, 1)) == iso_week(date(2026, 4, 30))


# ---------------------------------------------------------------------------
# weeks_in_month
# ---------------------------------------------------------------------------

class TestWeeksInMonth:
    def test_sorted_and_unique(self):
        weeks = weeks_in_month(2026, 5)
        assert weeks == sorted(set(weeks))
        assert len(weeks) > 0

    def test_matches_weekday_weeks(self):
        weeks = weeks_in_month(2026, 5)
        days = days_in_month(2026, 5)
        weekday_weeks = set()
        for d in range(1, days + 1):
            dt = date(2026, 5, d)
            if not is_weekend(dt):
                weekday_weeks.add(iso_week(dt))
        assert set(weeks) == weekday_weeks


# ---------------------------------------------------------------------------
# build_shift_pool
# ---------------------------------------------------------------------------

class TestBuildShiftPool:
    def test_pool_length_equals_num_supports(self):
        for ns in range(2, 8):
            pool = build_shift_pool({'D': 1, 'E': '*', 'N': 1}, ns)
            assert len(pool) == ns

    def test_all_E_when_only_e_wildcard(self):
        assert build_shift_pool({'E': '*'}, 4) == ['E', 'E', 'E', 'E']

    def test_d_slot_count_respected(self):
        pool = build_shift_pool({'D': 2, 'E': '*', 'N': 0}, 5)
        assert pool.count('D') == 2
        assert len(pool) == 5

    def test_n_slot_added_when_specified(self):
        pool = build_shift_pool({'D': 1, 'E': '*', 'N': 1}, 4)
        assert 'N' in pool
        assert pool.count('N') == 1

    def test_wildcard_d_fills_remaining(self):
        pool = build_shift_pool({'D': '*', 'E': 1, 'N': 1}, 5)
        assert pool.count('E') == 1
        assert pool.count('N') == 1
        assert pool.count('D') == 3

    def test_valid_codes_only(self):
        valid = {'D', 'E', 'N', 'OF'}
        pool = build_shift_pool({'D': 1, 'E': '*', 'N': 1}, 6)
        for code in pool:
            assert code in valid


# ---------------------------------------------------------------------------
# rotation_offset
# ---------------------------------------------------------------------------

class TestRotationOffset:
    def test_never_zero_for_nonzero_pool(self):
        seed = month_seed(2026, 5)
        assert rotation_offset(seed, 3) != 0

    def test_deterministic(self):
        assert rotation_offset(12345, 4) == rotation_offset(12345, 4)

    def test_within_bounds(self):
        # For pool_size >= 2: offset must be in [0, pool_size)
        # For pool_size == 1: JS returns (0 % 1) || 1 = 1, which is intentionally > 0
        #   — the caller's modulo brings it back to 0, so this is safe in practice.
        for pool_size in range(2, 10):
            off = rotation_offset(99999, pool_size)
            assert 0 <= off < pool_size

    def test_zero_pool_returns_zero(self):
        assert rotation_offset(999, 0) == 0


# ---------------------------------------------------------------------------
# month_seed
# ---------------------------------------------------------------------------

class TestMonthSeed:
    def test_different_months(self):
        assert month_seed(2026, 5) != month_seed(2026, 6)

    def test_different_team_indices(self):
        assert month_seed(2026, 5, 0) != month_seed(2026, 5, 1)

    def test_deterministic(self):
        assert month_seed(2026, 5, 2) == month_seed(2026, 5, 2)


# ---------------------------------------------------------------------------
# DEFAULT_SHIFT_MAP
# ---------------------------------------------------------------------------

class TestShiftCodeMap:
    def test_has_all_roster_suite_codes(self):
        required = {'D', 'E', 'OCN/E', 'WMO', 'WEO', 'VL', 'SL', 'PH', 'COFF', 'OFF'}
        assert required.issubset(DEFAULT_SHIFT_MAP.keys())

    def test_wmo_maps_to_os(self):
        assert DEFAULT_SHIFT_MAP['WMO'] == 'OS'

    def test_weo_maps_to_of(self):
        assert DEFAULT_SHIFT_MAP['WEO'] == 'OF'

    def test_ocne_maps_to_n(self):
        assert DEFAULT_SHIFT_MAP['OCN/E'] == 'N'

    def test_ph_maps_to_hl(self):
        assert DEFAULT_SHIFT_MAP['PH'] == 'HL'


# ---------------------------------------------------------------------------
# compute_month_plan — invariants
# ---------------------------------------------------------------------------

SAMPLE_MEMBERS = [
    {"id": 1, "name": "Alice",   "scheduling_role": "support"},
    {"id": 2, "name": "Bob",     "scheduling_role": "support"},
    {"id": 3, "name": "Carol",   "scheduling_role": "support"},
    {"id": 4, "name": "Dan",     "scheduling_role": "lead"},
]

SAMPLE_REQS = {'D': 1, 'E': '*', 'N': 1, 'OS': 1, 'OF': 1}


@pytest.fixture(scope="module")
def may_2026_plan():
    return compute_month_plan(
        year=2026, month=5,
        members=SAMPLE_MEMBERS,
        reqs=SAMPLE_REQS,
        holidays=set(),
        existing={},
    )


class TestComputeMonthPlan:
    def test_returns_list(self, may_2026_plan):
        assert isinstance(may_2026_plan, list)
        assert len(may_2026_plan) > 0

    def test_all_31_days_covered_per_member(self, may_2026_plan):
        for member in SAMPLE_MEMBERS:
            member_days = [a for a in may_2026_plan if a["member_id"] == member["id"]]
            assert len(member_days) == 31, f"{member['name']} should have 31 assignments"

    def test_weekdays_never_have_weekend_codes(self, may_2026_plan):
        weekend_only = {'OS', 'OF'}
        for a in may_2026_plan:
            if not is_weekend(a["shift_date"]):
                assert a["shift_code"] not in weekend_only, (
                    f"{a['shift_date']} is a weekday but got {a['shift_code']}"
                )

    def test_weekends_never_have_weekday_codes(self, may_2026_plan):
        weekday_only = {'D', 'E', 'N'}
        for a in may_2026_plan:
            if is_weekend(a["shift_date"]):
                assert a["shift_code"] not in weekday_only, (
                    f"{a['shift_date']} is a weekend but got {a['shift_code']}"
                )

    def test_leads_get_e_on_weekdays(self, may_2026_plan):
        lead_id = 4  # Dan
        for a in may_2026_plan:
            if a["member_id"] == lead_id and not is_weekend(a["shift_date"]):
                assert a["shift_code"] == 'E', (
                    f"Lead should get E on weekdays, got {a['shift_code']} on {a['shift_date']}"
                )

    def test_leads_get_off_on_weekends(self, may_2026_plan):
        lead_id = 4
        for a in may_2026_plan:
            if a["member_id"] == lead_id and is_weekend(a["shift_date"]):
                assert a["shift_code"] == 'OF', (
                    f"Lead should get OF on weekends, got {a['shift_code']} on {a['shift_date']}"
                )

    def test_public_holidays_become_hl(self):
        plan = compute_month_plan(
            year=2026, month=5,
            members=[{"id": 1, "name": "Alice", "scheduling_role": "support"}],
            reqs={'E': '*'},
            holidays={15},  # May 15 is a holiday
            existing={},
        )
        may_15 = next(a for a in plan if a["shift_date"] == date(2026, 5, 15))
        assert may_15["shift_code"] == 'HL'

    def test_protected_leave_not_overwritten(self):
        plan = compute_month_plan(
            year=2026, month=5,
            members=[{"id": 1, "name": "Alice", "scheduling_role": "support"}],
            reqs={'E': '*'},
            holidays=set(),
            existing={1: {12: 'VL'}},  # May 12: pre-existing VL
        )
        may_12 = next(a for a in plan if a["shift_date"] == date(2026, 5, 12))
        assert may_12["shift_code"] == 'VL'

    def test_deterministic_across_calls(self):
        plan_a = compute_month_plan(2026, 5, SAMPLE_MEMBERS, SAMPLE_REQS, set(), {})
        plan_b = compute_month_plan(2026, 5, SAMPLE_MEMBERS, SAMPLE_REQS, set(), {})
        codes_a = [(a["member_id"], a["shift_date"], a["shift_code"]) for a in plan_a]
        codes_b = [(a["member_id"], a["shift_date"], a["shift_code"]) for a in plan_b]
        assert codes_a == codes_b

    def test_different_months_produce_different_schedules(self):
        plan_may = compute_month_plan(2026, 5, SAMPLE_MEMBERS, SAMPLE_REQS, set(), {})
        plan_jun = compute_month_plan(2026, 6, SAMPLE_MEMBERS, SAMPLE_REQS, set(), {})
        # Pull first weekday of each month and compare support assignments
        def first_weekday_codes(plan):
            return {a["member_id"]: a["shift_code"]
                    for a in plan if not is_weekend(a["shift_date"]) and a["shift_date"].day == 4}
        assert first_weekday_codes(plan_may) != first_weekday_codes(plan_jun)
