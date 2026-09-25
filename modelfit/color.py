from __future__ import annotations

import os
import sys

NO_COLOR_ENVIRONMENT_VARIABLE = "NO_COLOR"
RESET_STYLE = "reset"
DEFAULT_CONFIDENCE_STYLE = "cyan"
QUADRANT_STYLES = ("bold",)
HEADING_STYLES = ("bold", "cyan")
LABEL_STYLES = ("dim",)
ACTION_STYLES = ("bold",)

_ANSI_CODES: dict[str, str] = {
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

CONFIDENCE_STYLE: dict[str, str] = {
    "high": "green",
    "medium": "yellow",
    "low": "red",
}


def enabled() -> bool:
    if _is_no_color_requested() is True:
        return False
    if bool(sys.stdout.isatty()) is True:
        return True
    return False


def c(text: str, *styles: str) -> str:
    if len(styles) == 0 or enabled() is False:
        return text
    prefix = "".join(_ANSI_CODES[style] for style in styles)
    return f"{prefix}{text}{_ANSI_CODES[RESET_STYLE]}"


def quadrant(name: str) -> str:
    return c(name, *QUADRANT_STYLES)


def confidence(level: str) -> str:
    return c(level, CONFIDENCE_STYLE.get(level, DEFAULT_CONFIDENCE_STYLE))


def heading(text: str) -> str:
    return c(text, *HEADING_STYLES)


def label(text: str) -> str:
    return c(text, *LABEL_STYLES)


def action(text: str) -> str:
    return c(text, *ACTION_STYLES)


def _is_no_color_requested() -> bool:
    no_color = os.environ.get(NO_COLOR_ENVIRONMENT_VARIABLE)
    if no_color is not None and len(no_color) > 0:
        return True
    return False
