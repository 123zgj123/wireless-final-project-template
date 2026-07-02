"""Frame structure, protected length fields, FEC payload, and CRC validation."""

from __future__ import annotations

from dataclasses import dataclass

from .channel_coding import (
    CONV_MEMORY,
    DEFAULT_REPETITION_FACTOR,
    conv_encode,
    decode_repetition,
    encode_repetition,
    viterbi_decode,
)
from .source_codec import bits_to_bytes


LENGTH_FIELD_BITS = 32
CHECKSUM_BITS = 16
BARKER_13_CHIPS = [1, 1, 1, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1]
PREAMBLE_REPETITIONS = 8


def _make_preamble_bits() -> list[int]:
    # Barker +1 chips are represented by bit 0 so BPSK maps them to +1.
    barker_bits = [0 if chip > 0 else 1 for chip in BARKER_13_CHIPS]
    return barker_bits * PREAMBLE_REPETITIONS


PREAMBLE = _make_preamble_bits()


@dataclass(frozen=True)
class ParsedFrame:
    payload_bit_length: int
    coded_payload_bit_length: int
    coded_payload_bits: list[int]
    decoded_info_bits: list[int]
    scrambled_payload_bits: list[int]
    checksum_bits: list[int]
    checksum_value: int
    consumed_bits: int
    status: str


def int_to_bits(value: int, width: int) -> list[int]:
    if value < 0:
        raise ValueError("value must be non-negative")
    if value >= (1 << width):
        raise ValueError(f"value {value} does not fit in {width} bits")
    return [(value >> shift) & 1 for shift in range(width - 1, -1, -1)]


def bits_to_int(bits: list[int]) -> int:
    value = 0
    for bit in bits:
        value = (value << 1) | (bit & 1)
    return value


def crc16_ccitt(data: bytes, initial: int = 0xFFFF) -> int:
    crc = initial
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF


def crc16_for_payload_bits(payload_bits: list[int]) -> int:
    return crc16_ccitt(bits_to_bytes(payload_bits))


def checksum_bits(payload_bits: list[int]) -> list[int]:
    return int_to_bits(crc16_for_payload_bits(payload_bits), CHECKSUM_BITS)


def convolutional_coded_length(info_bit_length: int) -> int:
    return (info_bit_length + CONV_MEMORY) * 2


def build_frame(
    payload_bits: list[int],
    scrambled_payload_bits: list[int] | None = None,
) -> list[int]:
    payload_bits = [bit & 1 for bit in payload_bits]
    if scrambled_payload_bits is None:
        scrambled_payload_bits = list(payload_bits)
    else:
        scrambled_payload_bits = [bit & 1 for bit in scrambled_payload_bits]
    if len(payload_bits) != len(scrambled_payload_bits):
        raise ValueError("payload and scrambled payload must have the same length")

    crc_bits = checksum_bits(payload_bits)
    info_bits = scrambled_payload_bits + crc_bits
    coded_payload = conv_encode(info_bits, terminate=True)

    header_bits = int_to_bits(len(payload_bits), LENGTH_FIELD_BITS) + int_to_bits(
        len(coded_payload), LENGTH_FIELD_BITS
    )
    encoded_header = encode_repetition(header_bits)

    return PREAMBLE + encoded_header + coded_payload


def parse_frame(bits: list[int], max_payload_bits: int | None = None) -> dict:
    """Convenience wrapper returning frame fields as a dict.

    Used by the standard frame build/parse round-trip so callers can read the
    preamble, length, payload and checksum without depending on the internal
    dataclass layout.
    """
    parsed = parse_frame_bits([bit & 1 for bit in bits], max_payload_bits=max_payload_bits)
    return {
        "preamble": PREAMBLE,
        "length": parsed.payload_bit_length,
        "payload": parsed.scrambled_payload_bits,
        "payload_bits": parsed.scrambled_payload_bits,
        "coded_length": parsed.coded_payload_bit_length,
        "checksum": parsed.checksum_value,
        "crc": parsed.checksum_value,
        "status": parsed.status,
    }


def parse_frame_bits(bits: list[int], max_payload_bits: int | None = None) -> ParsedFrame:
    """Parse a demodulated bit stream starting at the frame preamble."""
    status = "ok"
    cursor = len(PREAMBLE)
    header_size = 2 * LENGTH_FIELD_BITS * DEFAULT_REPETITION_FACTOR

    if len(bits) < cursor + header_size:
        header_bits = decode_repetition(bits[cursor:], output_length=2 * LENGTH_FIELD_BITS)
        payload_bit_length = bits_to_int(header_bits[:LENGTH_FIELD_BITS])
        coded_bit_length = bits_to_int(header_bits[LENGTH_FIELD_BITS:])
        return ParsedFrame(
            payload_bit_length,
            coded_bit_length,
            [],
            [],
            [],
            [0] * CHECKSUM_BITS,
            0,
            len(bits),
            "truncated_header",
        )

    encoded_header = bits[cursor : cursor + header_size]
    cursor += header_size
    header_bits = decode_repetition(encoded_header, output_length=2 * LENGTH_FIELD_BITS)
    payload_bit_length = bits_to_int(header_bits[:LENGTH_FIELD_BITS])
    coded_bit_length = bits_to_int(header_bits[LENGTH_FIELD_BITS:])

    if max_payload_bits is not None and payload_bit_length > max_payload_bits:
        payload_bit_length = max_payload_bits
        status = "length_clamped"

    expected_coded_length = convolutional_coded_length(payload_bit_length + CHECKSUM_BITS)
    if coded_bit_length <= 0 or coded_bit_length > expected_coded_length + 512:
        coded_bit_length = expected_coded_length
        status = "coded_length_clamped" if status == "ok" else status

    required = cursor + coded_bit_length
    if len(bits) < required:
        status = "truncated_payload"

    coded_payload = bits[cursor : min(cursor + coded_bit_length, len(bits))]
    cursor += len(coded_payload)

    decoded_info_bits = viterbi_decode(
        coded_payload,
        decoded_length=payload_bit_length + CHECKSUM_BITS,
        enforce_final_state=True,
    )
    scrambled_payload_bits = decoded_info_bits[:payload_bit_length]
    decoded_crc_bits = decoded_info_bits[payload_bit_length : payload_bit_length + CHECKSUM_BITS]
    if len(decoded_crc_bits) < CHECKSUM_BITS:
        decoded_crc_bits.extend([0] * (CHECKSUM_BITS - len(decoded_crc_bits)))
    checksum_value = bits_to_int(decoded_crc_bits)

    return ParsedFrame(
        payload_bit_length=payload_bit_length,
        coded_payload_bit_length=coded_bit_length,
        coded_payload_bits=coded_payload,
        decoded_info_bits=decoded_info_bits,
        scrambled_payload_bits=scrambled_payload_bits,
        checksum_bits=decoded_crc_bits,
        checksum_value=checksum_value,
        consumed_bits=cursor,
        status=status,
    )
