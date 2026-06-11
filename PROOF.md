# Proof: the tollbooth rails work end-to-end

This is a real, reproducible run of the x402 pay-per-call loop, metered through
the live `nano-empire-tollbooth` package. It is informational, not financial advice.

## What was proven

An external agent called a paid endpoint, was challenged with HTTP 402, paid the
toll, retried with proof, and received the result. The tollbooth locked escrow,
released it on success, and wrote two ledger lines. One cent was metered.

## The run (2026-06-09, mock verifier — proves the protocol, no real money)

```
$ DOGFOOD_VERIFIER=mock uvicorn paid_endpoint:app --port 8099 &
$ python buyer_agent.py

Step 1: call with no payment
  -> HTTP 402
  challenge: price $0.01 USD to demo-receiving-wallet via ['x402']
Step 2: pay the toll, retry with X-Payment proof
  -> HTTP 200
  result: Autonomous agents increasingly call each other to complete tasks. A
          per-call tollbooth meters each request, locks escrow, and settles on success.
  RECEIPT: earned $0.01 | status released | hash 4c56c4fd0d598e07 | payer agent-7f3a
  booth total earned this session: $0.0100
```

## Ledger (toll_ledger.jsonl)

```json
{"status": "escrow_locked", "amount_usd": 0.01, "payer_wallet": "agent-7f3a", "tx_signature": "valid-paper-token", "task_id": "text.summarize:...:a49b26a5"}
{"status": "released",      "amount_usd": 0.01, "payer_wallet": "agent-7f3a", "settled_at": "2026-06-10T00:58:29+00:00", "task_id": "text.summarize:...:a49b26a5"}
```

Escrow locked on payment, released on successful delivery. The two-phase
settlement is what separates a real payment rail from a counter.

## Reproduce it yourself

```bash
pip install fastapi uvicorn nano-empire-tollbooth
cd dogfood
DOGFOOD_VERIFIER=mock python -m uvicorn paid_endpoint:app --port 8099 &
python buyer_agent.py
```

## From proof to first real cent

The mock verifier proves the *protocol*. To take real currency, swap one env var
to an on-chain verifier (`DOGFOOD_VERIFIER=onchain`, `DOGFOOD_FACILITATOR_URL=...`)
pointed at a funded stablecoin receiving wallet. No application code changes — the
endpoint already calls the verifier. Stripe's ~50¢ floor is why cent-level metering
settles on-chain; the $19/mo Tollbooth Pro subscription is the parallel fiat path.

Tests: `33 passed`. Package: https://pypi.org/project/nano-empire-tollbooth/

## Proof 2: batch-netting settlement (2026-06-11)

Card rails can't clear a cent. `tollbooth settle` nets released tolls into one
charge-sized settlement — sub-cent pricing on fiat, no wallet:

```
$ # ledger: 50 released 1-cent calls
$ tollbooth --ledger toll_ledger.jsonl settle
SETTLED settle-094d8081c536: 50 call(s) netted to $0.50 (paper mode)

$ tollbooth --ledger toll_ledger.jsonl settle      # idempotent
no settlement: nothing to settle (0 pending call(s), net $0.00)

$ tollbooth --ledger toll_ledger.jsonl settle --live
no settlement: live settlement requires operator wiring ... fails closed by design
```

Reproduce: write any JSONL ledger of released tolls and run the commands above.
Paper mode simulates; the SDK never moves real money itself.

## Proof 3: rail adapters (2026-06-11)

One decorator, every settlement rail. Stubs fail fast — no pretend support:

```
>>> @monetize(price_usd=0.01, rail="stripe")
... def summarize(text): ...
>>> summarize.tollbooth_rail
'stripe'   # settles via batch netting: `tollbooth settle`

>>> @monetize(price_usd=0.01, rail="ap4m")
NotImplementedError: rail 'ap4m' is a stub: Mastercard has not published an
integration spec we can implement against ... no pretend support
```
