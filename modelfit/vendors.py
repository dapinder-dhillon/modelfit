"""
Vendors: the same two dials, spelled by two different companies.

Nothing in a task's wording says "Anthropic" or "OpenAI", so the advisor's
verdict is vendor-neutral by construction: a capability *tier* (small / mid /
large) plus an *effort* (off / low / high). This table only translates a tier
into a model id you can paste into code. `advise` shows every vendor by
default, because the advice holds for either; `advise --vendor` narrows it.

Two honesty notes, in the same spirit as `providers.PRICING`:

* Model ids go stale. These were checked against each vendor's model docs on
  2026-09-25 -- re-check them before trusting the table.
* "Same tier" across vendors is a rough starting guess, not a measured
  equivalence. Whether gpt-6-sol at low effort beats claude-sonnet-5 at high
  on YOUR tasks is exactly the question `modelfit run` exists to answer.
"""

from __future__ import annotations

from dataclasses import dataclass

TIERS = ("small", "mid", "large")

# The mock's pass-probability model (providers._pass_probability) is written in
# capability tiers, not model names -- this is the bridge.
TIER_RANK: dict[str, int] = {"small": 1, "mid": 2, "large": 3}


@dataclass(frozen=True)
class Vendor:
    key: str  # the --vendor value
    label: str  # how it's printed
    models: dict[str, str]  # tier -> model id


VENDORS: dict[str, Vendor] = {
    "anthropic": Vendor(
        "anthropic",
        "Anthropic",
        {"small": "claude-haiku-4-5", "mid": "claude-sonnet-5", "large": "claude-opus-5-5"},
    ),
    "openai": Vendor(
        "openai",
        "OpenAI",
        {"small": "gpt-6-luna", "mid": "gpt-6-sol", "large": "gpt-6-astra"},
    ),
}

# (vendor, tier, effort) combinations the vendor's API cannot express.
# gpt-6-astra's reasoning effort starts at "low" -- it has no "none" -- so no
# plan may put the large tier at effort "off". tests/test_advisor.py holds
# every plan to this.
UNSETTABLE: frozenset[tuple[str, str, str]] = frozenset({("openai", "large", "off")})


def chosen(vendor: str | None) -> list[Vendor]:
    """The vendors to show: the one asked for, or all of them."""
    return [VENDORS[vendor]] if vendor else list(VENDORS.values())


def names(tier: str, vendors: list[Vendor]) -> str:
    """A tier's model id(s) as prose: `claude-sonnet-5` for one vendor,
    `claude-sonnet-5 (Anthropic) or gpt-6-sol (OpenAI)` for several."""
    if len(vendors) == 1:
        return vendors[0].models[tier]
    return " or ".join(f"{v.models[tier]} ({v.label})" for v in vendors)


def fill(text: str, vendors: list[Vendor]) -> str:
    """Put model ids into a plan's text. Plans name a tier as `{large}` so the
    advisor never needs to know which vendor you use."""
    return text.format(**{tier: names(tier, vendors) for tier in TIERS})
