# tollbooth-mcp

Watch agents simulate pay-per-call metering inside your own AI.

An MCP server that demonstrates the full x402 pay-per-call loop in **paper mode**:
your assistant asks for a quote, gets an HTTP-402-style challenge, pays a simulated
toll, and receives the result with a receipt record from the live
[nano-empire-tollbooth](https://pypi.org/project/nano-empire-tollbooth/) package
code path. **No real money moves.**

## Install

```bash
pip install tollbooth-mcp
```

For local development from this repository:

```bash
python -m pip install ./tollbooth-mcp[dev]
python -m pytest tollbooth-mcp/tests -q
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

## Verified local smoke checks

From the repository root:

```bash
python -m pytest tests/ -q
python -m pip install ./tollbooth-mcp[dev]
python -m pytest tollbooth-mcp/tests -q
docker build -t tollbooth-mcp:local ./tollbooth-mcp
```

From `tollbooth-mcp/`, this Python MCP-client smoke check starts the packaged
stdio server, lists tools, and runs a demo metered call:

```bash
python - <<'PY'
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(
        command="python",
        args=["-m", "tollbooth_mcp.server"],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("TOOLS=" + ",".join(t.name for t in tools.tools))
            result = await session.call_tool(
                "demo_paid_call",
                {"text": "Agents call tools. Tollbooth meters requests. Paper mode proves the loop."},
            )
            print(result.content[0].text)

asyncio.run(main())
PY
```

To smoke test the Docker image instead, change the `StdioServerParameters` line
to:

```python
params = StdioServerParameters(
    command="docker",
    args=["run", "-i", "--rm", "tollbooth-mcp:local"],
)
```

Expected tool list:

```text
TOOLS=quote_toll,demo_paid_call,get_session_ledger,about_tollbooth
```

## Tools

| Tool | What it does |
|---|---|
| `quote_toll` | Returns the x402 payment challenge an agent would receive (402, price, nonce) |
| `demo_paid_call` | Runs a real metered function through paper-mode tollbooth code and returns a receipt record |
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

## Registry submission

See `REGISTRY-SUBMISSION.md` for the approval-gated Smithery, mcp.so, and Glama
submission checklist. The checklist is not proof of submission; Rob must approve
and perform any registry submission manually.

*Paper mode is a simulation. No revenue is guaranteed; this is a metering SDK,
not an income product. No live payments are enabled by this MCP server.* MIT licensed.
