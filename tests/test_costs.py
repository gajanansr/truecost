"""The billing model. Every dollar figure published comes from here."""

from __future__ import annotations

from truecost.core import costs


def test_cache_multipliers_are_the_documented_rates():
    """Collapsing the two write classes understates write cost by 60%."""
    assert costs.CACHE_READ_MULTIPLIER == 0.1
    assert costs.CACHE_WRITE_5M_MULTIPLIER == 1.25
    assert costs.CACHE_WRITE_1H_MULTIPLIER == 2.0


def test_context_window_marker_is_stripped_for_price_lookup():
    """Claude Code appends e.g. "[1m]"; a naive lookup misses every price."""
    assert costs.normalize_model("claude-opus-5[1m]")[0] == "claude-opus-5"


def test_synthetic_messages_are_free_and_are_not_turns():
    assert costs.is_synthetic("<synthetic>")
    assert not costs.is_synthetic("claude-sonnet-5")


def test_a_cache_read_is_an_order_of_magnitude_cheaper_than_a_write():
    """The whole reason an injected block bills at a multiple of its size."""
    assert costs.CACHE_WRITE_1H_MULTIPLIER / costs.CACHE_READ_MULTIPLIER == 20.0
