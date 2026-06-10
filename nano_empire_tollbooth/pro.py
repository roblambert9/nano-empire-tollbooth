"""
Tollbooth Pro license gating (self-contained, offline).

Pro is unlocked by setting TOLLBOOTH_LICENSE_KEY in the environment, or by
calling set_license(key) at runtime. Purchasing Tollbooth Pro issues you a key.

Honesty note: validation is currently an offline presence/format check
(honor-system v1). Server-side key validation is on the roadmap and is NOT
claimed to exist yet. What Pro unlocks today is concrete and shippable:
  - no upgrade nag on the free-call limit
  - ledger export to CSV/JSON via the `tollbooth export` command
  - higher default daily spend cap

This module imports nothing from the rest of the package, to avoid import cycles.
"""
from __future__ import annotations

import os

FREE_DAILY_CAP_USD = 10.0
PRO_DAILY_CAP_USD = 1000.0
_MIN_KEY_LEN = 8

_state: dict[str, str | None] = {"key": None}


def set_license(key: str | None) -> None:
    """Set a Pro license key at runtime. Pass None or '' to clear."""
    cleaned = (key or "").strip()
    _state["key"] = cleaned or None


def get_license() -> str | None:
    """Return the active license key from runtime state or environment."""
    if _state["key"]:
        return _state["key"]
    env = os.environ.get("TOLLBOOTH_LICENSE_KEY", "").strip()
    return env or None


def pro_enabled() -> bool:
    """True if a plausibly-valid Pro license is present (offline check)."""
    key = get_license()
    return bool(key) and len(key) >= _MIN_KEY_LEN


def tier() -> str:
    return "pro" if pro_enabled() else "free"


def daily_cap_usd() -> float:
    return PRO_DAILY_CAP_USD if pro_enabled() else FREE_DAILY_CAP_USD
