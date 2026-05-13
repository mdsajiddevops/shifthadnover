# Branch Protection Configuration — Shifthandover

## Configuration

**Protected branch**: `develop`
**Enforces**: REQ-001, REQ-002, REQ-003 (CTCOAMSHM-115)

### GitLab UI Steps
1. Navigate to **Settings → Repository → Protected Branches**
2. Find or add `develop` branch
3. Set:
   - **Allowed to push**: No one
   - **Allowed to merge**: Maintainers
   - **Allowed to force push**: Disabled (unchecked)
4. Click **Protect**

### GitLab API (equivalent)
```bash
curl --request PUT \
  --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  --data "push_access_level=0&merge_access_level=40&allow_force_push=false" \
  "https://<gitlab-host>/api/v4/projects/<project-id>/protected_branches/develop"
```
- `push_access_level: 0` = No one
- `merge_access_level: 40` = Maintainers

## Verification

```bash
# From a local clone with push access:
git checkout develop
echo "test" >> README.md && git add . && git commit -m "test direct push"
git push origin develop
# Expected: remote: GitLab: You are not allowed to push code to protected branches on this project.
# Exit code must be non-zero.
```

## Emergency Override Procedure

**Use only for P0 production incidents that cannot wait for MR approval.**

1. Obtain authorisation from the Engineering Lead or VP Engineering (written sign-off required).
2. Temporarily grant push access: GitLab → Settings → Repository → Protected Branches → Edit `develop` → temporarily set Allowed to push to the authorised individual's account.
3. Apply the hotfix commit directly.
4. **Immediately** restore the protection: set Allowed to push back to No one.
5. Raise a post-incident MR to capture the change for audit trail.
6. Record the override in the project audit log with timestamp and authoriser name.

## Approval Rules Reference

See `.gitlab/approval_rules.yml` and `CODEOWNERS` for the Maintainer-approval and self-approval-prevention configuration that complements this branch protection.

---
*Configured for CTCOAMSHM-115. Do not modify without raising a change request.*
