"""Tests for Tollbooth Pro license gating and the tollbooth CLI."""
from __future__ import annotations

import json
import os

import pytest

from nano_empire_tollbooth import (
    issue_license,
    make_keypair,
    monetize,
    pro_enabled,
    reset_tollbooth,
    reset_usage,
    set_license,
    tier,
)
from nano_empire_tollbooth import cli


@pytest.fixture(autouse=True)
def clear_license():
    set_license(None)
    os.environ.pop("TOLLBOOTH_LICENSE_KEY", None)
    yield
    set_license(None)
    os.environ.pop("TOLLBOOTH_LICENSE_KEY", None)


@pytest.fixture()
def issue(monkeypatch):
    """A real signed-key issuer wired to a fresh test keypair.

    Publishes the matching public key via TOLLBOOTH_LICENSE_PUBKEY so that
    pro.py's verify path (which takes no explicit pubkey) can validate it.
    """
    priv, pub = make_keypair()
    monkeypatch.setenv("TOLLBOOTH_LICENSE_PUBKEY", pub)

    def _issue(**kw):
        kw.setdefault("email", "buyer@example.com")
        kw.setdefault("sub_id", "sub_test")
        return issue_license(private_hex=priv, **kw)

    return _issue


# ── license gate ──────────────────────────────────────────────────────────
def test_pro_disabled_by_default():
    assert pro_enabled() is False
    assert tier() == "free"


def test_valid_signed_key_enables_pro(issue):
    set_license(issue())
    assert pro_enabled() is True
    assert tier() == "pro"


def test_arbitrary_string_does_not_enable_pro(issue):
    # Regression: the old gate accepted any >=8-char string. It must not.
    set_license("PRO-ABCDEFGH")
    assert pro_enabled() is False
    set_license("any-long-enough-string")
    assert pro_enabled() is False


def test_short_key_rejected():
    set_license("short")
    assert pro_enabled() is False


def test_expired_key_does_not_enable_pro(issue):
    set_license(issue(issued_at=1_000, expires_at=2_000))
    assert pro_enabled() is False  # exp is in the distant past


def test_env_license(issue):
    import os as _os
    _os.environ["TOLLBOOTH_LICENSE_KEY"] = issue()
    try:
        assert pro_enabled() is True
    finally:
        _os.environ.pop("TOLLBOOTH_LICENSE_KEY", None)


# ── nag suppression ───────────────────────────────────────────────────────
def test_free_shows_nag(capsys):
    reset_tollbooth(); reset_usage()
    @monetize(price_usd=0.0)
    def g():
        return 1
    for _ in range(100):
        g()
    assert "Upgrade to Tollbooth Pro" in capsys.readouterr().err


def test_pro_suppresses_nag(capsys, issue):
    reset_tollbooth(); reset_usage()
    set_license(issue())
    @monetize(price_usd=0.0)
    def f():
        return 1
    for _ in range(101):
        f()
    assert "Upgrade to Tollbooth Pro" not in capsys.readouterr().err


# ── CLI ───────────────────────────────────────────────────────────────────
def _write_ledger(p):
    recs = [
        {"task_id": "t1", "source_agent": "a", "target_agent": "b", "amount_usd": 0.01,
         "status": "escrow_locked", "created_at": "2026-06-09T00:00:00"},
        {"task_id": "t1", "source_agent": "a", "target_agent": "b", "amount_usd": 0.01,
         "status": "released", "payer_wallet": "w", "created_at": "2026-06-09T00:00:01"},
        {"task_id": "t2", "source_agent": "a", "target_agent": "b", "amount_usd": 0.02,
         "status": "released", "payer_wallet": "w2", "created_at": "2026-06-09T00:00:02"},
    ]
    p.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")


def test_report_json(tmp_path, capsys):
    led = tmp_path / "l.jsonl"; _write_ledger(led)
    assert cli.main(["--ledger", str(led), "report", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["summary"]["records"] == 3
    assert out["summary"]["total_usd"] == 0.04
    assert out["summary"]["by_status"]["released"] == 2


def test_verify_ok(tmp_path, capsys):
    led = tmp_path / "l.jsonl"; _write_ledger(led)
    assert cli.main(["--ledger", str(led), "verify"]) == 0
    assert "INTEGRITY: OK" in capsys.readouterr().out


def test_verify_flags_malformed(tmp_path, capsys):
    led = tmp_path / "l.jsonl"
    led.write_text('{"task_id":"t1","amount_usd":0.01,"status":"released"}\nNOT JSON\n', encoding="utf-8")
    assert cli.main(["--ledger", str(led), "verify"]) == 1
    assert "ISSUES" in capsys.readouterr().out


def test_export_gated_without_license(tmp_path, capsys):
    led = tmp_path / "l.jsonl"; _write_ledger(led)
    assert cli.main(["--ledger", str(led), "export", "--format", "csv"]) == 2
    assert "Pro feature" in capsys.readouterr().out


def test_export_works_with_license(tmp_path, issue):
    set_license(issue())
    led = tmp_path / "l.jsonl"; _write_ledger(led)
    out = tmp_path / "out.csv"
    assert cli.main(["--ledger", str(led), "export", "--format", "csv", "--out", str(out)]) == 0
    assert out.exists() and "task_id" in out.read_text()


def test_status_runs(tmp_path):
    led = tmp_path / "l.jsonl"; _write_ledger(led)
    assert cli.main(["--ledger", str(led), "status"]) == 0
