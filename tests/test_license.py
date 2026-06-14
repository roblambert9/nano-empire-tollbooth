"""Tests for offline Ed25519 license issuance and verification."""
from __future__ import annotations

import pytest

from nano_empire_tollbooth import license as lic


@pytest.fixture()
def keypair():
    return lic.make_keypair()  # (private_hex, public_hex)


def _issue(priv, **kw):
    base = dict(email="buyer@example.com", sub_id="sub_123", issued_at=1_000_000)
    base.update(kw)
    return lic.issue_license(private_hex=priv, **base)


# ── happy path ───────────────────────────────────────────────────────────────
def test_keygen_issue_verify_roundtrip(keypair):
    priv, pub = keypair
    key = _issue(priv, expires_at=2_000_000)
    claim = lic.verify_license(key, public_hex=pub, now=1_500_000)
    assert claim is not None
    assert claim.email == "buyer@example.com"
    assert claim.sub_id == "sub_123"
    assert claim.plan == "pro"
    assert claim.expires_at == 2_000_000


def test_perpetual_key_has_no_expiry(keypair):
    priv, pub = keypair
    key = _issue(priv, expires_at=None)
    claim = lic.verify_license(key, public_hex=pub, now=9_999_999_999)
    assert claim is not None and claim.expires_at is None


def test_key_format_is_three_dotted_parts(keypair):
    priv, _ = keypair
    key = _issue(priv)
    assert key.startswith("NEMPL1.")
    assert len(key.split(".")) == 3


# ── the core bug: arbitrary strings must NOT unlock Pro ───────────────────────
@pytest.mark.parametrize("junk", ["", "x", "PRO-ABCDEFGH", "any-8-plus-char-string", "NEMPL1.foo"])
def test_arbitrary_strings_are_rejected(keypair, junk):
    _, pub = keypair
    assert lic.verify_license(junk, public_hex=pub) is None


def test_tampered_payload_rejected(keypair):
    priv, pub = keypair
    key = _issue(priv, email="buyer@example.com")
    prefix, payload, sig = key.split(".")
    # Re-sign nothing; just swap in a different (validly-encoded) payload.
    forged_payload = lic._b64u_encode(b'{"exp":null,"iat":1,"plan":"pro","sid":"x","sub":"attacker@evil.com"}')
    forged = f"{prefix}.{forged_payload}.{sig}"
    assert lic.verify_license(forged, public_hex=pub) is None


def test_wrong_public_key_rejected(keypair):
    priv, _ = keypair
    _, other_pub = lic.make_keypair()
    key = _issue(priv)
    assert lic.verify_license(key, public_hex=other_pub) is None


def test_expired_key_rejected(keypair):
    priv, pub = keypair
    key = _issue(priv, issued_at=1_000, expires_at=2_000)
    assert lic.verify_license(key, public_hex=pub, now=2_000) is None  # boundary = expired
    assert lic.verify_license(key, public_hex=pub, now=2_001) is None
    assert lic.verify_license(key, public_hex=pub, now=1_999) is not None


def test_no_public_key_configured_fails_closed(keypair, monkeypatch):
    priv, _ = keypair
    monkeypatch.delenv(lic.ENV_PUBKEY, raising=False)
    monkeypatch.setattr(lic, "LICENSE_PUBKEY", "")
    key = _issue(priv)
    assert lic.verify_license(key) is None  # no pubkey anywhere -> not valid


# ── issuance guards ───────────────────────────────────────────────────────────
def test_issue_requires_signing_key(monkeypatch):
    monkeypatch.delenv(lic.ENV_SIGNING_KEY, raising=False)
    with pytest.raises(ValueError):
        lic.issue_license(email="a@b.com", sub_id="s")


def test_issue_rejects_unknown_plan(keypair):
    priv, _ = keypair
    with pytest.raises(ValueError):
        lic.issue_license(email="a@b.com", sub_id="s", plan="enterprise", private_hex=priv)


# ── env-driven resolution (matches how the SDK runs in production) ────────────
def test_env_signing_and_pubkey(keypair, monkeypatch):
    priv, pub = keypair
    monkeypatch.setenv(lic.ENV_SIGNING_KEY, priv)
    monkeypatch.setenv(lic.ENV_PUBKEY, pub)
    key = lic.issue_license(email="env@example.com", sub_id="sub_env", expires_at=None)
    claim = lic.verify_license(key)  # pubkey resolved from env
    assert claim is not None and claim.email == "env@example.com"


# ── describe_license (CLI surface) ────────────────────────────────────────────
def test_describe_license_valid_and_invalid(keypair):
    priv, pub = keypair
    good = _issue(priv, expires_at=2_000_000)
    d = lic.describe_license(good, public_hex=pub, now=1_500_000)
    assert d["valid"] is True and d["plan"] == "pro" and d["reason"] == "valid"

    d2 = lic.describe_license("not-a-key", public_hex=pub)
    assert d2["valid"] is False and d2["plan"] is None
    assert "not a Tollbooth license" in d2["reason"]
