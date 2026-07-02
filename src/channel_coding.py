"""Channel coding blocks used by the baseband link.

The production payload path uses a rate-1/2 convolutional code with
constraint length K=7 and generators (171, 133) in octal. Repetition and
Hamming(7,4) are kept as small, explainable baselines and for protected frame
header fields.
"""

from __future__ import annotations


DEFAULT_REPETITION_FACTOR = 3
CONV_CONSTRAINT_LENGTH = 7
CONV_MEMORY = CONV_CONSTRAINT_LENGTH - 1
CONV_GENERATORS = (0o171, 0o133)
CONV_NUM_STATES = 1 << CONV_MEMORY


def encode_repetition(bits: list[int], factor: int = DEFAULT_REPETITION_FACTOR) -> list[int]:
    if factor < 1 or factor % 2 == 0:
        raise ValueError("repetition factor must be a positive odd integer")
    out: list[int] = []
    for bit in bits:
        out.extend([bit & 1] * factor)
    return out


def decode_repetition(
    bits: list[int],
    factor: int = DEFAULT_REPETITION_FACTOR,
    output_length: int | None = None,
) -> list[int]:
    if factor < 1 or factor % 2 == 0:
        raise ValueError("repetition factor must be a positive odd integer")

    decoded: list[int] = []
    for i in range(0, len(bits), factor):
        chunk = bits[i : i + factor]
        if not chunk:
            break
        ones = sum(1 for bit in chunk if bit)
        decoded.append(1 if ones >= (len(chunk) + 1) // 2 else 0)

    if output_length is not None:
        if output_length < 0:
            raise ValueError("output_length must be non-negative")
        if len(decoded) < output_length:
            decoded.extend([0] * (output_length - len(decoded)))
        decoded = decoded[:output_length]
    return decoded


def _parity(value: int) -> int:
    return bin(value).count("1") & 1


def _conv_transition(prev_state: int, input_bit: int) -> tuple[int, tuple[int, int]]:
    """Return next state and two coded bits for one convolutional-code step."""
    bit = input_bit & 1
    register = (bit << CONV_MEMORY) | prev_state
    outputs = tuple(_parity(register & generator) for generator in CONV_GENERATORS)
    next_state = (register >> 1) & (CONV_NUM_STATES - 1)
    return next_state, (outputs[0], outputs[1])


def conv_encode(bits: list[int], terminate: bool = True) -> list[int]:
    """Rate-1/2 K=7 convolutional encoder using (171,133) octal generators."""
    state = 0
    encoded: list[int] = []
    input_bits = [bit & 1 for bit in bits]
    if terminate:
        input_bits.extend([0] * CONV_MEMORY)

    for bit in input_bits:
        state, pair = _conv_transition(state, bit)
        encoded.extend(pair)
    return encoded


def channel_encode(bits: list[int]) -> list[int]:
    """Default channel FEC: terminated K=7 (171,133) rate-1/2 convolutional code."""
    return conv_encode(bits, terminate=True)


def channel_decode(coded_bits: list[int], decoded_length: int | None = None) -> list[int]:
    """Hard-decision Viterbi decode matching :func:`channel_encode`.

    When ``decoded_length`` is omitted it is inferred from the terminated
    rate-1/2 structure: ``info = coded / 2 - CONV_MEMORY``.
    """
    coded = list(coded_bits)
    if decoded_length is None:
        decoded_length = max(0, len(coded) // 2 - CONV_MEMORY)
    return viterbi_decode(coded, decoded_length=decoded_length, enforce_final_state=True)


def viterbi_decode(
    coded_bits: list[int],
    decoded_length: int,
    enforce_final_state: bool = True,
) -> list[int]:
    """Hard-decision Viterbi decoder for the K=7 rate-1/2 code.

    `decoded_length` is the number of information bits wanted before the
    terminating zero-tail bits. Missing or odd coded inputs are padded with
    zeros so low-SNR frame damage produces metrics instead of a crash.
    """
    if decoded_length < 0:
        raise ValueError("decoded_length must be non-negative")

    pairs = list(coded_bits)
    if len(pairs) % 2:
        pairs.append(0)
    received = [(pairs[i] & 1, pairs[i + 1] & 1) for i in range(0, len(pairs), 2)]
    if not received:
        return [0] * decoded_length

    inf = 10**12
    metrics = [inf] * CONV_NUM_STATES
    metrics[0] = 0
    histories: list[list[tuple[int, int] | None]] = []

    for rx_pair in received:
        next_metrics = [inf] * CONV_NUM_STATES
        history: list[tuple[int, int] | None] = [None] * CONV_NUM_STATES
        for prev_state, prev_metric in enumerate(metrics):
            if prev_metric >= inf:
                continue
            for input_bit in (0, 1):
                next_state, expected = _conv_transition(prev_state, input_bit)
                distance = (rx_pair[0] != expected[0]) + (rx_pair[1] != expected[1])
                metric = prev_metric + distance
                if metric < next_metrics[next_state]:
                    next_metrics[next_state] = metric
                    history[next_state] = (prev_state, input_bit)
        metrics = next_metrics
        histories.append(history)

    if enforce_final_state and metrics[0] < inf:
        state = 0
    else:
        state = min(range(CONV_NUM_STATES), key=lambda s: metrics[s])

    decoded_reversed: list[int] = []
    for history in reversed(histories):
        item = history[state]
        if item is None:
            decoded_reversed.append(0)
            state = 0
        else:
            prev_state, input_bit = item
            decoded_reversed.append(input_bit)
            state = prev_state

    decoded = list(reversed(decoded_reversed))
    if len(decoded) < decoded_length:
        decoded.extend([0] * (decoded_length - len(decoded)))
    return decoded[:decoded_length]


def hamming74_encode(bits: list[int]) -> list[int]:
    """Encode data bits with Hamming(7,4), padding the final nibble with zeros."""
    padded = [bit & 1 for bit in bits]
    while len(padded) % 4:
        padded.append(0)

    encoded: list[int] = []
    for i in range(0, len(padded), 4):
        d1, d2, d3, d4 = padded[i : i + 4]
        p1 = d1 ^ d2 ^ d4
        p2 = d1 ^ d3 ^ d4
        p3 = d2 ^ d3 ^ d4
        encoded.extend([p1, p2, d1, p3, d2, d3, d4])
    return encoded


def hamming74_decode(bits: list[int], output_length: int | None = None) -> list[int]:
    """Decode Hamming(7,4) and correct one bit error per codeword."""
    decoded: list[int] = []
    padded = [bit & 1 for bit in bits]
    while len(padded) % 7:
        padded.append(0)

    for i in range(0, len(padded), 7):
        code = padded[i : i + 7]
        s1 = code[0] ^ code[2] ^ code[4] ^ code[6]
        s2 = code[1] ^ code[2] ^ code[5] ^ code[6]
        s3 = code[3] ^ code[4] ^ code[5] ^ code[6]
        syndrome = s1 | (s2 << 1) | (s3 << 2)
        if syndrome:
            idx = syndrome - 1
            if 0 <= idx < 7:
                code[idx] ^= 1
        decoded.extend([code[2], code[4], code[5], code[6]])

    if output_length is not None:
        if len(decoded) < output_length:
            decoded.extend([0] * (output_length - len(decoded)))
        decoded = decoded[:output_length]
    return decoded
