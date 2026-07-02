"""Frame-start detection with preamble correlation."""

from __future__ import annotations

import math


def normalized_correlation(segment: list[complex], reference: list[complex]) -> float:
    if len(segment) != len(reference) or not segment:
        return 0.0

    numerator = abs(sum(sample * ref.conjugate() for sample, ref in zip(segment, reference)))
    segment_energy = sum(abs(sample) ** 2 for sample in segment)
    reference_energy = sum(abs(ref) ** 2 for ref in reference)
    if segment_energy <= 0 or reference_energy <= 0:
        return 0.0
    return numerator / math.sqrt(segment_energy * reference_energy)


def synchronize(
    received_symbols: list[complex],
    preamble: list[complex] | None = None,
    preamble_symbols: list[complex] | None = None,
) -> int:
    """Return the most likely frame-start symbol index.

    Thin wrapper over :func:`find_frame_start` that accepts either ``preamble``
    or ``preamble_symbols`` and returns just the peak index.
    """
    reference = preamble if preamble is not None else preamble_symbols
    if reference is None:
        raise ValueError("a preamble reference is required")
    index, _scores = find_frame_start(
        [complex(sample) for sample in received_symbols],
        [complex(sample) for sample in reference],
    )
    return index


def find_frame_start(
    received_symbols: list[complex],
    preamble_symbols: list[complex],
) -> tuple[int, list[float]]:
    """Return the most likely frame start symbol index and all correlation scores."""
    width = len(preamble_symbols)
    if width == 0 or len(received_symbols) < width:
        return 0, []

    scores: list[float] = []
    best_index = 0
    best_score = -1.0
    for start in range(0, len(received_symbols) - width + 1):
        score = normalized_correlation(received_symbols[start : start + width], preamble_symbols)
        scores.append(score)
        if score > best_score:
            best_score = score
            best_index = start
    return best_index, scores

