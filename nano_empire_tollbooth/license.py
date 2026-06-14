"""
Tollbooth Pro license keys — offline, cryptographically verifiable (Ed25519).

A license key is a compact, copy-pasteable string:

    NEMPL1.<base64url(payload_json)>.<base64url(ed25519_signature)>

* ``NEMPL1`` — Nano Empire Pro License, format v1 (lets ``verify_license`` fast-
  reject anything that isn't a license, and lets us version the scheme later).
* payload — canonical JSON ``{"exp","iat","plan","sid","sub"}`` (sorted keys):
  the buyer email (``sub``), the Stripe id it was issued for (``sid``), the plan,
  issued-at and expiry (unix seconds; ``exp`` may be ``null`` for a perpetual key).
* signature — Ed25519 over the exact bytes ``NEMPL1.<base64url(payload)>``.

**Why offline / asymmetric.** Verification needs only the *public* key, so the
published SDK can validate a key with no network call and no embedded secret —
exactly the property that makes it safe to ship. Only the holder of the *private*
key (the operator's server, key from env — never in the package) can mint a key
that verifies. This mirrors ``empire/arthur/honesty/proof.py`` (Proof-of-Honesty),
which uses the same sign-private / verify-public-only pattern.

**Honesty / limits (v1).** Validation is a real signature + expiry check, so a
random string or a tampered/expired key does NOT unlock Pro. What it does *not* do
yet is online revocation: a key stays valid until ``exp`` even if the subscription
is cancelled early. Subscriptions are therefore issued with an expiry near the end
of the paid period and re-issued on renewal; instant revocation is roadmap.

This module is self-contained: it imports nothing from the rest of the package.

The wire format here is the canonical spec. The empire-side issuer
(``empire/commerce/tollbooth_licensing.py``) signs keys in this exact format; a
cross-check test asserts the two stay compatible.
"""
from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass

LICENSE_PREFIX = "NEMPL1"
VALID_PLANS = ("pro",)

# Operator pastes their Ed25519 *public* key (hex) here after running keygen, OR
# sets TOLLBOOTH_LICENSE_PUBKEY in the environment. Empty by default: with no
# public key configured, NO key validates and Pro stays off (fail-closed / honest).
LICENSE_PUBKEY = ""

# Env var names (house rule: keys come from the environment, never hardcoded).
ENV_PUBKEY = "TOLLBOOTH_LICENSE_PUBKEY"
ENV_SIGNING_KEY = "TOLLBOOTH_LICENSE_SIGNING_KEY"

try:  # cryptography is a hard dependency; degrade fail-closed if it's ever absent.
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )

    _CRYPTO_OK = True
except ImportError:  # pragma: no cover - exercised only in a broken install
    _CRYPTO_OK = False


@dataclass(frozen=True)
class LicenseClaim:
    """The verified contents of a license key."""

    email: str
    sub_id: str
    plan: str
    issued_at: int
    expires_at: int | None  # unix seconds; None = no expiry


# ── base64url helpers (no padding, URL/copy-paste safe) ──────────────────────

def _b64u_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64u_decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def _canonical_payload(claim: LicenseClaim) -> str:
    return json.dumps(
        {
            "exp": claim.expires_at,
            "iat": claim.issued_at,
            "plan": claim.plan,
            "sid": claim.sub_id,
            "sub": claim.email,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _signing_input(b64_payload: str) -> bytes:
    return f"{LICENSE_PREFIX}.{b64_payload}".encode("ascii")


# ── keys ─────────────────────────────────────────────────────────────────────

def make_keypair() -> tuple[str, str]:
    """Generate an Ed25519 keypair. Returns (private_hex, public_hex).

    Run once, offline. Keep the private hex secret (set it as
    ``TOLLBOOTH_LICENSE_SIGNING_KEY`` on the issuing server); publish the public
    hex (paste into ``LICENSE_PUBKEY`` / set ``TOLLBOOTH_LICENSE_PUBKEY``).
    """
    if not _CRYPTO_OK:  # pragma: no cover
        raise RuntimeError("cryptography is required to generate keys")
    sk = Ed25519PrivateKey.generate()
    priv = sk.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    ).hex()
    pub = sk.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    ).hex()
    return priv, pub


