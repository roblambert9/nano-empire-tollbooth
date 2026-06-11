"""Batch-netting settlement: many cent-level releases -> one net settlement.

The feature that makes sub-cent pricing work on fiat: card rails can't clear a
cent, so the ledger accumulates released tolls and `tollbooth settle` nets them
into one charge once the total crosses the processor minimum.
"""
import json
from pathlib import Path

import pytest

from nano_empire_tollbooth.settlement import (
    DEFAULT_MINIMUM_USD,
    SettlementResult,
    settle,
)


def _write_ledger(path: Path, entries: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def _released(task_id: str, usd: float) -> dict:
    return {"task_id": task_id, "amount_usd": usd, "status": "released",
            "source_agent": "buyer", "target_agent": "seller",
            "created_at": "2026-06-11T00:00:00+00:00"}


@pytest.fixture()
def ledger(tmp_path):
    return tmp_path / "toll_ledger.jsonl"


def test_nets_released_calls_into_one_settlement(ledger, tmp_path):
    _write_ledger(ledger, [_released(f"t{i}", 0.01) for i in range(50)])
    res = settle(ledger, paper=True)
    assert isinstance(res, SettlementResult)
    assert res.settled is True
    assert res.call_count == 50
    assert res.net_usd == pytest.approx(0.50)
    assert res.batch_id
    # settlement record persisted next to the ledger
    srecs = [json.loads(l) for l in res.settlements_path.read_text().splitlines()]
    assert srecs[-1]["net_usd"] == pytest.approx(0.50)
    assert srecs[-1]["mode"] == "paper"
    assert sorted(srecs[-1]["task_ids"])[:2] == ["t0", "t1"]


def test_below_minimum_does_not_settle(ledger):
    _write_ledger(ledger, [_released(f"t{i}", 0.01) for i in range(10)])  # $0.10
    res = settle(ledger, paper=True)
    assert res.settled is False
    assert res.net_usd == pytest.approx(0.10)
    assert res.reason and "minimum" in res.reason
    assert DEFAULT_MINIMUM_USD == pytest.approx(0.50)


def test_custom_minimum(ledger):
    _write_ledger(ledger, [_released(f"t{i}", 0.01) for i in range(10)])
    res = settle(ledger, paper=True, minimum_usd=0.10)
    assert res.settled is True


def test_idempotent_already_settled_excluded(ledger):
    _write_ledger(ledger, [_released(f"t{i}", 0.01) for i in range(50)])
    first = settle(ledger, paper=True)
    assert first.settled and first.call_count == 50
    second = settle(ledger, paper=True)
    assert second.settled is False
    assert second.call_count == 0  # nothing left to net


def test_only_released_entries_count(ledger):
    entries = [_released("ok1", 0.30), _released("ok2", 0.30)]
    entries.append({**_released("locked", 5.0), "status": "escrow_locked"})
    entries.append({**_released("refunded", 5.0), "status": "refunded"})
    _write_ledger(ledger, entries)
    res = settle(ledger, paper=True)
    assert res.settled is True
    assert res.call_count == 2
    assert res.net_usd == pytest.approx(0.60)


def test_empty_ledger(ledger):
    ledger.write_text("")
    res = settle(ledger, paper=True)
    assert res.settled is False and res.call_count == 0


def test_live_mode_refuses_without_operator_wiring(ledger):
    _write_ledger(ledger, [_released(f"t{i}", 0.01) for i in range(60)])
    res = settle(ledger, paper=False)
    # No Stripe wiring in the SDK by design: live settle must fail closed.
    assert res.settled is False
    assert res.reason and "operator" in res.reason.lower()
