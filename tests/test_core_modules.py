import json
import subprocess
import sys

import pytest

from src.channel import add_awgn, add_random_symbol_offset, apply_channel
from src.channel_coding import conv_encode, hamming74_decode, hamming74_encode, viterbi_decode
from src.framing import PREAMBLE, build_frame, crc16_for_payload_bits, parse_frame_bits
from src.modulation import QPSK_MAPPING, demodulate, modulate, qpsk_demodulate, qpsk_modulate
from src.pipeline import run_link
from src.scrambling import descramble, scramble
from src.source_codec import bits_to_text, text_to_bits
from src.synchronization import find_frame_start


def test_utf8_source_codec_round_trip_chinese_text():
    text = "无线通信技术：QPSK、AWGN、帧同步。"
    bits = text_to_bits(text)
    assert bits_to_text(bits) == text


def test_scrambler_is_reversible():
    bits = [0, 1, 1, 0, 1, 0, 0, 1] * 20
    assert descramble(scramble(bits)) == bits


def test_qpsk_gray_mapping_matches_prd():
    assert QPSK_MAPPING[(0, 0)].real > 0 and QPSK_MAPPING[(0, 0)].imag > 0
    assert QPSK_MAPPING[(0, 1)].real < 0 and QPSK_MAPPING[(0, 1)].imag > 0
    assert QPSK_MAPPING[(1, 1)].real < 0 and QPSK_MAPPING[(1, 1)].imag < 0
    assert QPSK_MAPPING[(1, 0)].real > 0 and QPSK_MAPPING[(1, 0)].imag < 0
    bits = [0, 0, 0, 1, 1, 1, 1, 0]
    assert qpsk_demodulate(qpsk_modulate(bits))[: len(bits)] == bits


def test_frame_length_checksum_and_payload_round_trip_without_noise():
    payload = text_to_bits("frame test")
    scrambled = scramble(payload)
    frame = build_frame(payload, scrambled)
    parsed = parse_frame_bits(frame)
    assert parsed.payload_bit_length == len(payload)
    assert parsed.scrambled_payload_bits == scrambled
    assert descramble(parsed.scrambled_payload_bits) == payload
    assert parsed.checksum_value == crc16_for_payload_bits(payload)
    assert parsed.status == "ok"


def test_synchronization_detects_known_offset_under_awgn():
    payload = text_to_bits("sync test")
    frame = build_frame(payload, scramble(payload))
    tx_symbols = qpsk_modulate(frame)
    rx_symbols, offset = add_random_symbol_offset(tx_symbols, 128, seed=7, offset_symbols=37)
    rx_symbols = add_awgn(rx_symbols, snr_db=12, seed=2026)
    start, scores = find_frame_start(rx_symbols, qpsk_modulate(PREAMBLE))
    assert scores
    assert abs(start - offset) <= 1


def test_end_to_end_matches_text_at_12db():
    text = "深圳大学无线通信技术期末项目公开基础用例。"
    result = run_link(text, snr_db=12, seed=2026, make_plots=False, make_ber_curve=False)
    assert result.received_text == text
    assert result.metrics["checksum_pass"] is True
    assert result.metrics["ber"] == 0.0


def test_convolutional_code_viterbi_corrects_simple_error():
    bits = [int(ch) for ch in "1011001110001111000011110101"]
    coded = conv_encode(bits)
    coded[9] ^= 1
    coded[22] ^= 1
    assert viterbi_decode(coded, decoded_length=len(bits)) == bits


def test_hamming74_corrects_single_bit_error():
    bits = [1, 0, 1, 1, 0, 1, 0, 0]
    coded = hamming74_encode(bits)
    coded[3] ^= 1
    coded[10] ^= 1
    assert hamming74_decode(coded, output_length=len(bits)) == bits


@pytest.mark.parametrize("modulation", ["bpsk", "qpsk", "16qam"])
def test_modulation_round_trip_without_noise(modulation):
    bits = [0, 1, 1, 0, 1, 0, 0, 1, 1, 1]
    recovered = demodulate(modulate(bits, modulation), modulation)
    assert recovered[: len(bits)] == bits


@pytest.mark.parametrize("channel,equalizer", [("awgn", "zf"), ("rayleigh", "zf"), ("rician", "mmse")])
def test_channel_models_do_not_change_length(channel, equalizer):
    symbols = modulate([0, 1, 1, 0] * 8, "qpsk")
    result = apply_channel(symbols, snr_db=20, seed=2026, channel=channel, equalizer=equalizer)
    assert len(result.symbols) == len(symbols)
    assert result.noise_power >= 0


@pytest.mark.parametrize("modulation", ["bpsk", "qpsk", "16qam"])
def test_end_to_end_supported_modulations_at_high_snr(modulation):
    text = "multi modulation check"
    result = run_link(text, snr_db=18, seed=2026, modulation=modulation, make_plots=False, make_ber_curve=False)
    assert result.received_text == text
    assert result.metrics["checksum_pass"] is True


@pytest.mark.parametrize("channel,equalizer", [("rayleigh", "zf"), ("rician", "mmse")])
def test_end_to_end_fading_channels_at_high_snr(channel, equalizer):
    text = "flat fading equalization check"
    result = run_link(
        text,
        snr_db=24,
        seed=2026,
        channel=channel,
        equalizer=equalizer,
        make_plots=False,
        make_ber_curve=False,
    )
    assert result.received_text == text
    assert result.metrics["checksum_pass"] is True


def test_cli_generates_required_files(tmp_path):
    input_path = tmp_path / "Test.txt"
    output_path = tmp_path / "results" / "received.txt"
    input_path.write_text("CLI 公开测试中文文本", encoding="utf-8")
    cmd = [
        sys.executable,
        "main.py",
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--results-dir",
        str(tmp_path / "results"),
        "--snr",
        "12",
        "--seed",
        "2026",
        "--mod",
        "qpsk",
        "--channel",
        "awgn",
    ]
    completed = subprocess.run(cmd, cwd=".", text=True, capture_output=True, check=True)
    assert "checksum_pass=True" in completed.stdout
    assert output_path.read_text(encoding="utf-8") == input_path.read_text(encoding="utf-8")
    metrics = json.loads((tmp_path / "results" / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["checksum_pass"] is True
    assert (tmp_path / "results" / "constellation.png").exists()
    assert (tmp_path / "results" / "ber_curve.png").exists()
    assert (tmp_path / "results" / "sync_peak.png").exists()


def test_low_snr_outputs_metrics_without_crashing():
    result = run_link("低信噪比测试", snr_db=0, seed=2026, make_plots=False, make_ber_curve=False)
    assert 0.0 <= result.metrics["ber"] <= 1.0
    assert 0.0 <= result.metrics["text_match_rate"] <= 1.0


def test_unsupported_modulation_raises_value_error():
    with pytest.raises(ValueError):
        run_link("bad mod", snr_db=12, seed=2026, modulation="bad", make_plots=False, make_ber_curve=False)
