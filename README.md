# nano-empire-tollbooth

Monetize and meter any Python function with one decorator.

```python
from nano_empire_tollbooth import monetize

@monetize(price_usd=0.01)
def summarize(text: str) -> str:
    return my_llm(text)
```

Every call is metered and logged to a local JSONL ledger. The first 100 calls
print an upgrade prompt once you cross the limit; the function keeps working.

## Install

```bash
pip install nano-empire-tollbooth
```

Python 3.9+, one dependency (pydantic).

## Command line

The package ships a `tollbooth` command that works over your local ledger:

```bash
tollbooth status                 # show tier (free/pro) and a ledger summary
tollbooth report                 # aggregate: calls, spend, by status
tollbooth report --json          # same, machine readable
tollbooth verify                 # integrity check of the ledger file
tollbooth export --format csv    # export the ledger (Pro)
```

## Free vs Pro

What Pro actually unlocks today. No overstated claims.

| | Free | Pro ($19/mo) |
|---|---|---|
| Metered calls | Unlimited (paper mode) | Unlimited (paper mode) |
| Local JSONL ledger | Yes | Yes |
| `report` and `verify` | Yes | Yes |
| Upgrade prompt | Shown after 100 calls | Suppressed |
| `tollbooth export` (CSV/JSON) | No | Yes |
| Default daily cap | $10 / agent | $1000 / agent |

Activate Pro by setting the key you receive after purchase:

```bash
export TOLLBOOTH_LICENSE_KEY=your-key
```

Get a key: https://buy.stripe.com/14A9ATaI76K8gjo9JE1Nu0h

> License validation is an offline check today (honor-system v1). Server-side
> validation is on the roadmap.

## Live settlement (experimental)

The tollbooth includes an x402 hook so you can wire your own live settlement
verifier:

```python
from nano_empire_tollbooth import Tollbooth, TollboothConfig

booth = Tollbooth(TollboothConfig(paper_mode=False))

async def my_verifier(wallet, tx_signature, amount_usd):
    # verify a real on-chain or off-chain payment, return True/False
    return await check_payment(wallet, tx_signature, amount_usd)

booth.set_x402_verifier(my_verifier)
```

This ships the escrow lifecycle (lock, release, refund) and the verifier hook.
It does NOT include a hosted settlement backend. Connecting real funds is your
responsibility and is on the project roadmap. This is informational and not
financial advice.

## How metering works

1. Decorate any sync or async function with `@monetize(price_usd=...)`.
2. Each call writes a record to `logs/toll_ledger.jsonl` with a settlement hash.
3. In paper mode (default) nothing is charged. Set `paper_mode=False` plus your
   own verifier to move real funds.

## License

MIT
