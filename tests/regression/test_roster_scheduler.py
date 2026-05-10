"""
Regression tests — Roster Scheduler (Phase 2)

Covers:
  - Page views: /roster-scheduler, /admin/roster-scheduler
  - API: coverage requirements CRUD
  - API: public holidays CRUD
  - API: team member scheduling roles
  - API: preview schedule (dry-run)
  - API: generate schedule (write)
  - Access control: non-admin cannot call admin endpoints

Requires a running app with the roster_scheduler tables migrated.
"""
import pytest
from datetime import date, timedelta

from tests.config import TestConfig

YEAR  = date.today().year
MONTH = date.today().month


class TestRosterSchedulerPages:
    """Page load smoke tests."""

    def test_roster_scheduler_page_loads(self, admin_session):
        resp = admin_session.get('/roster-scheduler')
        assert resp.status_code == 200, f'Page returned {resp.status_code}'

    def test_roster_scheduler_page_has_expected_content(self, admin_session):
        page = admin_session.get('/roster-scheduler').text
        assert 'roster' in page.lower() or 'schedule' in page.lower()

    def test_admin_settings_page_loads(self, admin_session):
        resp = admin_session.get('/admin/roster-scheduler')
        assert resp.status_code == 200

    def test_admin_settings_has_settings_content(self, admin_session):
        page = admin_session.get('/admin/roster-scheduler').text
        assert 'coverage' in page.lower() or 'holiday' in page.lower()

    def test_regular_user_can_view_roster_page(self, user_session):
        resp = user_session.get('/roster-scheduler')
        assert resp.status_code in (200, 302)

    def test_regular_user_redirected_from_admin_page(self, user_session):
        resp = user_session.session.get(
            f'{user_session.base_url}/admin/roster-scheduler',
            allow_redirects=True,
            timeout=TestConfig.REQUEST_TIMEOUT,
        )
        # Should redirect away or show 403 — NOT a 200 with admin settings content.
        # Check for admin-specific headings (not just 'coverage' which is also a regular view tab).
        is_denied = resp.status_code in (403, 404)
        admin_url_reached = '/admin/roster-scheduler' in resp.url
        admin_settings_visible = (
            ('coverage requirements' in resp.text.lower() or 'public holidays' in resp.text.lower())
            and admin_url_reached
            and resp.status_code == 200
        )
        assert is_denied or not admin_settings_visible, (
            'Regular user should not see admin scheduler settings'
        )


