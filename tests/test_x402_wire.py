"""Spec-exact x402 v1 wire format (coinbase/x402 specs/x402-specification-v1.md).

KR2.1: real field names, real shapes — not "x402-style". Paper-mode structural
verification only; chain signature verification is the operator's facilitator.
"""
import base64
import json

import pytest

from nano_empire_tollbooth.x402_wire import (
    X402_VERSION,
    X402ValidationError,
    build_payment_requirements,
    build_payment_required_response,
    build_settlement_response,
    build_verify_request,
    decode_x_payment_header,
    encode_x_payment_header,
    parse_payment_payload,
    verify_structurally,
)

REQS_KW = dict(
    scheme="exact", network="base-sepolia", max_amount_required="10000",
    asset="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
    pay_to="0x209693Bc6afc0C5328bA36FaF03C514EF312287C",
    resource="https://api.example.com/premium-data",
    description="Access to premium market data", max_timeout_seconds=60,
)


def _payload(value="10000", to=REQS_KW["pay_to"], valid_before="9999999999"):
    return {
        "x402Version": 1, "scheme": "exact", "network": "base-sepolia",
        "payload": {
            "signature": "0x" + "ab" * 65,
            "authorization": {
                "from": "0x857b06519E91e3A54538791bDbb0E22373e36b66",
                "to": to, "value": value, "validAfter": "0",
                "validBefore": valid_before, "nonce": "0x" + "11" * 32,
            },
        },
    }


def test_payment_requirements_uses_exact_spec_field_names():
    r = build_payment_requirements(**REQS_KW)
    assert set(r) >= {"scheme", "network", "maxAmountRequired", "asset",
                      "payTo", "resource", "description", "maxTimeoutSeconds"}
    assert r["maxAmountRequired"] == "10000"          # string, atomic units
    assert r["maxTimeoutSeconds"] == 60                # number


def test_402_response_shape():
    resp = build_payment_required_response([build_payment_requirements(**REQS_KW)])
    assert resp["x402Version"] == X402_VERSION == 1
    assert resp["error"] == "X-PAYMENT header is required"
    assert isinstance(resp["accepts"], list) and resp["accepts"][0]["scheme"] == "exact"


def test_x_payment_header_roundtrip_is_base64_json():
    header = encode_x_payment_header(_payload())
    assert json.loads(base64.b64decode(header))["scheme"] == "exact"
    assert decode_x_payment_header(header)["x402Version"] == 1


def test_parse_rejects_missing_fields_with_names():
    bad = _payload(); del bad["payload"]["authorization"]["nonce"]
    with pytest.raises(X402ValidationError) as e:
        parse_payment_payload(bad)
    assert "nonce" in str(e.value)


def test_parse_rejects_wrong_version():
    bad = _payload(); bad["x402Version"] = 2
    with pytest.raises(X402ValidationError):
        parse_payment_payload(bad)


def test_structural_verify_passes_matching_payload():
    reqs = build_payment_requirements(**REQS_KW)
    ok, reason = verify_structurally(_payload(), reqs, now=1)
    assert ok, reason


@pytest.mark.parametrize("kw,frag", [
    (dict(value="9999"), "value"),                       # amount mismatch
    (dict(to="0x" + "00" * 20), "payTo"),                # recipient mismatch
    (dict(valid_before="1"), "expired"),                 # expired auth
])
def test_structural_verify_rejects(kw, frag):
    reqs = build_payment_requirements(**REQS_KW)
    ok, reason = verify_structurally(_payload(**kw), reqs, now=1000)
    assert not ok and frag in reason


def test_settlement_response_success_and_failure():
    ok = build_settlement_response(success=True, transaction="0x" + "12" * 32,
                                   network="base-sepolia", payer="0xabc")
    assert ok["success"] is True and "errorReason" not in ok
    bad = build_settlement_response(success=False, network="base-sepolia",
                                    payer="0xabc", error_reason="insufficient_funds")
    assert bad["transaction"] == "" and bad["errorReason"] == "insufficient_funds"


def test_facilitator_verify_request_shape():
    reqs = build_payment_requirements(**REQS_KW)
    body = build_verify_request(_payload(), reqs)
    assert body["x402Version"] == 1
    assert body["paymentPayload"]["scheme"] == "exact"
    assert body["paymentRequirements"]["payTo"] == REQS_KW["pay_to"]
