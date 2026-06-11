"""Spec-exact x402 v1 wire format helpers.

Implements the shapes from coinbase/x402 `specs/x402-specification-v1.md`
(snapshot: empire docs/x402-spec-v1-snapshot.md): PaymentRequirementsResponse,
PaymentPayload (exact scheme), SettlementResponse, the X-PAYMENT HTTP header
binding (base64 JSON), and the facilitator /verify request body.

Honesty boundary: `verify_structurally` checks STRUCTURE and consistency only
(fields, version, recipient, amount, expiry). It does not and cannot verify
the EIP-712 signature on-chain — that is the facilitator's job, wired by the
operator. Paper mode stays a simulation.
"""
from __future__ import annotations

import base64
import json
from typing import Any, Optional

X402_VERSION = 1

_AUTH_FIELDS = ("from", "to", "value", "validAfter", "validBefore", "nonce")


class X402ValidationError(ValueError):
    """A payload does not match the x402 v1 spec; message names the problem."""


def build_payment_requirements(
    *, scheme: str, network: str, max_amount_required: str, asset: str,
    pay_to: str, resource: str, description: str, max_timeout_seconds: int,
    mime_type: Optional[str] = None, output_schema: Optional[dict] = None,
    extra: Optional[dict] = None,
) -> dict[str, Any]:
    """One PaymentRequirements object for the `accepts` array (5.1.2)."""
    req: dict[str, Any] = {
        "scheme": scheme,
        "network": network,
        "maxAmountRequired": str(max_amount_required),
        "asset": asset,
        "payTo": pay_to,
        "resource": resource,
        "description": description,
        "maxTimeoutSeconds": int(max_timeout_seconds),
    }
    if mime_type is not None:
        req["mimeType"] = mime_type
    if output_schema is not None:
        req["outputSchema"] = output_schema
    if extra is not None:
        req["extra"] = extra
    return req


def build_payment_required_response(
    accepts: list[dict[str, Any]],
    error: str = "X-PAYMENT header is required",
) -> dict[str, Any]:
    """The 402 response body: PaymentRequirementsResponse (5.1)."""
    return {"x402Version": X402_VERSION, "error": error, "accepts": list(accepts)}


def encode_x_payment_header(payment_payload: dict[str, Any]) -> str:
    """HTTP binding: X-PAYMENT carries the PaymentPayload as base64 JSON."""
    raw = json.dumps(payment_payload, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def decode_x_payment_header(header_value: str) -> dict[str, Any]:
    try:
        return json.loads(base64.b64decode(header_value))
    except Exception as exc:  # noqa: BLE001
        raise X402ValidationError(f"X-PAYMENT header is not base64 JSON: {exc}") from exc


def parse_payment_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Validate a PaymentPayload (5.2). Returns it unchanged; raises naming
    every missing/invalid field."""
    missing = [f for f in ("x402Version", "scheme", "network", "payload")
               if f not in data]
    if missing:
        raise X402ValidationError(f"PaymentPayload missing fields: {missing}")
    if data["x402Version"] != X402_VERSION:
        raise X402ValidationError(
            f"unsupported x402Version {data['x402Version']!r} (must be {X402_VERSION})")
    payload = data["payload"]
    if "signature" not in payload:
        raise X402ValidationError("SchemePayload missing field: signature")
    auth = payload.get("authorization")
    if not isinstance(auth, dict):
        raise X402ValidationError("SchemePayload missing field: authorization")
    missing = [f for f in _AUTH_FIELDS if f not in auth]
    if missing:
        raise X402ValidationError(f"Authorization missing fields: {missing}")
    return data


def verify_structurally(
    payment_payload: dict[str, Any],
    payment_requirements: dict[str, Any],
    *, now: Optional[float] = None,
) -> tuple[bool, str]:
    """Paper-mode consistency check of payload against requirements.

    NOT signature verification — see module docstring. Returns (ok, reason).
    """
    try:
        parse_payment_payload(payment_payload)
    except X402ValidationError as exc:
        return False, str(exc)

    auth = payment_payload["payload"]["authorization"]
    if payment_payload["scheme"] != payment_requirements["scheme"]:
        return False, "scheme mismatch"
    if payment_payload["network"] != payment_requirements["network"]:
        return False, "network mismatch"
    if auth["to"] != payment_requirements["payTo"]:
        return False, f"payTo mismatch: authorization.to={auth['to']!r}"
    if auth["value"] != payment_requirements["maxAmountRequired"]:
        return False, (f"value mismatch: {auth['value']!r} != "
                       f"maxAmountRequired {payment_requirements['maxAmountRequired']!r}")
    if now is not None:
        if float(auth["validBefore"]) <= now:
            return False, "authorization expired (validBefore <= now)"
        if float(auth["validAfter"]) > now:
            return False, "authorization not yet valid (validAfter > now)"
    return True, "structurally valid (signature NOT verified — paper mode)"


def build_settlement_response(
    *, success: bool, network: str, payer: str,
    transaction: str = "", error_reason: Optional[str] = None,
) -> dict[str, Any]:
    """SettlementResponse (5.3) for the X-PAYMENT-RESPONSE header."""
    resp: dict[str, Any] = {
        "success": success,
        "transaction": transaction if success else "",
        "network": network,
        "payer": payer,
    }
    if not success and error_reason:
        resp["errorReason"] = error_reason
    return resp


def build_verify_request(
    payment_payload: dict[str, Any], payment_requirements: dict[str, Any],
) -> dict[str, Any]:
    """Facilitator POST /verify body (7.1)."""
    return {
        "x402Version": X402_VERSION,
        "paymentPayload": payment_payload,
        "paymentRequirements": payment_requirements,
    }