def _resolve_pubkey(public_hex: str | None) -> str:
    return (
        (public_hex or "").strip()
        or os.environ.get(ENV_PUBKEY, "").strip()
        or LICENSE_PUBKEY.strip()
    )


# ── issue (server-side; needs the private key) ───────────────────────────────

def issue_license(
    *,
    email: str,
    sub_id: str,
    plan: str = "pro",
    issued_at: int | None = None,
    expires_at: int | None = None,
    private_hex: str | None = None,
) -> str:
    """Sign and return a license key. Private key from ``private_hex`` or the
    ``TOLLBOOTH_LICENSE_SIGNING_KEY`` env var. Raises on misconfiguration — never
    returns an unsigned/placeholder key.
    """
    if not _CRYPTO_OK:  # pragma: no cover
        raise RuntimeError("cryptography is required to issue licenses")
    if plan not in VALID_PLANS:
        raise ValueError(f"unknown plan: {plan!r}")
    priv_hex = (private_hex or os.environ.get(ENV_SIGNING_KEY, "")).strip()
    if not priv_hex:
        raise ValueError(
            f"no signing key (pass private_hex or set {ENV_SIGNING_KEY})"
        )
    iat = int(issued_at if issued_at is not None else time.time())
    claim = LicenseClaim(
        email=email, sub_id=sub_id, plan=plan, issued_at=iat, expires_at=expires_at
    )
    b64_payload = _b64u_encode(_canonical_payload(claim).encode("utf-8"))
    sk = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(priv_hex))
    sig = sk.sign(_signing_input(b64_payload))
    return f"{LICENSE_PREFIX}.{b64_payload}.{_b64u_encode(sig)}"


# ── verify (client-side; needs only the public key) ──────────────────────────

def _decode_and_verify(
    key: str | None, public_hex: str | None, now: int | None
) -> tuple[LicenseClaim | None, str]:
    """Return (claim, reason). claim is None unless the key is fully valid."""
    if not _CRYPTO_OK:  # pragma: no cover
        return None, "cryptography unavailable"
    raw = (key or "").strip()
    if not raw:
        return None, "no license key"
    parts = raw.split(".")
    if len(parts) != 3 or parts[0] != LICENSE_PREFIX:
        return None, "not a Tollbooth license key"
    _, b64_payload, b64_sig = parts

    pub_hex = _resolve_pubkey(public_hex)
    if not pub_hex:
        return None, "no public key configured"

    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex)).verify(
            _b64u_decode(b64_sig), _signing_input(b64_payload)
        )
    except InvalidSignature:
        return None, "signature mismatch (forged or tampered key)"
    except (ValueError, TypeError):
        return None, "malformed key or public key"

    try:
        data = json.loads(_b64u_decode(b64_payload).decode("utf-8"))
        claim = LicenseClaim(
            email=str(data["sub"]),
            sub_id=str(data["sid"]),
            plan=str(data["plan"]),
            issued_at=int(data["iat"]),
            expires_at=None if data["exp"] is None else int(data["exp"]),
        )
    except (ValueError, TypeError, KeyError):
        return None, "malformed payload"

    if claim.plan not in VALID_PLANS:
        return None, f"unknown plan: {claim.plan}"
    if claim.expires_at is not None:
        current = int(now if now is not None else time.time())
        if current >= claim.expires_at:
            return None, "license expired"
    return claim, "valid"


def verify_license(
    key: str | None, *, public_hex: str | None = None, now: int | None = None
) -> LicenseClaim | None:
    """Return the LicenseClaim if ``key`` is a genuine, unexpired license, else None.

    Fails closed: a random string, a tampered or forged key, an expired key, or a
    missing public key all return None.
    """
    claim, _reason = _decode_and_verify(key, public_hex, now)
    return claim


def describe_license(
    key: str | None, *, public_hex: str | None = None, now: int | None = None
) -> dict:
    """Human-facing detail for the CLI: {valid, reason, plan, email, expires_at}."""
    claim, reason = _decode_and_verify(key, public_hex, now)
    return {
        "valid": claim is not None,
        "reason": reason,
        "plan": claim.plan if claim else None,
        "email": claim.email if claim else None,
        "expires_at": claim.expires_at if claim else None,
    }
