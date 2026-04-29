"""Client entry point skeleton for the TCP file transfer MVP."""

from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path

from common import progress
from common import protocol


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5001
CHUNK_SIZE = 8192


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send one file over TCP.")
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"server IP address (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"server TCP port (default: {DEFAULT_PORT})",
    )
    parser.add_argument("--file", type=Path, required=True, help="single file to send")
    return parser.parse_args()


def print_percent_progress(sent: int, total: int, last_percent: int | None) -> int:
    percent = 100 if total == 0 else int((sent * 100) / total)
    if percent != last_percent:
        print(
            f"Progress: {percent}% "
            f"({progress.format_bytes(sent)} / {progress.format_bytes(total)})",
            file=sys.stderr,
        )
    return percent


def send_file_body(sock: socket.socket, file_path: Path, file_size: int) -> None:
    sent = 0
    last_percent: int | None = None

    if file_size == 0:
        print_percent_progress(0, 0, last_percent)
        return

    with file_path.open("rb") as file:
        while sent < file_size:
            chunk = file.read(min(CHUNK_SIZE, file_size - sent))
            if not chunk:
                raise OSError("file ended before expected bytes were read")

            sock.sendall(chunk)
            sent += len(chunk)
            last_percent = print_percent_progress(sent, file_size, last_percent)


def validate_file_path(file_path: Path) -> tuple[Path, int]:
    if not file_path.exists():
        raise FileNotFoundError(f"file not found: {file_path}")
    if not file_path.is_file():
        raise IsADirectoryError(f"path is not a file: {file_path}")

    return file_path, file_path.stat().st_size


def describe_response(response: dict[str, object]) -> str:
    message = response.get("message", "")
    if message:
        return f"{response['status']}: {message}"
    return str(response["status"])


def main() -> int:
    args = parse_args()

    try:
        file_path, file_size = validate_file_path(args.file)
        metadata = protocol.build_file_metadata(file_path)
    except (OSError, protocol.ProtocolError) as exc:
        print(f"File error: {exc}", file=sys.stderr)
        return 1

    print(f"Connecting to {args.host}:{args.port}")
    print(
        f"Sending {metadata['filename']} "
        f"({progress.format_bytes(file_size)})"
    )

    try:
        with socket.create_connection((args.host, args.port)) as sock:
            protocol.send_metadata(sock, metadata)

            ready_response = protocol.recv_response(sock)
            ready_status = ready_response["status"]
            if ready_status == protocol.STATUS_ERROR:
                print(
                    f"Server error before transfer: {describe_response(ready_response)}",
                    file=sys.stderr,
                )
                return 1
            if ready_status != protocol.STATUS_READY:
                print(
                    f"READY not received: {describe_response(ready_response)}",
                    file=sys.stderr,
                )
                return 1

            print("Server READY received. Sending file body.")
            send_file_body(sock, file_path, file_size)

            final_response = protocol.recv_response(sock)
            final_status = final_response["status"]
            if final_status == protocol.STATUS_COMPLETE:
                print(f"Server response: {describe_response(final_response)}")
                return 0
            if final_status == protocol.STATUS_ERROR:
                print(
                    f"Server error after transfer: {describe_response(final_response)}",
                    file=sys.stderr,
                )
                return 1

            print(
                f"Unexpected server response: {describe_response(final_response)}",
                file=sys.stderr,
            )
            return 1
    except (ConnectionRefusedError, TimeoutError, socket.gaierror, OSError) as exc:
        print(f"Connection failed: {exc}", file=sys.stderr)
        return 1
    except protocol.ProtocolError as exc:
        print(f"Protocol error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
