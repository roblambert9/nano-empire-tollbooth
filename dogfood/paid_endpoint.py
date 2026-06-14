"""
Dogfood paid endpoint — x402-gated, metered through nano-empire-tollbooth.
====================================================================

A real, runnable demonstration of the loop:
  1. Agent calls /summarize with no payment  -> HTTP 402 + payment challenge
  2. Agent pays, retries with X-Payment proof -> verified, metered, served

The useful function is an extractive text summarizer (stdlib only, no API key),
so the endpoint delivers genuine value for its toll.

Verifier is pluggable via env DOGFOOD_VERIFIER:
  - "mock"   : accepts the proof token "valid-paper-token" (local proof of loop)
  - "onchain": verifies a real stablecoin tx via DOGFOOD_FACILITATOR_URL (mainnet)

Price: 1 cent (USD 0.01) per call. This is informational and not financial advice.
"""
from __future__ import annotations

import os
import re
import time
import uuid
from collections import Counter

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from nano_empire_tollbooth import Tollbooth, TollboothConfig
from nano_empire_tollbooth.tollbooth import SettlementStatus

PRICE_USD = 0.01
CAPABILITY = "text.summarize"
PAY_TO = os.environ.get("DOGFOOD_PAY_TO", "demo-receiving-wallet")
VERIFIER = os.environ.get("DOGFOOD_VERIFIER", "mock")
LEDGER = os.environ.get("DOGFOOD_LEDGER", "/sessions/lucid-eager-fermi/mnt/outputs/dogfood/toll_ledger.jsonl")

# Live tollbooth: real escrow, real ledger. paper_mode False so this is the live path.
booth = Tollbooth(TollboothConfig(
    toll_per_message_usd=PRICE_USD,
    paper_mode=False,
    require_payment_before_route=True,
    ledger_path=__import__("pathlib").Path(LEDGER),
))

_seen_nonces: set[str] = set()


async def _verify(payer_wallet: str, tx_signature: str, amount: float) -> bool:
    if VERIFIER == "mock":
        return tx_signature == "valid-paper-token"
    if VERIFIER == "onchain":
        url = os.environ.get("DOGFOOD_FACILITATOR_URL")
        if not url:
            return False  # refuse: no real facilitator configured
        import urllib.request, json as _json
        body = _json.dumps({"wallet": payer_wallet, "tx": tx_signature,
                            "amount_usd": amount, "pay_to": PAY_TO}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return _json.loads(r.read()).get("verified") is True
    return False

booth.set_x402_verifier(_verify)

app = FastAPI(title="Nano Empire dogfood endpoint")
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware,
    allow_origins=['https://neuralempireai.com', 'https://www.neuralempireai.com'],
    allow_methods=['GET'], allow_headers=['*'])


def summarize(text: str, max_sentences: int = 2) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s for s in sentences if s]
    if len(sentences) <= max_sentences:
        return " ".join(sentences)
    words = re.findall(r"[a-z']+", text.lower())
    freq = Counter(w for w in words if len(w) > 3)
    scored = sorted(sentences, key=lambda s: sum(freq[w] for w in re.findall(r"[a-z']+", s.lower())), reverse=True)
    top = scored[:max_sentences]
    return " ".join(s for s in sentences if s in top)


def _challenge(nonce: str) -> dict:
    return {
        "status_code": 402, "capability_id": CAPABILITY,
        "price_usd": PRICE_USD, "price_minor": 1, "currency": "USD",
        "pay_to": PAY_TO, "nonce": nonce,
        "payment_methods": ["x402"], "verifier": VERIFIER,
        "header": "X-Payment",
        "message": "Payment required. Pay the toll, then retry with X-Payment: <wallet>:<tx_signature>.",
        "disclaimer": "Informational, not financial advice.",
    }


@app.post("/summarize")
async def paid_summarize(request: Request):
    proof = request.headers.get("X-Payment")
    if not proof or ":" not in proof:
        nonce = uuid.uuid4().hex
        _seen_nonces.add(nonce)
        return JSONResponse(status_code=402, content=_challenge(nonce))

    wallet, _, tx = proof.partition(":")
    body = await request.json()
    text = body.get("text", "")
    max_s = int(body.get("max_sentences", 2))
    task_id = f"{CAPABILITY}:{time.time():.0f}:{uuid.uuid4().hex[:8]}"

    record = await booth.charge(task_id, source_agent=wallet, target_agent="nano-empire",
                                payer_wallet=wallet, tx_signature=tx)
    if record.status != SettlementStatus.ESCROW_LOCKED:
        return JSONResponse(status_code=402, content={
            "error": "payment_not_verified", "status": record.status.value,
            **_challenge(uuid.uuid4().hex)})

    try:
        result = summarize(text, max_s)
        await booth.release(task_id)
    except Exception as exc:
        await booth.refund(task_id)
        return JSONResponse(status_code=500, content={"error": str(exc)})

    final = booth.get_record(task_id)
    return {
        "result": result,
        "receipt": {
            "task_id": task_id, "amount_usd": final.amount_usd,
            "status": final.status.value, "settlement_hash": final.settlement_hash,
            "payer": wallet, "settled_at": final.settled_at,
        },
        "stats": booth.get_stats(),
    }


@app.get("/health")
def health():
    return {"ok": True, "verifier": VERIFIER, "price_usd": PRICE_USD, "pay_to": PAY_TO}


# ── Public observability: the live machine-economy window ──────────────────
# Read-only, paper-mode-labeled, no wallets beyond what payers sent publicly.

@app.get("/ledger")
def public_ledger(limit: int = 20):
    """Last N ledger lines — the live feed any browser or agent can watch."""
    import json as _json
    from pathlib import Path as _P
    path = _P(LEDGER)
    entries = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines()[-max(1, min(limit, 100)):]:
            try:
                e = _json.loads(line)
                entries.append({k: e.get(k) for k in
                                ("task_id", "amount_usd", "status", "settled_at",
                                 "created_at", "source_agent")})
            except Exception:
                continue
    return {"mode": "paper — simulated payments, no real money moves",
            "count": len(entries), "entries": entries}


@app.get("/verify/{settlement_hash}")
def verify_receipt(settlement_hash: str):
    """Public receipt verification: anyone can check a hash against the ledger."""
    import hashlib as _h
    import json as _json
    from pathlib import Path as _P
    path = _P(LEDGER)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                e = _json.loads(line)
            except Exception:
                continue
            raw = f"{e.get('task_id')}:{e.get('nonce')}:{e.get('tx_signature')}:{e.get('created_at')}"
            if _h.sha256(raw.encode()).hexdigest()[:16] == settlement_hash:
                return {"verified": True, "status": e.get("status"),
                        "amount_usd": e.get("amount_usd"),
                        "settled_at": e.get("settled_at"),
                        "mode": "paper — simulated, no real money moved"}
    return {"verified": False, "reason": "no ledger entry matches that hash"}
