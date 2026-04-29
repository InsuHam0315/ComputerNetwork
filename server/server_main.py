"""Server entry point for the TCP file transfer MVP."""

from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path

from common import protocol
from common.progress import DEFAULT_CHUNK_SIZE, format_bytes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Receive one file over TCP.")
    parser.add_argument("--host", default="0.0.0.0", help="interface to bind")
    parser.add_argument("--port", type=int, default=5001, help="TCP port to listen on")
    parser.add_argument(
        "--save-dir",
        default="received",
        help="directory where the received file will be saved",
    )
    return parser.parse_args()


def resolve_unique_path(save_dir: Path, filename: str) -> Path:
    """Return a non-existing path by appending _1, _2, ... before the suffix."""
    target = save_dir / Path(filename).name
    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    index = 1
    while True:
        candidate = save_dir / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def print_receive_progress(current: int, total: int, last_percent: int | None) -> int:
    percent = 100 if total == 0 else int((current * 100) // total)
    if percent != last_percent:
        sys.stderr.write(
            f"\rReceiving: {format_bytes(current)} / {format_bytes(total)} "
            f"({percent:3d}%)"
        )
        sys.stderr.flush()
        if current >= total:
            sys.stderr.write("\n")
            sys.stderr.flush()
    return percent


def receive_file(sock: socket.socket, target_path: Path, filesize: int) -> None:
    remaining = filesize
    received = 0
    last_percent: int | None = None

    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("wb") as file:
        if filesize == 0:
            print_receive_progress(0, 0, last_percent)
            return

        while remaining > 0:
            chunk = sock.recv(min(DEFAULT_CHUNK_SIZE, remaining))
            if not chunk:
                raise protocol.ProtocolError(
                    "connection closed before complete file body arrived"
                )
            file.write(chunk)
            received += len(chunk)
            remaining -= len(chunk)

            percent = 100 if filesize == 0 else int((received * 100) // filesize)
            if percent != last_percent:
                last_percent = print_receive_progress(received, filesize, last_percent)


def handle_client(conn: socket.socket, save_dir: Path) -> Path:
    metadata = protocol.recv_metadata(conn)
    filename, filesize = protocol.validate_file_metadata(metadata)
    safe_filename = Path(filename).name
    target_path = resolve_unique_path(save_dir, safe_filename)

    print(f"Receiving {safe_filename} ({format_bytes(filesize)})")
    print(f"Saving to {target_path}")
    protocol.send_response(conn, protocol.STATUS_READY)

    receive_file(conn, target_path, filesize)
    protocol.send_response(conn, protocol.STATUS_COMPLETE, "file received")
    return target_path


def main() -> None:
    args = parse_args()
    save_dir = Path(args.save_dir)

    print(f"Starting server on {args.host}:{args.port}")
    print(f"Save directory: {save_dir}")

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind((args.host, args.port))
            server_sock.listen(1)
            print("Waiting for one client...")

            conn, addr = server_sock.accept()
            with conn:
                print(f"Connected by {addr[0]}:{addr[1]}")
                try:
                    saved_path = handle_client(conn, save_dir)
                except Exception as exc:
                    try:
                        protocol.send_response(conn, protocol.STATUS_ERROR, str(exc))
                    except Exception:
                        pass
                    raise

            print(f"Receive complete: {saved_path}")
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
    except Exception as exc:
        print(f"Server error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
