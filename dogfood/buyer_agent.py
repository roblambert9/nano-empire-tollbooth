"""
External buyer agent — completes the full x402 pay-per-call loop.

Run after the endpoint is up:
    python buyer_agent.py
"""
from __future__ import annotations
import os, sys, json, urllib.request

BASE = os.environ.get("DOGFOOD_BASE", "http://127.0.0.1:8099")
WALLET = os.environ.get("BUYER_WALLET", "agent-7f3a")
# In mock mode the valid proof token is "valid-paper-token".
# On mainnet this is the real on-chain tx signature after paying PAY_TO.
TX = os.environ.get("BUYER_TX", "valid-paper-token")

PAYLOAD = {"text": (
    "Autonomous agents increasingly call each other to complete tasks. "
    "Human payment rails assume a person at checkout, which does not fit machine traffic. "
    "A per-call tollbooth meters each request, locks escrow, and settles on success. "
    "This lets builders attribute cost, cap budgets, and recover failed calls automatically."
), "max_sentences": 2}


def _post(payload, headers):
    req = urllib.request.Request(f"{BASE}/summarize", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def main():
    print("Step 1: call with no payment")
    code, body = _post(PAYLOAD, {})
    print(f"  -> HTTP {code}")
    assert code == 402, "expected a 402 payment challenge"
    print(f"  challenge: price ${body['price_usd']} {body['currency']} to {body['pay_to']} via {body['payment_methods']}")

    print("Step 2: pay the toll, retry with X-Payment proof")
    code, body = _post(PAYLOAD, {"X-Payment": f"{WALLET}:{TX}"})
    print(f"  -> HTTP {code}")
    if code != 200:
        print("  payment not verified:", body)
        sys.exit(1)
    print(f"  result: {body['result']}")
    r = body["receipt"]
    print(f"  RECEIPT: earned ${r['amount_usd']} | status {r['status']} | hash {r['settlement_hash']} | payer {r['payer']}")
    print(f"  booth total earned this session: ${body['stats']['total_usd']:.4f}")


if __name__ == "__main__":
    main()
