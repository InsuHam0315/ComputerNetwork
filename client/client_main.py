"""Client entry point for ConnectBox file sending."""

from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path
from typing import Callable, Iterable

from common import progress
from common import protocol


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5001
CHUNK_SIZE = 8192

ProgressCallback = Callable[[dict[str, object]], None]
LogCallback = Callable[[str], None]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send one file, multiple files, or one folder over TCP."
    )
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
    parser.add_argument(
        "--file",
        dest="files",
        action="append",
        type=Path,
        help="file to send; repeat this option for multiple files",
    )
    parser.add_argument(
        "--files",
        dest="files_list",
        nargs="+",
        type=Path,
        help="space-separated files to send in one transfer session",
    )
    parser.add_argument("--folder", type=Path, help="folder to send recursively")
    return parser.parse_args()


def _log(message: str, log_callback: LogCallback | None = None) -> None:
    if log_callback is None:
        print(message)
    else:
        log_callback(message)


def print_percent_progress(sent: int, total: int, last_percent: int | None) -> int:
    percent = 100 if total == 0 else int((sent * 100) / total)
    if percent != last_percent:
        print(
            f"Progress: {percent}% "
            f"({progress.format_bytes(sent)} / {progress.format_bytes(total)})",
            file=sys.stderr,
        )
    return percent


def _emit_progress(
    progress_callback: ProgressCallback | None,
    *,
    relative_path: str,
    file_index: int,
    file_count: int,
    current_bytes: int,
    current_total: int,
    total_bytes: int,
    total_size: int,
) -> None:
    if progress_callback is None:
        return
    progress_callback(
        {
            "direction": "send",
            "relative_path": relative_path,
            "file_index": file_index,
            "file_count": file_count,
            "current_bytes": current_bytes,
            "current_total": current_total,
            "total_bytes": total_bytes,
            "total_size": total_size,
        }
    )


def send_file_body(
    sock: socket.socket,
    file_path: Path,
    file_size: int,
    *,
    relative_path: str | None = None,
    file_index: int = 1,
    file_count: int = 1,
    total_before: int = 0,
    total_size: int | None = None,
    progress_callback: ProgressCallback | None = None,
) -> None:
    sent = 0
    last_percent: int | None = None
    display_path = relative_path or file_path.name
    effective_total_size = file_size if total_size is None else total_size

    if file_size == 0:
        if progress_callback is None:
            print_percent_progress(0, 0, last_percent)
        else:
            _emit_progress(
                progress_callback,
                relative_path=display_path,
                file_index=file_index,
                file_count=file_count,
                current_bytes=0,
                current_total=0,
                total_bytes=total_before,
                total_size=effective_total_size,
            )
        return

    with file_path.open("rb") as file:
        while sent < file_size:
            chunk = file.read(min(CHUNK_SIZE, file_size - sent))
            if not chunk:
                raise OSError("file ended before expected bytes were read")

            sock.sendall(chunk)
            sent += len(chunk)
            if progress_callback is None:
                last_percent = print_percent_progress(sent, file_size, last_percent)
            else:
                _emit_progress(
                    progress_callback,
                    relative_path=display_path,
                    file_index=file_index,
                    file_count=file_count,
                    current_bytes=sent,
                    current_total=file_size,
                    total_bytes=total_before + sent,
                    total_size=effective_total_size,
                )


def validate_file_path(file_path: Path) -> tuple[Path, int]:
    if not file_path.exists():
        raise FileNotFoundError(f"file not found: {file_path}")
    if not file_path.is_file():
        raise IsADirectoryError(f"path is not a file: {file_path}")

    return file_path, file_path.stat().st_size


def validate_folder_path(folder_path: Path) -> Path:
    if not folder_path.exists():
        raise FileNotFoundError(f"folder not found: {folder_path}")
    if not folder_path.is_dir():
        raise NotADirectoryError(f"path is not a folder: {folder_path}")
    return folder_path


def build_transfer_items(
    file_paths: Iterable[Path] | None = None,
    folder_path: Path | None = None,
) -> list[protocol.TransferItem]:
    """Build a deterministic v2-compatible transfer item list."""
    items: list[protocol.TransferItem] = []

    if file_paths is not None:
        for file_path in file_paths:
            path, size = validate_file_path(Path(file_path))
            relative_path = protocol.normalize_relative_path(path.name)
            items.append(protocol.TransferItem(path, relative_path, size))

    if folder_path is not None:
        folder = validate_folder_path(Path(folder_path))
        folder_name = protocol.normalize_relative_path(folder.name)
        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue
            relative_child = path.relative_to(folder).as_posix()
            relative_path = protocol.normalize_relative_path(
                f"{folder_name}/{relative_child}"
            )
            items.append(protocol.TransferItem(path, relative_path, path.stat().st_size))

    if not items:
        raise ValueError("no files to send")
    return items


def describe_response(response: dict[str, object]) -> str:
    message = response.get("message", "")
    if message:
        return f"{response['status']}: {message}"
    return str(response["status"])


def _expect_ready(response: dict[str, object], context: str) -> None:
    status = response["status"]
    if status == protocol.STATUS_ERROR:
        raise protocol.ProtocolError(
            f"server error during {context}: {describe_response(response)}"
        )
    if status != protocol.STATUS_READY:
        raise protocol.ProtocolError(
            f"READY not received during {context}: {describe_response(response)}"
        )


