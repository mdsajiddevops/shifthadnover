# Regression Test Suite

HTTP integration tests covering all major feature domains.
Every test requires a **running app instance** (Docker or local dev).

## Quick start

```bash
# 1. Set credentials
export TEST_BASE_URL=http://localhost:5000
export TEST_SUPERADMIN_USER=superadmin
export TEST_SUPERADMIN_PASSWORD=your_password
export TEST_USER=ctctestuser
export TEST_USER_PASSWORD=your_user_password
export TEST_ACCOUNT_ID=1
export TEST_TEAM_ID=1

# 2. Run everything
pytest tests/regression/ -v

# 3. Run a single file
pytest tests/regression/test_auth_rbac.py -v

# 4. Run with HTML report
pytest tests/regression/ -v --html=regression_report.html --self-contained-html

# 5. Stop on first failure
pytest tests/regression/ -x -v
```

## File map

| File | What it covers |
|---|---|
| `test_auth_rbac.py` | Login, logout, CSRF, RBAC — regular users can't reach admin pages |
| `test_handover_lifecycle.py` | Full draft→edit→submit→reports flow, delete draft, export |
| `test_data_features.py` | Key points, change info, KB updates, escalation matrix, notifications |
| `test_checkin_roster.py` | Check-in/out API, roster pages, shift swap/leave |
| `test_admin_management.py` | System config, email monitoring, sessions, user management |
| `test_api_contracts.py` | JSON Content-Type headers, 401 for unauth, no silent 500s |
| `test_collaboration.py` | Session join/leave/heartbeat, section locking, draft incident/KP CRUD, SSE stream |
| `test_user_profile.py` | Profile, change password, team context switching, dashboard widgets |

## Using as a regression baseline for new features

Before starting a new feature:
```bash
pytest tests/regression/ -v --tb=short 2>&1 | tee baseline.txt
```

After implementing the feature:
```bash
pytest tests/regression/ -v --tb=short 2>&1 | tee after.txt
diff baseline.txt after.txt
```

Any newly failing tests that appear in `diff` are regressions introduced by the feature.

## Adding tests for a new feature

1. Either add a new class to the most relevant existing file, or create
   `tests/regression/test_<feature_name>.py`.
2. Use the `admin_session`, `user_session`, and `anon_session` fixtures
   from `conftest.py` — they handle auth automatically.
3. Tag test data with a timestamp so it doesn't collide with real data:
   ```python
   TIMESTAMP = datetime.now().strftime("%H%M%S")
   TEST_LABEL = f"REGRESSION-{TIMESTAMP}"
   ```
4. Clean up created records in a fixture teardown (the `yield` pattern).
