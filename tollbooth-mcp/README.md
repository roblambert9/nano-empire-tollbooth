# tollbooth-mcp

Watch agents pay per call — inside your own AI.

An MCP server that demonstrates the full x402 pay-per-call loop in **paper mode**:
your assistant asks for a quote, gets an HTTP-402-style challenge, pays a simulated
toll, and receives the result with a genuine receipt from the live
[nano-empire-tollbooth](https://pypi.org/project/nano-empire-tollbooth/) escrow
lifecycle. **No real money moves.**

## Install

```bash
pip install tollbooth-mcp
```

### Claude Desktop / Claude Code

```json
{
  "mcpServers": {
    "tollbooth": { "command": "tollbooth-mcp" }
  }
}
```

### Cursor

```json
{ "mcp": { "servers": { "tollbooth": { "command": "tollbooth-mcp" } } } }
```

Then ask your assistant: *"Use the tollbooth to run a paid call and show me the receipt."*

## Tools

| Tool | What it does |
|---|---|
| `quote_toll` | Returns the x402 payment challenge an agent would receive (402, price, nonce) |
| `demo_paid_call` | Runs a real metered function: escrow lock → work → release → receipt |
| `get_session_ledger` | Every paper-mode receipt issued this session, with running total |
| `about_tollbooth` | What the real package does and where to learn more |

## Monetize your own functions

The real thing is one decorator:

```python
from nano_empire_tollbooth import monetize

@monetize(price_usd=0.01)
def summarize(text: str) -> str:
    return my_llm(text)
```

- Quickstart: https://neuralempireai.com/docs/quickstart.html
- Live simulator: https://neuralempireai.com/simulator/
- Source: https://github.com/roblambert9/nano-empire-tollbooth

*Paper mode is a simulation. No revenue is guaranteed; this is a metering SDK,
not an income product.* MIT licensed.