def _send_single_file_v1(
    sock: socket.socket,
    item: protocol.TransferItem,
    *,
    log_callback: LogCallback | None = None,
    progress_callback: ProgressCallback | None = None,
) -> None:
    metadata = protocol.build_file_metadata(item.path)
    _log(
        f"Sending {metadata['filename']} ({progress.format_bytes(item.filesize)})",
        log_callback,
    )
    protocol.send_metadata(sock, metadata)
    _expect_ready(protocol.recv_response(sock), "single-file setup")

    _log("Server READY received. Sending file body.", log_callback)
    send_file_body(
        sock,
        item.path,
        item.filesize,
        relative_path=item.relative_path,
        progress_callback=progress_callback,
    )

    final_response = protocol.recv_response(sock)
    final_status = final_response["status"]
    if final_status != protocol.STATUS_COMPLETE:
        raise protocol.ProtocolError(
            f"single-file transfer failed: {describe_response(final_response)}"
        )
    _log(f"Server response: {describe_response(final_response)}", log_callback)


def _send_transfer_v2(
    sock: socket.socket,
    items: list[protocol.TransferItem],
    *,
    log_callback: LogCallback | None = None,
    progress_callback: ProgressCallback | None = None,
) -> None:
    total_size = sum(item.filesize for item in items)
    item_count = len(items)
    _log(
        f"Sending transfer session: {item_count} files, "
        f"{progress.format_bytes(total_size)} total",
        log_callback,
    )
    protocol.send_metadata(
        sock, protocol.build_transfer_start_metadata(item_count, total_size)
    )
    _expect_ready(protocol.recv_response(sock), "transfer setup")

    total_sent = 0
    for index, item in enumerate(items, start=1):
        _log(
            f"[{index}/{item_count}] Sending {item.relative_path} "
            f"({progress.format_bytes(item.filesize)})",
            log_callback,
        )
        protocol.send_metadata(
            sock,
            protocol.build_file_item_metadata(index, item.relative_path, item.filesize),
        )
        _expect_ready(protocol.recv_response(sock), f"file {index} setup")

        send_file_body(
            sock,
            item.path,
            item.filesize,
            relative_path=item.relative_path,
            file_index=index,
            file_count=item_count,
            total_before=total_sent,
            total_size=total_size,
            progress_callback=progress_callback,
        )
        done = protocol.recv_file_done(sock)
        if done["status"] != protocol.STATUS_COMPLETE:
            raise protocol.ProtocolError(
                f"server failed file {index}: {done.get('message', '')}"
            )
        total_sent += item.filesize

    protocol.send_metadata(sock, protocol.build_transfer_end_metadata(item_count, total_size))
    final_response = protocol.recv_response(sock)
    if final_response["status"] != protocol.STATUS_COMPLETE:
        raise protocol.ProtocolError(
            f"transfer failed: {describe_response(final_response)}"
        )
    _log(f"Server response: {describe_response(final_response)}", log_callback)


def send_paths(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    file_paths: Iterable[Path] | None = None,
    folder_path: Path | None = None,
    log_callback: LogCallback | None = None,
    progress_callback: ProgressCallback | None = None,
) -> None:
    """Send files/folder to a ConnectBox server.

    A single file with no folder uses v1 for MVP compatibility. Multi-file and
    folder transfers use the v2 transfer-session protocol.
    """
    files = list(file_paths or [])
    items = build_transfer_items(files, folder_path)
    use_v2 = folder_path is not None or len(items) > 1

    _log(f"Connecting to {host}:{port}", log_callback)
    with socket.create_connection((host, port)) as sock:
        if use_v2:
            _send_transfer_v2(
                sock,
                items,
                log_callback=log_callback,
                progress_callback=progress_callback,
            )
        else:
            _send_single_file_v1(
                sock,
                items[0],
                log_callback=log_callback,
                progress_callback=progress_callback,
            )


def _cli_progress_printer() -> ProgressCallback:
    last: dict[tuple[int, int], int] = {}

    def print_progress(event: dict[str, object]) -> None:
        current = int(event["current_bytes"])
        current_total = int(event["current_total"])
        total_bytes = int(event["total_bytes"])
        total_size = int(event["total_size"])
        file_index = int(event["file_index"])
        file_count = int(event["file_count"])
        relative_path = str(event["relative_path"])

        current_percent = 100 if current_total == 0 else int(current * 100 / current_total)
        total_percent = 100 if total_size == 0 else int(total_bytes * 100 / total_size)
        key = (file_index, total_percent)
        if last.get(key) == current_percent:
            return
        last[key] = current_percent
        print(
            f"Current [{file_index}/{file_count}] {relative_path}: "
            f"{current_percent}% "
            f"({progress.format_bytes(current)} / {progress.format_bytes(current_total)}) | "
            f"Total: {total_percent}% "
            f"({progress.format_bytes(total_bytes)} / {progress.format_bytes(total_size)})",
            file=sys.stderr,
        )

    return print_progress


def main() -> int:
    args = parse_args()
    file_paths: list[Path] = []
    if args.files:
        file_paths.extend(args.files)
    if args.files_list:
        file_paths.extend(args.files_list)

    if not file_paths and args.folder is None:
        print("File error: specify --file, --files, or --folder", file=sys.stderr)
        return 1

    try:
        send_paths(
            args.host,
            args.port,
            file_paths=file_paths,
            folder_path=args.folder,
            progress_callback=_cli_progress_printer(),
        )
        return 0
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError, ValueError) as exc:
        print(f"File error: {exc}", file=sys.stderr)
        return 1
    except (ConnectionRefusedError, TimeoutError, socket.gaierror, OSError) as exc:
        print(f"Connection failed: {exc}", file=sys.stderr)
        return 1
    except protocol.ProtocolError as exc:
        print(f"Protocol error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
