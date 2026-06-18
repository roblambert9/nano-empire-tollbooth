"""Tests for tollbooth-mcp core logic (no MCP runtime required)."""
import pytest

from tollbooth_mcp import core


@pytest.fixture(autouse=True)
def fresh_session():
    core.reset_session()
    yield
    core.reset_session()


def test_quote_toll_shape():
    q = core.quote_toll()
    assert q["status_code"] == 402
    assert q["price_usd"] == core.DEMO_PRICE_USD
    assert q["payment_methods"] == ["x402"]
    assert "no real money" in q["note"]


def test_quote_toll_unique_nonces():
    assert core.quote_toll()["nonce"] != core.quote_toll()["nonce"]


@pytest.mark.asyncio
async def test_demo_paid_call_returns_result_and_receipt():
    out = await core.demo_paid_call(
        "Agents call each other to complete tasks. A tollbooth meters each "
        "request. Escrow locks on call and releases on success. Receipts prove work."
    )
    assert out["receipt"]["status"] == "released"
    assert out["receipt"]["amount_usd"] == core.DEMO_PRICE_USD
    assert "no real money" in out["receipt"]["note"]
    assert len(out["result"]) > 0
    assert out["session_total_usd"] == core.DEMO_PRICE_USD


@pytest.mark.asyncio
async def test_ledger_accumulates():
    await core.demo_paid_call("One sentence here. Another sentence there.")
    await core.demo_paid_call("More text to summarize. And a second sentence.")
    ledger = core.get_session_ledger()
    assert ledger["count"] == 2
    assert ledger["total_usd"] == round(2 * core.DEMO_PRICE_USD, 4)


def test_about_is_honest():
    about = core.about_tollbooth()
    assert "simulated" in about["this_server"]
    assert "No revenue is guaranteed" in about["honesty"]
    assert about["install"] == "pip install nano-empire-tollbooth"


def test_summarize_short_text_passthrough():
    assert core._summarize("Only one sentence.") == "Only one sentence."