class TestCoverageRequirementsAPI:
    """Coverage requirements CRUD."""

    @pytest.fixture(scope='class')
    def req_id(self, admin_session):
        resp = admin_session.post('/api/roster/coverage-requirements', json={
            'team_id': TestConfig.TEST_TEAM_ID,
            'shift_code': 'D',
            'required_count': '2',
        })
        assert resp.status_code in (200, 201), f'Create req returned {resp.status_code}: {resp.text[:200]}'
        data = resp.json()
        assert data.get('success'), f'API returned error: {data}'
        rid = data.get('id')
        assert rid, f'No id in response: {data}'
        yield rid
        # cleanup
        admin_session.delete(f'/api/roster/coverage-requirements/{rid}')

    def test_list_coverage_requirements(self, admin_session):
        resp = admin_session.get(
            f'/api/roster/coverage-requirements?team_id={TestConfig.TEST_TEAM_ID}'
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get('success')
        assert isinstance(data.get('data'), list)

    def test_create_coverage_requirement(self, req_id):
        assert req_id is not None

    def test_delete_coverage_requirement(self, admin_session, req_id):
        resp = admin_session.delete(f'/api/roster/coverage-requirements/{req_id}')
        assert resp.status_code in (200, 204)
        data = resp.json()
        assert data.get('success')

    def test_non_admin_cannot_create_requirement(self, user_session):
        resp = user_session.post('/api/roster/coverage-requirements', json={
            'team_id': TestConfig.TEST_TEAM_ID,
            'shift_code': 'E',
            'required_count': '1',
        })
        assert resp.status_code in (403, 401), (
            f'Non-admin should be blocked, got {resp.status_code}'
        )


class TestPublicHolidaysAPI:
    """Public holidays CRUD."""

    # Use a far-future date to avoid collisions with existing data
    HOLIDAY_DATE = (date.today() + timedelta(days=300)).isoformat()
    HOLIDAY_NAME = 'Regression Test Holiday'

    @pytest.fixture(scope='class')
    def holiday_id(self, admin_session):
        resp = admin_session.post('/api/roster/holidays', json={
            'date': self.HOLIDAY_DATE,
            'name': self.HOLIDAY_NAME,
        })
        assert resp.status_code in (200, 201), f'Create holiday returned {resp.status_code}: {resp.text[:200]}'
        data = resp.json()
        assert data.get('success'), f'API returned error: {data}'
        hid = data.get('id')
        assert hid, f'No id in response: {data}'
        yield hid
        admin_session.delete(f'/api/roster/holidays/{hid}')

    def test_list_holidays(self, admin_session):
        resp = admin_session.get(f'/api/roster/holidays?year={YEAR}')
        assert resp.status_code == 200
        data = resp.json()
        assert data.get('success')
        assert isinstance(data.get('data'), list)

    def test_create_holiday(self, holiday_id):
        assert holiday_id is not None

    def test_holiday_appears_in_list(self, admin_session, holiday_id):
        future_year = (date.today() + timedelta(days=300)).year
        resp = admin_session.get(f'/api/roster/holidays?year={future_year}')
        assert resp.status_code == 200
        ids = [h['id'] for h in resp.json().get('data', [])]
        assert holiday_id in ids, 'Created holiday not found in list'

    def test_delete_holiday(self, admin_session, holiday_id):
        resp = admin_session.delete(f'/api/roster/holidays/{holiday_id}')
        assert resp.status_code in (200, 204)
        assert resp.json().get('success')

    def test_non_admin_cannot_create_holiday(self, user_session):
        resp = user_session.post('/api/roster/holidays', json={
            'date': (date.today() + timedelta(days=400)).isoformat(),
            'name': 'Blocked Holiday',
        })
        assert resp.status_code in (403, 401)


class TestMembersAPI:
    """Team member scheduling roles."""

    def test_list_members(self, admin_session):
        resp = admin_session.get(
            f'/api/roster/members?team_id={TestConfig.TEST_TEAM_ID}'
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get('success')
        assert isinstance(data.get('data'), list)

    def test_members_have_scheduling_role(self, admin_session):
        resp = admin_session.get(
            f'/api/roster/members?team_id={TestConfig.TEST_TEAM_ID}'
        )
        data = resp.json()
        if data.get('data'):
            for m in data['data']:
                assert 'scheduling_role' in m, 'Member missing scheduling_role field'
                assert m['scheduling_role'] in ('lead', 'support'), (
                    f"Invalid scheduling_role: {m['scheduling_role']}"
                )

    def test_non_admin_cannot_update_role(self, user_session, admin_session):
        # Get a member id first
        resp = admin_session.get(
            f'/api/roster/members?team_id={TestConfig.TEST_TEAM_ID}'
        )
        members = resp.json().get('data', [])
        if not members:
            pytest.skip('No members found to test role update')
        member_id = members[0]['id']
        resp2 = user_session.put(
            f'/api/roster/members/{member_id}/role',
            json={'scheduling_role': 'lead'},
        )
        assert resp2.status_code in (403, 401)


class TestScheduleAPI:
    """Schedule generation and retrieval."""

    def test_get_schedule_returns_json(self, admin_session):
        resp = admin_session.get(
            f'/api/roster/schedule?team_id={TestConfig.TEST_TEAM_ID}&year={YEAR}&month={MONTH}'
        )
        assert resp.status_code == 200
        assert resp.headers.get('Content-Type', '').startswith('application/json')
        data = resp.json()
        assert data.get('success') is True

    def test_get_schedule_shape(self, admin_session):
        resp = admin_session.get(
            f'/api/roster/schedule?team_id={TestConfig.TEST_TEAM_ID}&year={YEAR}&month={MONTH}'
        )
        data = resp.json()
        if data.get('data'):
            member = data['data'][0]
            assert 'team_member_id' in member
            assert 'name' in member
            assert 'shifts' in member
            assert isinstance(member['shifts'], dict)

    def test_preview_schedule(self, admin_session):
        resp = admin_session.post('/api/roster/preview', json={
            'team_id': TestConfig.TEST_TEAM_ID,
            'year': YEAR,
            'month': MONTH,
        })
        assert resp.status_code in (200, 201), f'Preview returned {resp.status_code}: {resp.text[:300]}'
        data = resp.json()
        assert data.get('success'), f'Preview failed: {data}'
        assert data.get('dry_run') is True

    def test_preview_has_assignments(self, admin_session):
        resp = admin_session.post('/api/roster/preview', json={
            'team_id': TestConfig.TEST_TEAM_ID,
            'year': YEAR,
            'month': MONTH,
        })
        data = resp.json()
        if data.get('success'):
            # May be empty if team has no members — acceptable
            assert isinstance(data.get('assignments', []), list)

    def test_generate_schedule(self, admin_session):
        resp = admin_session.post('/api/roster/generate', json={
            'team_id': TestConfig.TEST_TEAM_ID,
            'year': YEAR,
            'month': MONTH,
            'overwrite': False,
        })
        assert resp.status_code in (200, 201), f'Generate returned {resp.status_code}: {resp.text[:300]}'
        data = resp.json()
        assert data.get('success'), f'Generate failed: {data}'
        assert data.get('dry_run') is False

    def test_generate_schedule_codes_valid(self, admin_session):
        resp = admin_session.post('/api/roster/generate', json={
            'team_id': TestConfig.TEST_TEAM_ID,
            'year': YEAR,
            'month': MONTH,
            'overwrite': True,
        })
        data = resp.json()
        if not data.get('success') or not data.get('assignments'):
            pytest.skip('No assignments in response')
        valid_codes = {'D', 'E', 'N', 'OCN', 'D/OCN', 'E/OCN', 'N/OCN', 'WMO', 'WEO', 'OS', 'OF', 'VL', 'SL', 'HL', 'CO', 'LE', 'G', ''}
        for a in data['assignments']:
            assert a['shift_code'] in valid_codes, (
                f"Unexpected shift code {a['shift_code']} on {a['shift_date']}"
            )

    def test_non_admin_cannot_generate(self, user_session):
        resp = user_session.post('/api/roster/generate', json={
            'team_id': TestConfig.TEST_TEAM_ID,
            'year': YEAR,
            'month': MONTH,
        })
        assert resp.status_code in (403, 401)

    def test_non_admin_cannot_preview(self, user_session):
        resp = user_session.post('/api/roster/preview', json={
            'team_id': TestConfig.TEST_TEAM_ID,
            'year': YEAR,
            'month': MONTH,
        })
        assert resp.status_code in (403, 401)

    def test_regular_user_can_read_schedule(self, user_session):
        resp = user_session.get(
            f'/api/roster/schedule?team_id={TestConfig.TEST_TEAM_ID}&year={YEAR}&month={MONTH}'
        )
        assert resp.status_code in (200, 404)
