"""Metric calculations for end-to-end validation."""

from __future__ import annotations

from difflib import SequenceMatcher


def bit_error_rate(expected: list[int], actual: list[int]) -> float:
    if not expected:
        return 0.0 if not actual else 1.0
    padded_actual = list(actual[: len(expected)])
    if len(padded_actual) < len(expected):
        padded_actual.extend([0] * (len(expected) - len(padded_actual)))
    errors = sum(1 for a, b in zip(expected, padded_actual) if a != b)
    return errors / len(expected)


def text_match_rate(expected: str, actual: str) -> float:
    if expected == actual:
        return 1.0
    if not expected:
        return 0.0 if actual else 1.0
    return SequenceMatcher(None, expected, actual).ratio()

