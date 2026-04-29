"""Small progress helpers shared by client and server."""

from __future__ import annotations

import sys
from typing import BinaryIO


DEFAULT_CHUNK_SIZE = 64 * 1024


def format_bytes(size: int) -> str:
    """Return a compact human-readable byte count."""
    units = ("B", "KB", "MB", "GB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def print_progress(label: str, current: int, total: int) -> None:
    """Print one-line transfer progress to stderr."""
    percent = 100.0 if total == 0 else (current / total) * 100
    sys.stderr.write(
        f"\r{label}: {format_bytes(current)} / {format_bytes(total)} "
        f"({percent:5.1f}%)"
    )
    sys.stderr.flush()
    if current >= total:
        sys.stderr.write("\n")
        sys.stderr.flush()


def copy_stream_with_progress(
    source: BinaryIO,
    target: BinaryIO,
    total_size: int,
    label: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> None:
    """Copy exactly total_size bytes while printing progress."""
    remaining = total_size
    copied = 0

    while remaining > 0:
        chunk = source.read(min(chunk_size, remaining))
        if not chunk:
            raise EOFError("input ended before expected bytes were copied")
        target.write(chunk)
        copied += len(chunk)
        remaining -= len(chunk)
        print_progress(label, copied, total_size)

    if total_size == 0:
        print_progress(label, 0, 0)
