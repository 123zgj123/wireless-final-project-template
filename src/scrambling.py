"""Reversible PN-sequence scrambling."""

from __future__ import annotations


DEFAULT_SCRAMBLER_SEED = 0xACE1


def pn_sequence(length: int, seed: int = DEFAULT_SCRAMBLER_SEED) -> list[int]:
    """Generate a deterministic binary PN sequence with a 16-bit LFSR."""
    if length < 0:
        raise ValueError("length must be non-negative")

    state = seed & 0xFFFF
    if state == 0:
        state = DEFAULT_SCRAMBLER_SEED

    seq: list[int] = []
    for _ in range(length):
        out = state & 1
        # Primitive-ish taps for a compact deterministic scrambler.
        feedback = ((state >> 0) ^ (state >> 2) ^ (state >> 3) ^ (state >> 5)) & 1
        state = (state >> 1) | (feedback << 15)
        seq.append(out)
    return seq


def xor_bits(bits: list[int], mask: list[int]) -> list[int]:
    if len(bits) != len(mask):
        raise ValueError("bits and mask must have the same length")
    return [(bit ^ mask_bit) & 1 for bit, mask_bit in zip(bits, mask)]


def scramble(bits: list[int], seed: int = DEFAULT_SCRAMBLER_SEED) -> list[int]:
    return xor_bits(bits, pn_sequence(len(bits), seed))


def descramble(bits: list[int], seed: int = DEFAULT_SCRAMBLER_SEED) -> list[int]:
    return scramble(bits, seed)

