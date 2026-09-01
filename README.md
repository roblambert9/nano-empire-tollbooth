# nano-empire-tollbooth

Monetize any Python function with one decorator. Paper-mode metering is free. Live x402 settlement is optional and off until you wire a verifier.

```python
from nano_empire_tollbooth import monetize

@monetize(price_usd=0.01)
def summarize(text: str) -> str:
    return my_llm(text)
```

Every call is metered and written to a local JSONL ledger with a settlement hash. Paper mode does not charge. It nags after 100 calls. It does not block.

Built in Ottawa by [Nano Empire AI](https://nanoempireai.com). MIT license.

## Install

```bash
pip install nano-empire-tollbooth
```

Python 3.9+. One dependency (pydantic).

```bash
tollbooth status
tollbooth report
tollbooth verify
```

## What this is

A decorator and a local ledger for agent-speed metering. Use it when a human Stripe Customer object is the wrong interface — when the caller is software.

## What this is not

Not a hosted payment processor. Not a subscription system. Not financial advice. Connecting real funds is your responsibility. Mainnet is a flip you make after you have a verifier.

## Free vs Pro

| | Free | Pro ($19/mo) |
|---|---|---|
| Metered calls | Unlimited (paper mode) | Unlimited (paper mode) |
| Local JSONL ledger | Yes | Yes |
| `report` and `verify` | Yes | Yes |
| Upgrade prompt | After 100 calls | Suppressed |
| `tollbooth export` | No | Yes |
| Default daily cap | $10 / agent | $1000 / agent |

**Pro is built and tested. It is not purchasable yet.** There is no buy link on purpose. Watch this repo.

```bash
export TOLLBOOTH_LICENSE_KEY=your-key
```

License check is offline: Ed25519 signature + expiry, verified locally. No phone-home.

## Live settlement (experimental)

```python
from nano_empire_tollbooth import Tollbooth, TollboothConfig

booth = Tollbooth(TollboothConfig(paper_mode=False))

async def my_verifier(wallet, tx_signature, amount_usd):
    return await check_payment(wallet, tx_signature, amount_usd)

booth.set_x402_verifier(my_verifier)
```

Escrow lifecycle (lock, release, refund) ships. A hosted settlement backend does not.

## Human products (buy these today)

If you want Nano Empire to do the thinking:

- **MCP Tool Metering Readiness Audit — $99**  
  Metering map, price shape, paper-mode demo against your endpoint, copy-paste plan, risk notes.  
  [Book the audit](https://buy.stripe.com/28EcN61rC9Dh6if1NCfAc01) · [What you get](https://nanoempireai.com/audit-offer.html)

- **LandTrace report — $29**  
  Year-over-year physical change of a land parcel from satellite embeddings.  
  [Samples](https://nanoempireai.com/landtrace/)

- **RFP compliance matrix — from $149**  
  Every shall/must/will (and French doit/devra) extracted into a response-ready matrix. First public tender free.  
  Email rob@nanoempireai.com

## Hosted parser

Same rails, hosted:

`POST https://nanoempireai.com/api/v1/parse`  
OpenAPI: https://nanoempireai.com/openapi.json  
Free 5/day · $0.005 basic · $0.05 premium

## Links

- Site: https://nanoempireai.com
- Tollbooth division: https://nanoempireai.com/tollbooth/
- Simulator: https://nanoempireai.com/simulator/
- Contact: rob@nanoempireai.com

## License

MIT
