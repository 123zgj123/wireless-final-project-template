"""UTF-8 source coding utilities."""

from __future__ import annotations


def bytes_to_bits(data: bytes) -> list[int]:
    """Convert bytes to a MSB-first bit list."""
    bits: list[int] = []
    for byte in data:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)
    return bits


def bits_to_bytes(bits: list[int]) -> bytes:
    """Convert a MSB-first bit list to bytes.

    The input is padded with zero bits if its length is not a multiple of 8.
    In the receiver the original payload length is applied before this step,
    so padding only protects abnormal or low-SNR cases from crashing.
    """
    padded = list(bits)
    remainder = len(padded) % 8
    if remainder:
        padded.extend([0] * (8 - remainder))

    out = bytearray()
    for i in range(0, len(padded), 8):
        value = 0
        for bit in padded[i : i + 8]:
            value = (value << 1) | (bit & 1)
        out.append(value)
    return bytes(out)


def text_to_bits(text: str) -> list[int]:
    return bytes_to_bits(text.encode("utf-8"))


def bits_to_text(bits: list[int]) -> str:
    data = bits_to_bytes(bits)
    return data.decode("utf-8", errors="replace")

