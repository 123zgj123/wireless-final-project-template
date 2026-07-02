"""Wireless channel models, equalization, and frame timing offset."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random

from .modulation import constellation


def average_symbol_power(symbols: list[complex]) -> float:
    if not symbols:
        return 0.0
    return sum(abs(symbol) ** 2 for symbol in symbols) / len(symbols)


def add_awgn(symbols: list[complex], snr_db: float, seed: int) -> list[complex]:
    """Add complex AWGN using SNR = average symbol power / noise power."""
    symbols = [complex(symbol) for symbol in symbols]
    if not symbols:
        return []

    rng = random.Random(seed)
    signal_power = average_symbol_power(symbols)
    snr_linear = 10.0 ** (snr_db / 10.0)
    noise_power = signal_power / snr_linear if snr_linear > 0 else signal_power
    sigma = math.sqrt(noise_power / 2.0)

    return [
        complex(symbol.real + rng.gauss(0.0, sigma), symbol.imag + rng.gauss(0.0, sigma))
        for symbol in symbols
    ]


@dataclass(frozen=True)
class ChannelResult:
    symbols: list[complex]
    fading_coefficient: complex
    noise_power: float
    equalizer: str


def _noise_power_for(symbols: list[complex], snr_db: float) -> float:
    signal_power = average_symbol_power(symbols)
    snr_linear = 10.0 ** (snr_db / 10.0)
    return signal_power / snr_linear if snr_linear > 0 else signal_power


def _complex_gaussian(rng: random.Random, sigma: float = 1.0) -> complex:
    return complex(rng.gauss(0.0, sigma), rng.gauss(0.0, sigma))


def _flat_fading_coefficient(channel: str, rng: random.Random, k_factor_db: float = 6.0) -> complex:
    if channel == "awgn":
        return complex(1.0, 0.0)
    if channel == "rayleigh":
        return _complex_gaussian(rng, 1.0 / math.sqrt(2.0))
    if channel == "rician":
        k_linear = 10.0 ** (k_factor_db / 10.0)
        los = math.sqrt(k_linear / (k_linear + 1.0))
        scatter = math.sqrt(1.0 / (k_linear + 1.0)) * _complex_gaussian(rng, 1.0 / math.sqrt(2.0))
        return complex(los, 0.0) + scatter
    raise ValueError(f"unsupported channel '{channel}', supported: awgn, rayleigh, rician")


def apply_channel(
    symbols: list[complex],
    snr_db: float,
    seed: int,
    channel: str = "awgn",
    equalizer: str = "zf",
) -> ChannelResult:
    """Apply AWGN or flat fading, then equalize with known channel state.

    This intentionally models a single flat fading tap so the receiver-side
    equalization remains compact and explainable for a course project.
    """
    channel = channel.lower()
    equalizer = equalizer.lower()
    if equalizer not in {"none", "zf", "mmse"}:
        raise ValueError("unsupported equalizer, supported: none, zf, mmse")
    if not symbols:
        return ChannelResult([], complex(1.0, 0.0), 0.0, equalizer)

    rng = random.Random(seed)
    h = _flat_fading_coefficient(channel, rng)
    faded = [h * symbol for symbol in symbols]
    noise_power = _noise_power_for(faded, snr_db)
    sigma = math.sqrt(noise_power / 2.0)
    noisy = [symbol + _complex_gaussian(rng, sigma) for symbol in faded]

    if channel == "awgn" or equalizer == "none":
        return ChannelResult(noisy, h, noise_power, equalizer)

    h_power = abs(h) ** 2
    if h_power <= 1e-12:
        return ChannelResult(noisy, h, noise_power, equalizer)

    if equalizer == "zf":
        equalized = [sample / h for sample in noisy]
    else:
        signal_power = max(average_symbol_power(symbols), 1e-12)
        weight = h.conjugate() / (h_power + noise_power / signal_power)
        equalized = [weight * sample for sample in noisy]
    return ChannelResult(equalized, h, noise_power, equalizer)


def add_random_symbol_offset(
    symbols: list[complex],
    max_offset_symbols: int,
    seed: int,
    offset_symbols: int | None = None,
    modulation: str = "qpsk",
) -> tuple[list[complex], int]:
    if max_offset_symbols < 0:
        raise ValueError("max_offset_symbols must be non-negative")

    rng = random.Random(seed)
    if offset_symbols is None:
        offset_symbols = rng.randint(0, max_offset_symbols)
    if offset_symbols < 0:
        raise ValueError("offset_symbols must be non-negative")

    choices = constellation(modulation)
    prefix = [rng.choice(choices) for _ in range(offset_symbols)]
    return prefix + symbols, offset_symbols
