"""Digital modulation mappings and hard-decision demodulation."""

from __future__ import annotations

import math


INV_SQRT2 = 1.0 / math.sqrt(2.0)

QPSK_MAPPING: dict[tuple[int, int], complex] = {
    (0, 0): complex(INV_SQRT2, INV_SQRT2),
    (0, 1): complex(-INV_SQRT2, INV_SQRT2),
    (1, 1): complex(-INV_SQRT2, -INV_SQRT2),
    (1, 0): complex(INV_SQRT2, -INV_SQRT2),
}

QAM16_SCALE = math.sqrt(10.0)
QAM16_LEVELS: dict[tuple[int, int], float] = {
    (0, 0): -3.0 / QAM16_SCALE,
    (0, 1): -1.0 / QAM16_SCALE,
    (1, 1): 1.0 / QAM16_SCALE,
    (1, 0): 3.0 / QAM16_SCALE,
}


def bits_per_symbol(modulation: str) -> int:
    modulation = modulation.lower()
    if modulation == "bpsk":
        return 1
    if modulation == "qpsk":
        return 2
    if modulation in {"16qam", "16-qam", "qam16"}:
        return 4
    raise ValueError(f"unsupported modulation '{modulation}'")


def constellation(modulation: str) -> list[complex]:
    modulation = modulation.lower()
    if modulation == "bpsk":
        return [complex(1.0, 0.0), complex(-1.0, 0.0)]
    if modulation == "qpsk":
        return list(QPSK_MAPPING.values())
    if modulation in {"16qam", "16-qam", "qam16"}:
        return [complex(i_level, q_level) for i_level in QAM16_LEVELS.values() for q_level in QAM16_LEVELS.values()]
    raise ValueError(f"unsupported modulation '{modulation}'")


def qpsk_modulate(bits: list[int]) -> list[complex]:
    padded = list(bits)
    if len(padded) % 2:
        padded.append(0)

    symbols: list[complex] = []
    for i in range(0, len(padded), 2):
        pair = (padded[i] & 1, padded[i + 1] & 1)
        symbols.append(QPSK_MAPPING[pair])
    return symbols


def qpsk_demodulate(symbols: list[complex]) -> list[int]:
    bits: list[int] = []
    for symbol in symbols:
        if symbol.real >= 0 and symbol.imag >= 0:
            bits.extend([0, 0])
        elif symbol.real < 0 and symbol.imag >= 0:
            bits.extend([0, 1])
        elif symbol.real < 0 and symbol.imag < 0:
            bits.extend([1, 1])
        else:
            bits.extend([1, 0])
    return bits


def bpsk_modulate(bits: list[int]) -> list[complex]:
    return [complex(1.0 if (bit & 1) == 0 else -1.0, 0.0) for bit in bits]


def bpsk_demodulate(symbols: list[complex]) -> list[int]:
    return [0 if symbol.real >= 0 else 1 for symbol in symbols]


def qam16_modulate(bits: list[int]) -> list[complex]:
    padded = [bit & 1 for bit in bits]
    while len(padded) % 4:
        padded.append(0)

    symbols: list[complex] = []
    for i in range(0, len(padded), 4):
        i_bits = (padded[i], padded[i + 1])
        q_bits = (padded[i + 2], padded[i + 3])
        symbols.append(complex(QAM16_LEVELS[i_bits], QAM16_LEVELS[q_bits]))
    return symbols


def _nearest_level_bits(value: float) -> list[int]:
    pair, _ = min(QAM16_LEVELS.items(), key=lambda item: abs(value - item[1]))
    return [pair[0], pair[1]]


def qam16_demodulate(symbols: list[complex]) -> list[int]:
    bits: list[int] = []
    for symbol in symbols:
        bits.extend(_nearest_level_bits(symbol.real))
        bits.extend(_nearest_level_bits(symbol.imag))
    return bits


def modulate(bits: list[int], modulation: str) -> list[complex]:
    modulation = modulation.lower()
    if modulation == "bpsk":
        return bpsk_modulate(bits)
    if modulation == "qpsk":
        return qpsk_modulate(bits)
    if modulation in {"16qam", "16-qam", "qam16"}:
        return qam16_modulate(bits)
    raise ValueError(f"unsupported modulation '{modulation}', supported: bpsk, qpsk, 16qam")


def demodulate(symbols: list[complex], modulation: str) -> list[int]:
    modulation = modulation.lower()
    if modulation == "bpsk":
        return bpsk_demodulate(symbols)
    if modulation == "qpsk":
        return qpsk_demodulate(symbols)
    if modulation in {"16qam", "16-qam", "qam16"}:
        return qam16_demodulate(symbols)
    raise ValueError(f"unsupported modulation '{modulation}', supported: bpsk, qpsk, 16qam")
