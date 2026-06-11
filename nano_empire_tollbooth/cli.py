"""
tollbooth command-line interface.

Real, offline value over your local ledger:

  tollbooth status                 show tier (free/pro) and ledger summary
  tollbooth report [--json]        aggregate the ledger: calls, spend, by status
  tollbooth verify                 integrity check of the ledger file
  tollbooth export --format csv    export the ledger (Pro feature)
  tollbooth settle                 net released tolls into one settlement

All commands read the JSONL ledger written by the tollbooth. Point at a specific
file with --ledger PATH.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import Counter
from pathlib import Path

from .pro import pro_enabled, tier

_UPGRADE_URL = "https://buy.stripe.com/14A9ATaI76K8gjo9JE1Nu0h"
_DEFAULT_LEDGER = Path(__file__).resolve().parent.parent / "logs" / "toll_ledger.jsonl"


def _load(ledger: Path) -> tuple[list[dict], list[str]]:
    """Return (records, errors). Never raises on a bad line."""
    records: list[dict] = []
    errors: list[str] = []
    if not ledger.exists():
        return records, [f"ledger not found: {ledger}"]
    for i, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            errors.append(f"line {i}: malformed JSON ({exc.msg})")
    return records, errors


def _summary(records: list[dict]) -> dict:
    total_usd = sum(float(r.get("amount_usd", 0) or 0) for r in records)
    by_status = Counter(r.get("status", "unknown") for r in records)
    payers = {r.get("payer_wallet") for r in records if r.get("payer_wallet")}
    ts = sorted(r.get("created_at", "") for r in records if r.get("created_at"))
    return {
        "records": len(records),
        "total_usd": round(total_usd, 6),
        "by_status": dict(by_status),
        "unique_payers": len(payers),
        "first": ts[0] if ts else None,
        "last": ts[-1] if ts else None,
    }


def cmd_report(args) -> int:
    records, errors = _load(Path(args.ledger))
    summary = _summary(records)
    if args.json:
        print(json.dumps({"summary": summary, "errors": errors}, indent=2))
        return 0
    print(f"Ledger: {args.ledger}")
    print(f"Records:       {summary['records']}")
    print(f"Total USD:     {summary['total_usd']}")
    print(f"Unique payers: {summary['unique_payers']}")
    print(f"Range:         {summary['first']}  ->  {summary['last']}")
    print("By status:")
    for k, v in summary["by_status"].items():
        print(f"  {k:<14} {v}")
    if errors:
        print(f"Warnings: {len(errors)} malformed line(s)")
    return 0


def cmd_verify(args) -> int:
    records, errors = _load(Path(args.ledger))
    required = {"task_id", "amount_usd", "status"}
    missing = sum(1 for r in records if not required.issubset(r))
    seen: Counter = Counter(r.get("task_id") for r in records)
    dupes = {k: c for k, c in seen.items() if k and c > 1}
    ok = not errors and missing == 0
    print(f"Ledger: {args.ledger}")
    print(f"Records parsed:        {len(records)}")
    print(f"Malformed lines:       {len(errors)}")
    print(f"Records missing fields: {missing}")
    print(f"Repeated task_ids:     {len(dupes)} (normal for charge+release pairs)")
    print("INTEGRITY: OK" if ok else "INTEGRITY: ISSUES FOUND")
    for e in errors[:10]:
        print(f"  {e}")
    return 0 if ok else 1


def cmd_status(args) -> int:
    records, _ = _load(Path(args.ledger))
    print(f"Tier:        {tier()}")
    print(f"Pro active:  {pro_enabled()}")
    print(f"Free limit:  100 calls/function (paper mode)")
    print(f"Ledger:      {args.ledger}  ({len(records)} records)")
    if not pro_enabled():
        print(f"Upgrade to Pro for exports and higher caps: {_UPGRADE_URL}")
    return 0


def cmd_export(args) -> int:
    if not pro_enabled():
        print("export is a Tollbooth Pro feature.")
        print(f"Upgrade ($19/mo) then set TOLLBOOTH_LICENSE_KEY: {_UPGRADE_URL}")
        return 2
    records, _ = _load(Path(args.ledger))
    if args.format == "json":
        out = json.dumps(records, indent=2)
    else:
        buf = io.StringIO()
        fields = ["task_id", "source_agent", "target_agent", "amount_usd", "status", "created_at"]
        w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in records:
            w.writerow(r)
        out = buf.getvalue()
    if args.out:
        Path(args.out).write_text(out, encoding="utf-8")
        print(f"Wrote {len(records)} records to {args.out}")
    else:
        print(out)
    return 0


def cmd_settle(args) -> int:
    from .settlement import DEFAULT_MINIMUM_USD, settle
    minimum = args.minimum if args.minimum is not None else DEFAULT_MINIMUM_USD
    res = settle(Path(args.ledger), paper=not args.live, minimum_usd=minimum)
    if res.settled:
        print(f"SETTLED {res.batch_id}: {res.call_count} call(s) netted to "
              f"${res.net_usd:.2f} ({res.mode} mode)")
        print(f"record: {res.settlements_path}")
        return 0
    print(f"no settlement: {res.reason} "
          f"({res.call_count} pending call(s), net ${res.net_usd:.2f})")
    return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tollbooth", description="Tollbooth ledger tools.")
    p.add_argument("--ledger", default=str(_DEFAULT_LEDGER), help="path to toll_ledger.jsonl")
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("report", help="aggregate the ledger")
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=cmd_report)
    v = sub.add_parser("verify", help="integrity check")
    v.set_defaults(func=cmd_verify)
    s = sub.add_parser("status", help="show tier and ledger summary")
    s.set_defaults(func=cmd_status)
    e = sub.add_parser("export", help="export ledger (Pro)")
    e.add_argument("--format", choices=["csv", "json"], default="csv")
    e.add_argument("--out", default=None)
    e.set_defaults(func=cmd_export)
    st = sub.add_parser("settle",
                        help="net released tolls into one settlement (batch netting)")
    st.add_argument("--minimum", type=float, default=None,
                    help="minimum net USD to settle (default 0.50)")
    st.add_argument("--live", action="store_true",
                    help="live mode (fails closed: operator wiring required)")
    st.set_defaults(func=cmd_settle)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
