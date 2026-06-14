# Releasing nano-empire-tollbooth

Two automated paths. Both keep the token out of the repo and out of any command line.

## Path A — Zero-token (recommended): GitHub Actions + Trusted Publishing

No API token exists anywhere. GitHub authenticates to PyPI via OIDC.

**One-time setup** (PyPI → your account → *Publishing* → *Add a pending publisher*):

| Field | Value |
|---|---|
| PyPI project name | `nano-empire-tollbooth` |
| Owner | `roblambert9` |
| Repository | `nano-empire-tollbooth` |
| Workflow filename | `publish.yml` |
| Environment | `pypi` |

**Every release after that:**

```bash
git tag v0.3.0
git push origin v0.3.0      # GitHub builds, validates, and publishes
```

## Path B — Local one-command (`release.ps1`)

Uses a token stored once in `%USERPROFILE%\.pypirc` (twine reads it automatically;
it is git-ignored and never printed).

**One-time setup** — create `%USERPROFILE%\.pypirc`:

```ini
[pypi]
  username = __token__
  password = pypi-AgEI...your-real-token...
```

**Every release:**

```powershell
.\release.ps1            # version from pyproject.toml
.\release.ps1 0.3.1      # or explicit
```

The script rebuilds, validates, uploads (idempotent `--skip-existing`),
smoke-tests the live package in a throwaway venv, and tags the commit.
It stops *before* upload with instructions if no credential is present, so it
never hangs on a prompt.

## What "honest 0.3.0" means

- Free MIT SDK. Local ledger, signed receipts, PAPER_MODE simulator.
- Pro exists in the code path but is **not purchasable** (private setup only).
- No Stripe buy link in the public package. No live payments.
- Revenue: $0 until proven otherwise.
