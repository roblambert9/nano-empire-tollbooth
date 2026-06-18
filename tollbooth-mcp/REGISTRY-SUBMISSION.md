# Registry submission checklist

Verified locally on 2026-06-18. This file is a human checklist only; do not use
it as evidence that any registry submission has happened.

## Honest one-line description

Paper-mode MCP server that demonstrates an x402-style pay-per-call loop with
`nano-empire-tollbooth`: quote, simulated payment, receipt, and session ledger.
No real money moves.

## Repository and package fields

| Field | Value |
| --- | --- |
| Name | `tollbooth-mcp` |
| Repository | `https://github.com/roblambert9/nano-empire-tollbooth` |
| Package install | `pip install tollbooth-mcp` |
| Local run command | `tollbooth-mcp` |
| Transport | stdio |
| License | MIT |
| Category | Developer tools / payments / MCP demo |
| Auth required | No |
| Secrets required | No |
| Default mode | Paper mode; simulated payment only |

## Verified local commands

From the repository root:

```bash
python -m pytest tests/ -q
python -m pip install ./tollbooth-mcp[dev]
python -m pytest tollbooth-mcp/tests -q
docker build -t tollbooth-mcp:local ./tollbooth-mcp
```

From `tollbooth-mcp/`, run the stdio smoke check from the README to confirm:

```text
TOOLS=quote_toll,demo_paid_call,get_session_ledger,about_tollbooth
```

## Smithery

Current Smithery docs prefer URL-published MCP servers or local `.mcpb` bundles
for stdio servers. This project is a local stdio server, so the recommended
submission path is a bundle upload, not a live URL submission.

Manual steps:

1. Build the Docker image locally with the verified command above.
2. Prepare an MCPB bundle according to the current Smithery/Anthropic MCPB docs.
3. Publish manually with:

```bash
smithery mcp publish ./server.mcpb -n roblambert9/tollbooth-mcp
```

The included `smithery.yaml` remains valid local-run metadata for the legacy
Docker/stdio shape used by many Smithery examples:

```yaml
startCommand:
  type: stdio
  configSchema:
    type: object
    properties: {}
  commandFunction: |-
    (config) => ({ "command": "tollbooth-mcp", "args": [] })
build:
  dockerfile: Dockerfile
  dockerBuildPath: .
```

Validation performed:

```bash
npx --yes @smithery/cli --version
npx --yes @smithery/cli mcp publish --help
python scripts/local-validate-smithery-yaml.py
```

Do not run `smithery mcp publish` without Rob's explicit approval.

## mcp.so

Manual fields:

| Field | Value |
| --- | --- |
| Name | `tollbooth-mcp` |
| Description | Use the honest one-line description above. |
| Repository URL | `https://github.com/roblambert9/nano-empire-tollbooth` |
| Install command | `pip install tollbooth-mcp` |
| Run command | `tollbooth-mcp` |
| Transport | stdio |
| Tools | `quote_toll`, `demo_paid_call`, `get_session_ledger`, `about_tollbooth` |

Do not claim live payments, revenue, customers, or registry verification.

## Glama

Manual fields:

| Field | Value |
| --- | --- |
| Server name | `tollbooth-mcp` |
| Source | `https://github.com/roblambert9/nano-empire-tollbooth` |
| Description | Use the honest one-line description above. |
| Install | `pip install tollbooth-mcp` |
| Start command | `tollbooth-mcp` |
| Configuration | None required |

If Glama performs an automatic scan, verify that it detects exactly the four
tools listed above. If it cannot scan stdio, paste the tool list manually and
state that paper mode is the only default operating mode.
