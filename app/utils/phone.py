"""Utility helpers for phone number formatting and validation."""

from typing import Final

ALLOWED_PREFIXES: Final[tuple[str, ...]] = ("00",)


def normalize_phone_number(raw_number: str) -> str:
    """Remove non-digit characters and strip known international prefixes."""

    digits = "".join(ch for ch in raw_number if ch.isdigit())

    for prefix in ALLOWED_PREFIXES:
        if digits.startswith(prefix):
            digits = digits[len(prefix) :]
            break

    return digits




