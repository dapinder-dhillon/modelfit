from __future__ import annotations

from dataclasses import dataclass

TIERS = ("small", "mid", "large")
MODEL_NAME_SEPARATOR = " or "
TIER_RANK: dict[str, int] = {"small": 1, "mid": 2, "large": 3}


@dataclass(frozen=True)
class Vendor:
    key: str
    label: str
    models: dict[str, str]


# model ids checked against each vendor's model docs on 2026-09-25; they go stale.
VENDORS: dict[str, Vendor] = {
    "anthropic": Vendor(
        key="anthropic",
        label="Anthropic",
        models={"small": "claude-haiku-4-5", "mid": "claude-sonnet-5", "large": "claude-opus-5-5"},
    ),
    "openai": Vendor(
        key="openai",
        label="OpenAI",
        models={"small": "gpt-6-luna", "mid": "gpt-6-sol", "large": "gpt-6-astra"},
    ),
}

# gpt-6-astra's reasoning effort starts at "low"; it has no "none".
UNSETTABLE: frozenset[tuple[str, str, str]] = frozenset({("openai", "large", "off")})


def chosen(vendor: str | None) -> list[Vendor]:
    if vendor is not None and len(vendor) > 0:
        return [VENDORS[vendor]]
    else:
        return list(VENDORS.values())


def names(tier: str, shown_vendors: list[Vendor]) -> str:
    if len(shown_vendors) == 1:
        return shown_vendors[0].models[tier]
    return MODEL_NAME_SEPARATOR.join(
        _model_id_with_label(vendor=vendor, tier=tier) for vendor in shown_vendors
    )


def fill(text: str, shown_vendors: list[Vendor]) -> str:
    return text.format(**_model_names_by_tier(shown_vendors=shown_vendors))


def _model_id_with_label(vendor: Vendor, tier: str) -> str:
    return f"{vendor.models[tier]} ({vendor.label})"


def _model_names_by_tier(shown_vendors: list[Vendor]) -> dict[str, str]:
    return {tier: names(tier=tier, shown_vendors=shown_vendors) for tier in TIERS}
