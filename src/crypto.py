"""Compatibility wrapper for reversible payload scrambling."""

from .scrambling import DEFAULT_SCRAMBLER_SEED, descramble, pn_sequence, scramble, xor_bits

__all__ = ["DEFAULT_SCRAMBLER_SEED", "descramble", "pn_sequence", "scramble", "xor_bits"]

