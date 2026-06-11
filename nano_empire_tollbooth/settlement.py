"""Batch-netting settlement — sub-cent pricing on fiat rails.

Card processors can't clear a cent (Stripe's effective floor is ~$0.50). The
tollbooth's answer: meter cent-level calls in the append-only ledger, then net
all released-and-unsettled tolls into ONE settlement once the total crosses the
minimum. Paper mode records the settlement honestly; live mode fails closed
until the operator wires a real charge hook — the SDK never moves money itself.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DEFAULT_MINIMUM_USD = 0.50
SETTLEMENTS_SUFFIX = ".settlements.jsonl"


@dataclass(frozen=True)
class SettlementResult:
    settled: bool
    net_usd: float
    call_count: int
    batch_id: str = ""
    mode: str = "paper"
    reason: str = ""
    task_ids: tuple[str, ...] = field(default_factory=tuple)
    settlements_path: Optional[Path] = None


def _settlements_path(ledger_path: Path) -> Path:
    return ledger_path.with_name(ledger_path.stem + SETTLEMENTS_SUFFIX)


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # verify() owns integrity reporting; settle skips bad lines
    return records


def _already_settled_ids(settlements: list[dict]) -> set[str]:
    done: set[str] = set()
    for s in settlements:
        done.update(s.get("task_ids", []))
    return done


def settle(ledger_path: Path, *, paper: bool = True,
           minimum_usd: float = DEFAULT_MINIMUM_USD) -> SettlementResult:
    """Net all released, not-yet-settled tolls into one settlement record.

    Returns a SettlementResult; writes one JSON line to
    <ledger>.settlements.jsonl when a settlement occurs. Idempotent: task_ids
    referenced by prior settlement records are never netted twice.
    """
    ledger_path = Path(ledger_path)
    spath = _settlements_path(ledger_path)

    done = _already_settled_ids(_read_jsonl(spath))
    pending: dict[str, float] = {}
    for rec in _read_jsonl(ledger_path):
        tid = rec.get("task_id")
        if not tid or tid in done or tid in pending:
            continue
        if rec.get("status") != "released":
            continue
        try:
            pending[tid] = float(rec.get("amount_usd", 0))
        except (TypeError, ValueError):
            continue

    net = round(sum(pending.values()), 6)
    count = len(pending)

    if count == 0:
        return SettlementResult(False, 0.0, 0, reason="nothing to settle",
                                settlements_path=spath)
    if net < minimum_usd:
        return SettlementResult(
            False, net, count,
            reason=f"net ${net:.2f} below minimum ${minimum_usd:.2f}",
            settlements_path=spath)
    if not paper:
        # Fail closed: the SDK ships no payment credentials and never moves
        # real money. Live settlement requires the operator to take the netted
        # batch and charge it through their own processor account.
        return SettlementResult(
            False, net, count, mode="live",
            reason="live settlement requires operator wiring (e.g. create one "
                   "Stripe PaymentIntent for net_usd in YOUR account, then "
                   "record it); the SDK fails closed by design",
            settlements_path=spath)

    batch_id = f"settle-{uuid.uuid4().hex[:12]}"
    record = {
        "batch_id": batch_id,
        "mode": "paper",
        "net_usd": net,
        "call_count": count,
        "task_ids": sorted(pending),
        "settled_at": datetime.now(timezone.utc).isoformat(),
        "note": "paper mode — simulated settlement, no real money moves",
    }
    spath.parent.mkdir(parents=True, exist_ok=True)
    with open(spath, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return SettlementResult(True, net, count, batch_id=batch_id, mode="paper",
                            task_ids=tuple(sorted(pending)),
                            settlements_path=spath)
