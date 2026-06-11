"""Settlement rail adapters — one decorator, every rail.

Four serious agent-payment protocols launched within 14 months (Stripe metered
billing, Coinbase x402, Google AP2, Mastercard AP4M). Sellers shouldn't bet
their integration on which rail wins: meter once with @monetize, pick the rail
at the edge. The registry below is the seam where settlement plugs in.

Honesty rules: a rail is "available" only when the SDK genuinely supports its
path today; anything else is a "stub" that fails fast with a reason.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RailAdapter:
    name: str
    status: str  # "available" | "stub"
    description: str
    settlement: str  # how money actually settles on this rail


RAILS: dict[str, RailAdapter] = {
    "paper": RailAdapter(
        name="paper",
        status="available",
        description="Simulated settlement (default). Full metering, escrow "
                    "lifecycle, and ledger; no real money moves.",
        settlement="Simulated: receipts and ledger lines only.",
    ),
    "stripe": RailAdapter(
        name="stripe",
        status="available",
        description="Fiat via the operator's own Stripe account.",
        settlement="Batch netting: meter cent-level calls, then `tollbooth "
                    "settle` nets released tolls into one charge-sized batch "
                    "(default minimum $0.50) the operator bills via Stripe.",
    ),
    "x402": RailAdapter(
        name="x402",
        status="available",
        description="Per-call stablecoin settlement via the x402 pattern "
                    "(HTTP 402 challenge -> payment proof -> receipt).",
        settlement="Operator wires a verifier with booth.set_x402_verifier() "
                    "against their facilitator; the SDK never holds funds.",
    ),
    "ap4m": RailAdapter(
        name="ap4m",
        status="stub",
        description="Mastercard Agent Pay for Machines (launched 2026-06-10).",
        settlement="Stub: Mastercard has not published an integration spec we "
                    "can implement against. This rail fails fast until it "
                    "exists — no pretend support.",
    ),
}


def get_rail(name: str) -> RailAdapter:
    """Return the adapter for `name`, or raise listing the known rails."""
    try:
        return RAILS[name]
    except KeyError:
        known = ", ".join(sorted(RAILS))
        raise ValueError(f"unknown rail {name!r}; known rails: {known}") from None


def validate_rail_for_decoration(name: str) -> RailAdapter:
    """Fail-fast check used by @monetize at decoration time."""
    rail = get_rail(name)
    if rail.status == "stub":
        raise NotImplementedError(
            f"rail {rail.name!r} is a stub: {rail.settlement} "
            "(Mastercard AP4M adapter lands when the public spec does)")
    return rail
