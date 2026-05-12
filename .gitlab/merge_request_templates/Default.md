## Summary

<!-- What does this MR do? 1-3 bullet points. -->

## Test plan

<!-- How was this tested? Include steps a reviewer can follow to verify. -->

## Checklist

- [ ] Unit tests pass (`pytest tests/ -v --ignore=tests/test_application.py ...`)
- [ ] Lint passes (`ruff check . && ruff format --check .`)
- [ ] `secrets/` directory was **not** committed
- [ ] No `.env` files (other than `.example`) committed
- [ ] If schema changed: `flask db migrate` run, migration registered in `migrations/README.md`
- [ ] If new Celery task: registered in `celeryconfig.py` and tested
- [ ] CHANGELOG.md updated if user-facing change

## Peer review

**A second person must approve this MR before merging.**
Self-merges are not permitted on `develop` or `master`.

- [ ] Reviewer has read the diff, not just the summary
- [ ] Reviewer has checked for XSS / SQL injection / auth bypass in changed routes
- [ ] Reviewer has verified that no secrets are hardcoded

🤖 See `CONTRIBUTING.md` for the full contribution guide.
