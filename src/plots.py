"""Small dependency-free PNG plots for project deliverables."""

from __future__ import annotations

from pathlib import Path
import struct
import zlib


Color = tuple[int, int, int]
Point = tuple[float, float]

WHITE: Color = (255, 255, 255)
BLACK: Color = (24, 24, 24)
GRID: Color = (220, 226, 232)
BLUE: Color = (42, 110, 216)
RED: Color = (210, 70, 70)
GREEN: Color = (42, 145, 95)


def _blank(width: int, height: int, color: Color = WHITE) -> list[list[Color]]:
    return [[color for _ in range(width)] for _ in range(height)]


def _set(px: list[list[Color]], x: int, y: int, color: Color) -> None:
    if 0 <= y < len(px) and 0 <= x < len(px[0]):
        px[y][x] = color


def _line(px: list[list[Color]], x0: int, y0: int, x1: int, y1: int, color: Color) -> None:
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        _set(px, x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def _circle(px: list[list[Color]], x: int, y: int, radius: int, color: Color) -> None:
    for yy in range(y - radius, y + radius + 1):
        for xx in range(x - radius, x + radius + 1):
            if (xx - x) ** 2 + (yy - y) ** 2 <= radius * radius:
                _set(px, xx, yy, color)


def _write_png(path: str | Path, px: list[list[Color]]) -> None:
    height = len(px)
    width = len(px[0]) if height else 0
    raw = bytearray()
    for row in px:
        raw.append(0)
        for r, g, b in row:
            raw.extend([r, g, b])

    def chunk(name: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + name
            + data
            + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)
        )

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )
    Path(path).write_bytes(png)


def _plot_area(width: int, height: int) -> tuple[int, int, int, int]:
    return 54, 28, width - 24, height - 44


def _draw_axes(px: list[list[Color]]) -> tuple[int, int, int, int]:
    width = len(px[0])
    height = len(px)
    left, top, right, bottom = _plot_area(width, height)
    for t in [0.25, 0.5, 0.75]:
        x = int(left + (right - left) * t)
        y = int(top + (bottom - top) * t)
        _line(px, x, top, x, bottom, GRID)
        _line(px, left, y, right, y, GRID)
    _line(px, left, bottom, right, bottom, BLACK)
    _line(px, left, top, left, bottom, BLACK)
    return left, top, right, bottom


def save_constellation(path: str | Path, received_symbols: list[complex], max_points: int = 1200) -> None:
    width, height = 760, 520
    px = _blank(width, height)
    left, top, right, bottom = _draw_axes(px)

    # Draw I/Q zero axes.
    x0 = int((left + right) / 2)
    y0 = int((top + bottom) / 2)
    _line(px, x0, top, x0, bottom, (160, 170, 180))
    _line(px, left, y0, right, y0, (160, 170, 180))

    points = received_symbols[:max_points]
    scale = 1.8
    for symbol in points:
        x = int(left + (symbol.real + scale) / (2 * scale) * (right - left))
        y = int(bottom - (symbol.imag + scale) / (2 * scale) * (bottom - top))
        _circle(px, x, y, 2, BLUE)

    for re in (-1, 1):
        for im in (-1, 1):
            x = int(left + (re / 2**0.5 + scale) / (2 * scale) * (right - left))
            y = int(bottom - (im / 2**0.5 + scale) / (2 * scale) * (bottom - top))
            _circle(px, x, y, 5, RED)

    _write_png(path, px)


def save_sync_peak(path: str | Path, scores: list[float], detected_index: int) -> None:
    width, height = 760, 380
    px = _blank(width, height)
    left, top, right, bottom = _draw_axes(px)
    if not scores:
        _write_png(path, px)
        return

    max_score = max(max(scores), 1e-12)
    prev: tuple[int, int] | None = None
    for i, score in enumerate(scores):
        x = int(left + i / max(1, len(scores) - 1) * (right - left))
        y = int(bottom - score / max_score * (bottom - top))
        if prev is not None:
            _line(px, prev[0], prev[1], x, y, GREEN)
        prev = (x, y)

    peak_x = int(left + detected_index / max(1, len(scores) - 1) * (right - left))
    _line(px, peak_x, top, peak_x, bottom, RED)
    _write_png(path, px)


def save_ber_curve(path: str | Path, points: list[Point]) -> None:
    width, height = 760, 420
    px = _blank(width, height)
    left, top, right, bottom = _draw_axes(px)
    if not points:
        _write_png(path, px)
        return

    xs = [p[0] for p in points]
    ys = [max(p[1], 1e-6) for p in points]
    min_x, max_x = min(xs), max(xs)
    min_log_y, max_log_y = -6.0, 0.0

    prev: tuple[int, int] | None = None
    for snr, ber in points:
        log_y = max(min_log_y, min(max_log_y, _log10(max(ber, 1e-6))))
        x = int(left + (snr - min_x) / max(1e-12, max_x - min_x) * (right - left))
        y = int(bottom - (log_y - min_log_y) / (max_log_y - min_log_y) * (bottom - top))
        _circle(px, x, y, 4, RED)
        if prev is not None:
            _line(px, prev[0], prev[1], x, y, BLUE)
        prev = (x, y)

    _write_png(path, px)


def _log10(value: float) -> float:
    import math

    return math.log10(value)

