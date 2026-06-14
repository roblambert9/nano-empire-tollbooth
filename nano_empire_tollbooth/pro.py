"""
Tollbooth Pro license gating (self-contained, offline).

Pro is unlocked by setting TOLLBOOTH_LICENSE_KEY in the environment to a key
issued at purchase, or by calling set_license(key) at runtime.

Validation is real: the key must carry a valid Ed25519 signature from the
operator's license key and must not be expired (see ``license.py``). A random
string, a tampered key, or an expired key does NOT unlock Pro — it fails closed.
Verification is offline and needs only the published *public* key, so there is no
phone-home and no embedded secret.

What Pro unlocks today is concrete and shippable (NOT "live payments"):
  - no upgrade nag on the free-call limit
  - ledger export to CSV/JSON via the `tollbooth export` command
  - higher default daily spend cap
  - priority support

This module imports only the sibling ``license`` module, to avoid import cycles.
"""
from __future__ import annotations

import os

from .license import LicenseClaim, describe_license, verify_license

FREE_DAILY_CAP_USD = 10.0
PRO_DAILY_CAP_USD = 1000.0

ENV_LICENSE_KEY = "TOLLBOOTH_LICENSE_KEY"

_state: dict[str, str | None] = {"key": None}


def set_license(key: str | None) -> None:
    """Set a Pro license key at runtime. Pass None or '' to clear."""
    cleaned = (key or "").strip()
    _state["key"] = cleaned or None


def get_license() -> str | None:
    """Return the active license key from runtime state or environment."""
    if _state["key"]:
        return _state["key"]
    env = os.environ.get(ENV_LICENSE_KEY, "").strip()
    return env or None


def license_claim() -> LicenseClaim | None:
    """Return the verified LicenseClaim for the active key, or None."""
    return verify_license(get_license())


def license_status() -> dict:
    """Detail for the CLI/status: {valid, reason, plan, email, expires_at}."""
    return describe_license(get_license())


def pro_enabled() -> bool:
    """True only if a genuine, unexpired Pro license is present (offline check)."""
    return license_claim() is not None


def tier() -> str:
    return "pro" if pro_enabled() else "free"


def daily_cap_usd() -> float:
    return PRO_DAILY_CAP_USD if pro_enabled() else FREE_DAILY_CAP_USD
