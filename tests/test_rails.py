"""Rail adapters: one decorator, every settlement rail.

KR1.1: @monetize(rail=...) validates against a registry of settlement rails.
Paper/Stripe/x402 are available; AP4M is an honest stub that fails fast until
Mastercard publishes the spec.
"""
import pytest

from nano_empire_tollbooth import monetize
from nano_empire_tollbooth.rails import RAILS, RailAdapter, get_rail


def test_registry_contains_the_four_rails():
    assert set(RAILS) == {"paper", "stripe", "x402", "ap4m"}


def test_available_rails_have_settlement_guidance():
    for name in ("paper", "stripe", "x402"):
        rail = get_rail(name)
        assert rail.status == "available"
        assert rail.settlement  # human-readable: how money actually settles
    assert "settle" in get_rail("stripe").settlement  # batch-netting path


def test_ap4m_is_an_honest_stub():
    rail = get_rail("ap4m")
    assert rail.status == "stub"
    assert "spec" in rail.settlement.lower()


def test_unknown_rail_raises_with_known_names():
    with pytest.raises(ValueError) as e:
        get_rail("visa")
    assert "paper" in str(e.value) and "x402" in str(e.value)


def test_monetize_accepts_rail_and_tags_wrapper():
    @monetize(price_usd=0.01, rail="stripe")
    def fn(x):
        return x

    assert fn.tollbooth_rail == "stripe"


def test_monetize_default_rail_is_paper():
    @monetize(price_usd=0.01)
    def fn(x):
        return x

    assert fn.tollbooth_rail == "paper"


def test_monetize_rejects_stub_rail_at_decoration():
    with pytest.raises(NotImplementedError) as e:
        @monetize(price_usd=0.01, rail="ap4m")
        def fn(x):
            return x
    assert "Mastercard" in str(e.value)


def test_monetize_rejects_unknown_rail_at_decoration():
    with pytest.raises(ValueError):
        @monetize(price_usd=0.01, rail="dogecoin")
        def fn(x):
            return x
