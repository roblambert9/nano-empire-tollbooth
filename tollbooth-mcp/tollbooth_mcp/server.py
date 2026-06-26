"""tollbooth-mcp — MCP server exposing the paper-mode pay-per-call demo.

Run: tollbooth-mcp   (stdio transport; add to Claude Desktop / Cursor config)
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import core

mcp = FastMCP(
    "tollbooth",
    instructions=(
        "Demonstrates agent pay-per-call with nano-empire-tollbooth in PAPER MODE: "
        "402 challenge, simulated payment, real tollbooth lifecycle, receipt record. "
        "No real money moves. Start with quote_toll, then demo_paid_call."
    ),
)

mcp.tool()(core.quote_toll)
mcp.tool()(core.demo_paid_call)
mcp.tool()(core.get_session_ledger)
mcp.tool()(core.about_tollbooth)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
