"""Create a deterministic dummy file for file-transfer tests."""

from __future__ import annotations

import argparse
from pathlib import Path


CHUNK_SIZE = 64 * 1024


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("size-kb must be an integer") from exc

    if number < 0:
        raise argparse.ArgumentTypeError("size-kb must be zero or greater")
    return number


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a dummy binary file with a requested size."
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="output file path, for example sample.bin",
    )
    parser.add_argument(
        "--size-kb",
        type=positive_int,
        required=True,
        help="file size in KiB, for example 100",
    )
    return parser.parse_args()


def create_dummy_file(path: Path, size_kb: int) -> int:
    size_bytes = size_kb * 1024
    path.parent.mkdir(parents=True, exist_ok=True)

    pattern = bytes(range(256))
    remaining = size_bytes

    with path.open("wb") as output_file:
        while remaining > 0:
            chunk_size = min(CHUNK_SIZE, remaining)
            repeats = (chunk_size // len(pattern)) + 1
            output_file.write((pattern * repeats)[:chunk_size])
            remaining -= chunk_size

    return size_bytes


def main() -> int:
    args = parse_args()
    size_bytes = create_dummy_file(args.output, args.size_kb)
    print(f"Created: {args.output.resolve()}")
    print(f"Size: {size_bytes} bytes ({args.size_kb} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
