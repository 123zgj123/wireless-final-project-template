"""End-to-end baseband simulation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path

from .channel import add_random_symbol_offset, apply_channel
from .framing import PREAMBLE, build_frame, crc16_for_payload_bits, parse_frame_bits
from .metrics import bit_error_rate, text_match_rate
from .modulation import bits_per_symbol, demodulate, modulate
from .plots import save_ber_curve, save_constellation, save_sync_peak
from .scrambling import DEFAULT_SCRAMBLER_SEED, descramble, scramble
from .source_codec import bits_to_text, text_to_bits
from .synchronization import find_frame_start


SUPPORTED_MODULATIONS = {"bpsk", "qpsk", "16qam"}
SUPPORTED_CHANNELS = {"awgn", "rayleigh", "rician"}
MAX_SYNC_OFFSET_SYMBOLS = 128


@dataclass(frozen=True)
class LinkResult:
    received_text: str
    metrics: dict[str, object]
    received_payload_bits: list[int]
    transmitted_payload_bits: list[int]
    received_symbols: list[complex]
    sync_scores: list[float]
    ber_curve: list[tuple[float, float]]


def run_link(
    input_text: str,
    snr_db: float,
    seed: int,
    modulation: str = "qpsk",
    channel: str = "awgn",
    equalizer: str = "zf",
    results_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    make_plots: bool = True,
    make_ber_curve: bool = True,
) -> LinkResult:
    modulation = _normalize_modulation(modulation)
    channel = channel.lower()
    if modulation not in SUPPORTED_MODULATIONS:
        raise ValueError("unsupported modulation, supported: bpsk, qpsk, 16qam")
    if channel not in SUPPORTED_CHANNELS:
        raise ValueError("unsupported channel, supported: awgn, rayleigh, rician")

    payload_bits = text_to_bits(input_text)
    scrambled_bits = scramble(payload_bits, DEFAULT_SCRAMBLER_SEED)
    frame_bits = build_frame(payload_bits, scrambled_bits)
    tx_symbols = modulate(frame_bits, modulation)
    preamble_symbols = modulate(PREAMBLE, modulation)

    offset_seed = seed + 1701
    offset_symbols = None
    timed_symbols, true_offset = add_random_symbol_offset(
        tx_symbols,
        MAX_SYNC_OFFSET_SYMBOLS,
        offset_seed,
        offset_symbols,
        modulation=modulation,
    )
    channel_result = apply_channel(timed_symbols, snr_db, seed, channel=channel, equalizer=equalizer)
    rx_symbols = channel_result.symbols

    sync_start, sync_scores = find_frame_start(rx_symbols, preamble_symbols)
    rx_frame_symbols = rx_symbols[sync_start:]
    rx_bits = demodulate(rx_frame_symbols, modulation)
    parsed = parse_frame_bits(rx_bits, max_payload_bits=max(len(payload_bits) * 4, len(payload_bits) + 4096))

    descrambled_bits = descramble(parsed.scrambled_payload_bits, DEFAULT_SCRAMBLER_SEED)
    decoded_payload_bits = descrambled_bits[: parsed.payload_bit_length]
    received_text = bits_to_text(decoded_payload_bits)

    expected_crc = crc16_for_payload_bits(decoded_payload_bits)
    checksum_pass = parsed.checksum_value == expected_crc
    ber = bit_error_rate(payload_bits, decoded_payload_bits)
    match_rate = text_match_rate(input_text, received_text)
    fer = 0.0 if checksum_pass and input_text == received_text else 1.0
    sync_error_symbols = abs(sync_start - true_offset)

    metrics: dict[str, object] = {
        "snr_db": snr_db,
        "seed": seed,
        "modulation": modulation,
        "channel": channel,
        "payload_bits": len(payload_bits),
        "coded_payload_bits": parsed.coded_payload_bit_length,
        "ber": ber,
        "fer": fer,
        "text_match_rate": match_rate,
        "checksum_pass": bool(checksum_pass),
        "crc_type": "crc16_ccitt",
        "sync_start_index": sync_start,
        "true_sync_offset_symbols": true_offset,
        "sync_error_symbols": sync_error_symbols,
        "frame_parse_status": parsed.status,
        "preamble": "barker13_repeat8",
        "scrambler": "xor_lfsr_16bit",
        "channel_code": "convolutional_k7_171_133_viterbi_hard",
        "header_code": "repetition_3_majority",
        "equalizer": channel_result.equalizer,
        "fading_coefficient": {
            "real": channel_result.fading_coefficient.real,
            "imag": channel_result.fading_coefficient.imag,
        },
        "noise_power": channel_result.noise_power,
        "ebn0_db": snr_db - 10.0 * math.log10(bits_per_symbol(modulation)),
        "qpsk_gray_mapping": "00,+/+; 01,-/+; 11,-/-; 10,+/-",
    }

    ber_curve: list[tuple[float, float]] = []
    if make_ber_curve:
        ber_curve = evaluate_ber_curve(
            input_text,
            seed=seed,
            modulation=modulation,
            channel=channel,
            equalizer=equalizer,
            snr_values=[0, 2, 4, 6, 8, 10, 12, 14],
        )

    if results_dir is not None:
        results_path = Path(results_dir)
        results_path.mkdir(parents=True, exist_ok=True)

        if output_path is None:
            output_path = results_path / "received.txt"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(received_text, encoding="utf-8")

        metrics_path = results_path / "metrics.json"
        metrics_for_file = dict(metrics)
        metrics_for_file["ber_curve"] = [
            {"snr_db": snr, "ber": point_ber} for snr, point_ber in ber_curve
        ]
        metrics_path.write_text(
            json.dumps(metrics_for_file, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if make_plots:
            save_constellation(results_path / "constellation.png", rx_symbols[sync_start : sync_start + 1200])
            save_sync_peak(results_path / "sync_peak.png", sync_scores, sync_start)
            save_ber_curve(results_path / "ber_curve.png", ber_curve)

    return LinkResult(
        received_text=received_text,
        metrics=metrics,
        received_payload_bits=decoded_payload_bits,
        transmitted_payload_bits=payload_bits,
        received_symbols=rx_symbols,
        sync_scores=sync_scores,
        ber_curve=ber_curve,
    )


def evaluate_ber_curve(
    input_text: str,
    seed: int,
    modulation: str,
    channel: str,
    equalizer: str,
    snr_values: list[float],
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for index, snr in enumerate(snr_values):
        result = run_link(
            input_text,
            snr_db=snr,
            seed=seed + 1000 + index,
            modulation=modulation,
            channel=channel,
            equalizer=equalizer,
            results_dir=None,
            output_path=None,
            make_plots=False,
            make_ber_curve=False,
        )
        points.append((snr, float(result.metrics["ber"])))
    return points


def _normalize_modulation(modulation: str) -> str:
    value = modulation.lower()
    if value in {"16-qam", "qam16"}:
        return "16qam"
    return value
