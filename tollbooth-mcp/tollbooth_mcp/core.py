"""Core demo logic for tollbooth-mcp — pure functions, no MCP dependency.

Everything here runs in PAPER MODE: payments are simulated, receipts are real
data structures from the live nano-empire-tollbooth package, and no money moves.
"""
from __future__ import annotations

import re
import time
import uuid
from collections import Counter
from typing import Any

from nano_empire_tollbooth import Tollbooth, TollboothConfig

DEMO_PRICE_USD = 0.01
PAPER_NOTE = "paper mode — simulated payment, no real money moves"

_booth: Tollbooth | None = None
_session_ledger: list[dict[str, Any]] = []


def _get_booth() -> Tollbooth:
    global _booth
    if _booth is None:
        _booth = Tollbooth(TollboothConfig(
            toll_per_message_usd=DEMO_PRICE_USD,
            paper_mode=True,
        ))
    return _booth


def _summarize(text: str, max_sentences: int = 2) -> str:
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
    if len(sentences) <= max_sentences:
        return " ".join(sentences)
    words = re.findall(r"[a-z']+", text.lower())
    freq = Counter(w for w in words if len(w) > 3)
    scored = sorted(
        sentences,
        key=lambda s: sum(freq[w] for w in re.findall(r"[a-z']+", s.lower())),
        reverse=True,
    )
    top = set(scored[:max_sentences])
    return " ".join(s for s in sentences if s in top)


def quote_toll(capability: str = "text.summarize") -> dict[str, Any]:
    """Return the x402-style payment challenge an agent would receive (HTTP 402)."""
    return {
        "status_code": 402,
        "capability_id": capability,
        "price_usd": DEMO_PRICE_USD,
        "currency": "USD",
        "nonce": uuid.uuid4().hex,
        "payment_methods": ["x402"],
        "header": "X-Payment",
        "message": "Payment required. Pay the toll, then retry with X-Payment: <wallet>:<proof>.",
        "note": PAPER_NOTE,
    }


async def demo_paid_call(text: str, payer: str = "demo-agent") -> dict[str, Any]:
    """Run the full pay-per-call loop on a real metered function.

    Charges a paper-mode toll through the live tollbooth (escrow lock -> work ->
    release), then returns the result plus the genuine receipt record.
    """
    booth = _get_booth()
    task_id = f"text.summarize:{time.time():.0f}:{uuid.uuid4().hex[:8]}"

    record = await booth.charge(task_id, source_agent=payer, target_agent="tollbooth-mcp")
    try:
        result = _summarize(text)
        await booth.release(task_id)
    except Exception:
        await booth.refund(task_id)
        raise

    final = booth.get_record(task_id)
    receipt = {
        "task_id": task_id,
        "amount_usd": final.amount_usd,
        "status": final.status.value,
        "payer": payer,
        "settled_at": final.settled_at,
        "note": PAPER_NOTE,
    }
    _session_ledger.append(receipt)
    return {
        "result": result,
        "receipt": receipt,
        "session_total_usd": round(sum(r["amount_usd"] for r in _session_ledger), 4),
        "install": "pip install nano-empire-tollbooth",
    }


def get_session_ledger() -> dict[str, Any]:
    """Every paper-mode receipt issued in this MCP session."""
    return {
        "entries": list(_session_ledger),
        "count": len(_session_ledger),
        "total_usd": round(sum(r["amount_usd"] for r in _session_ledger), 4),
        "note": PAPER_NOTE,
    }


def about_tollbooth() -> dict[str, Any]:
    """What this is, how the real package works, and where to learn more."""
    return {
        "what": "nano-empire-tollbooth meters, logs, and settles every call to a "
                "Python function via one decorator: @monetize(price_usd=0.01).",
        "this_server": "A paper-mode demonstration. Receipts and escrow lifecycle are "
                       "real code paths from the live package; payments are simulated.",
        "install": "pip install nano-empire-tollbooth",
        "quickstart": "https://neuralempireai.com/docs/quickstart.html",
        "simulator": "https://neuralempireai.com/simulator/",
        "source": "https://github.com/roblambert9/nano-empire-tollbooth",
        "pricing": "Free: 100 paper-mode calls. Pro ($19/mo): ledger export, higher caps, CLI.",
        "honesty": "No revenue is guaranteed. This is a metering SDK, not an income product.",
    }


def reset_session() -> None:
    """Test helper: clear booth + ledger state."""
    global _booth
    _booth = None
    _session_ledger.clear()
