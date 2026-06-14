# Dogfood paid endpoint

A real, runnable x402-gated pay-per-call endpoint metered through the live
`nano-empire-tollbooth`. Proves the full loop: an agent is challenged with
HTTP 402, pays, retries with proof, and receives the result. Each call earns
a 1 cent toll and writes a settlement line to the ledger.

This is informational and not financial advice.

## Run the loop locally (proves the protocol, no real money)

    pip install fastapi uvicorn nano-empire-tollbooth
    DOGFOOD_VERIFIER=mock python -m uvicorn paid_endpoint:app --port 8099 &
    python buyer_agent.py

Expected: Step 1 returns 402, Step 2 returns 200 with a receipt, and
`toll_ledger.jsonl` shows an escrow_locked then released record.

## Earn the first REAL cent (mainnet checklist)

The local run uses a mock verifier. To take real currency from a stranger's
agent, three things are required. None of them are code we can fake:

1. Receiving wallet
   - A funded stablecoin receiving address (for example USDC on Base or Solana).
   - Set DOGFOOD_PAY_TO to that address.

2. Real on-chain verifier
   - Set DOGFOOD_VERIFIER=onchain and DOGFOOD_FACILITATOR_URL to an x402
     facilitator that verifies a stablecoin transfer to DOGFOOD_PAY_TO and
     returns {"verified": true}.
   - The endpoint already calls it in `_verify`. No code change needed.

3. Deploy + a real caller
   - Deploy paid_endpoint.py behind api.nanoempireai.com (nginx is already
     serving that host; add a reverse-proxy location to the uvicorn process).
   - Publish the endpoint URL where agent developers will find it (the blog
     posts and simulator already explain the model and can link to it).
   - The first external agent that pays earns the first real cent.

## Why this is the honest path

Stripe cannot charge 1 cent (its floor is about 50 cents), so cent-level
metering has to settle on-chain. A flat Tollbooth Pro subscription ($19/mo for
export + higher caps + support) is the planned parallel fiat path, but it is in
private setup and not yet purchasable — no live checkout link until the issuance
webhook is wired.

## Files
- paid_endpoint.py : the x402-gated, tollbooth-metered FastAPI service
- buyer_agent.py   : an external agent that completes the pay-per-call loop
