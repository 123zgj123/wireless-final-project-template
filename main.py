"""Unified CLI entry for the wireless final project."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from src.pipeline import run_link


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wireless baseband file transmission simulation")
    parser.add_argument("--input", default="Test.txt", help="UTF-8 input text file")
    parser.add_argument("--output", default="results/received.txt", help="Recovered output text file")
    parser.add_argument("--snr", type=float, default=12.0, help="AWGN SNR in dB")
    parser.add_argument("--seed", type=int, default=2026, help="Random seed for reproducible channel noise")
    parser.add_argument("--mod", default="qpsk", help="Modulation: bpsk, qpsk, or 16qam")
    parser.add_argument("--channel", default="awgn", help="Channel: awgn, rayleigh, or rician")
    parser.add_argument("--equalizer", default="zf", help="Equalizer for fading channels: zf, mmse, or none")
    parser.add_argument("--results-dir", default="results", help="Directory for metrics and plots")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 2

    input_text = input_path.read_text(encoding="utf-8")
    try:
        result = run_link(
            input_text=input_text,
            snr_db=args.snr,
            seed=args.seed,
            modulation=args.mod,
            channel=args.channel,
            equalizer=args.equalizer,
            results_dir=args.results_dir,
            output_path=args.output,
            make_plots=True,
            make_ber_curve=True,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(
        "completed: "
        f"BER={result.metrics['ber']:.6g}, "
        f"FER={result.metrics['fer']:.6g}, "
        f"text_match_rate={result.metrics['text_match_rate']:.6g}, "
        f"checksum_pass={result.metrics['checksum_pass']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
