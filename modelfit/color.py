"""
Terminal color, plain ANSI -- no dependency for a handful of escape codes.

Decoration only: every string this module returns is identical content with
or without color, so nothing here can change what a test asserts on, and
nothing here is load-bearing for any of the tool's actual output. It's off
whenever stdout isn't a real terminal (pipes, redirects, `capsys` in tests)
or `NO_COLOR` is set, so scripts and CI stay exactly as before.
"""

from __future__ import annotations

import os
import sys

_CODES: dict[str, str] = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
}

# Confidence maps to conventional traffic-light semantics -- that one's a fair
# use of color. Quadrant name does NOT get its own color scale: an ordinal
# green->yellow->magenta->red "cost" mapping doesn't survive contact with
# normal terminal conventions (red reads as error/danger, not "priciest but
# legitimate"), and it isn't an intuitive ordinal scale to begin with.
CONFIDENCE_STYLE: dict[str, str] = {
    "high": "green",
    "medium": "yellow",
    "low": "red",
}


def enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def c(text: str, *styles: str) -> str:
    """Wrap `text` in the given style codes if color is on, else return it as-is."""
    if not styles or not enabled():
        return text
    prefix = "".join(_CODES[s] for s in styles)
    return f"{prefix}{text}{_CODES['reset']}"


def quadrant(name: str) -> str:
    """A quadrant name wherever it appears inline -- bold for identity, no hue,
    so it never implies an ordinal or error/danger reading it doesn't have."""
    return c(name, "bold")


def confidence(level: str) -> str:
    return c(level, CONFIDENCE_STYLE.get(level, "cyan"))


def heading(text: str) -> str:
    return c(text, "bold", "cyan")


def label(text: str) -> str:
    """A field label (START, WHY, ...) -- dim, so it recedes behind its value.
    The recommendation should be the loudest thing on screen, not its caption."""
    return c(text, "dim")


def action(text: str) -> str:
    """The one thing a user actually needs to read: what to run."""
    return c(text, "bold")
