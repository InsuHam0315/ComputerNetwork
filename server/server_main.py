"""Server entry point for ConnectBox file receiving."""

from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path
from typing import Callable

from common import protocol
from common.progress import DEFAULT_CHUNK_SIZE, format_bytes


ProgressCallback = Callable[[dict[str, object]], None]
LogCallback = Callable[[str], None]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Receive one ConnectBox transfer over TCP."
    )
    parser.add_argument("--host", default="0.0.0.0", help="interface to bind")
    parser.add_argument("--port", type=int, default=5001, help="TCP port to listen on")
    parser.add_argument(
        "--save-dir",
        default="received",
        help="directory where received files will be saved",
    )
    return parser.parse_args()


def _log(message: str, log_callback: LogCallback | None = None) -> None:
    if log_callback is None:
        print(message)
    else:
        log_callback(message)


def resolve_unique_path(parent_dir: Path, filename: str) -> Path:
    """Return a non-existing path by appending _1, _2, ... before the suffix."""
    target = parent_dir / Path(filename).name
    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    index = 1
    while True:
        candidate = parent_dir / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def resolve_unique_relative_path(save_dir: Path, relative_path: str) -> Path:
    """Return a safe target path under save_dir for a v2 relative path."""
    parts = protocol.relative_path_parts(relative_path)
    target = save_dir.joinpath(*parts)
    return resolve_unique_path(target.parent, target.name)


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
            "direction": "receive",
            "relative_path": relative_path,
            "file_index": file_index,
            "file_count": file_count,
            "current_bytes": current_bytes,
            "current_total": current_total,
            "total_bytes": total_bytes,
            "total_size": total_size,
        }
    )


def receive_file(
    sock: socket.socket,
    target_path: Path,
    filesize: int,
    *,
    relative_path: str = "",
    file_index: int = 1,
    file_count: int = 1,
    total_before: int = 0,
    total_size: int | None = None,
    progress_callback: ProgressCallback | None = None,
) -> None:
    remaining = filesize
    received = 0
    last_percent: int | None = None
    effective_total_size = filesize if total_size is None else total_size
    display_path = relative_path or target_path.name

    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("wb") as file:
        if filesize == 0:
            if progress_callback is None:
                print_receive_progress(0, 0, last_percent)
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

        while remaining > 0:
            chunk = sock.recv(min(DEFAULT_CHUNK_SIZE, remaining))
            if not chunk:
                raise protocol.ProtocolError(
                    "connection closed before complete file body arrived"
                )
            file.write(chunk)
            received += len(chunk)
            remaining -= len(chunk)

            if progress_callback is None:
                percent = 100 if filesize == 0 else int((received * 100) // filesize)
                if percent != last_percent:
                    last_percent = print_receive_progress(received, filesize, last_percent)
            else:
                _emit_progress(
                    progress_callback,
                    relative_path=display_path,
                    file_index=file_index,
                    file_count=file_count,
                    current_bytes=received,
                    current_total=filesize,
                    total_bytes=total_before + received,
                    total_size=effective_total_size,
                )


def _handle_v1_file(
    conn: socket.socket,
    metadata: dict[str, object],
    save_dir: Path,
    *,
    log_callback: LogCallback | None = None,
    progress_callback: ProgressCallback | None = None,
) -> list[Path]:
    filename, filesize = protocol.validate_file_metadata(metadata)
    safe_filename = Path(filename).name
    target_path = resolve_unique_path(save_dir, safe_filename)

    _log(f"Receiving {safe_filename} ({format_bytes(filesize)})", log_callback)
    _log(f"Saving to {target_path}", log_callback)
    protocol.send_response(conn, protocol.STATUS_READY)

    receive_file(
        conn,
        target_path,
        filesize,
        relative_path=safe_filename,
        progress_callback=progress_callback,
    )
    protocol.send_response(conn, protocol.STATUS_COMPLETE, "file received")
    return [target_path]


def _handle_v2_transfer(
    conn: socket.socket,
    start_metadata: dict[str, object],
    save_dir: Path,
    *,
    log_callback: LogCallback | None = None,
    progress_callback: ProgressCallback | None = None,
) -> list[Path]:
    item_count, total_size = protocol.validate_transfer_start_metadata(start_metadata)
    _log(
        f"Receiving transfer session: {item_count} files, {format_bytes(total_size)}",
        log_callback,
    )
    protocol.send_response(conn, protocol.STATUS_READY, "transfer ready")

    saved_paths: list[Path] = []
    total_received = 0
    for expected_index in range(1, item_count + 1):
        item_metadata = protocol.recv_metadata(conn)
        index, relative_path, filesize = protocol.validate_file_item_metadata(
            item_metadata
        )
        if index != expected_index:
            raise protocol.ProtocolError(
                f"unexpected file index: expected {expected_index}, got {index}"
            )

        target_path = resolve_unique_relative_path(save_dir, relative_path)
        _log(
            f"[{index}/{item_count}] Receiving {relative_path} "
            f"({format_bytes(filesize)})",
            log_callback,
        )
        _log(f"Saving to {target_path}", log_callback)
        protocol.send_response(conn, protocol.STATUS_READY, "file ready")

        receive_file(
            conn,
            target_path,
            filesize,
            relative_path=relative_path,
            file_index=index,
            file_count=item_count,
            total_before=total_received,
            total_size=total_size,
            progress_callback=progress_callback,
        )
        total_received += filesize
        saved_paths.append(target_path)
        protocol.send_file_done(
            conn,
            index,
            protocol.STATUS_COMPLETE,
            "file received",
            str(target_path),
        )

    end_metadata = protocol.recv_metadata(conn)
    end_count, end_total = protocol.validate_transfer_end_metadata(end_metadata)
    if end_count != item_count or end_total != total_size:
        raise protocol.ProtocolError("TRANSFER_END summary does not match TRANSFER_START")
    if total_received != total_size:
        raise protocol.ProtocolError("received byte total does not match TRANSFER_START")

    protocol.send_response(conn, protocol.STATUS_COMPLETE, "transfer complete")
    _log(f"Transfer complete: {len(saved_paths)} files saved", log_callback)
    return saved_paths


def handle_client(
    conn: socket.socket,
    save_dir: Path,
    *,
    log_callback: LogCallback | None = None,
    progress_callback: ProgressCallback | None = None,
) -> list[Path]:
    metadata = protocol.recv_metadata(conn)
    metadata_type = metadata.get("type")
    if metadata_type == protocol.TYPE_FILE_SEND:
        return _handle_v1_file(
            conn,
            metadata,
            save_dir,
            log_callback=log_callback,
            progress_callback=progress_callback,
        )
    if metadata_type == protocol.TYPE_TRANSFER_START:
        return _handle_v2_transfer(
            conn,
            metadata,
            save_dir,
            log_callback=log_callback,
            progress_callback=progress_callback,
        )

    raise protocol.ProtocolError(f"unsupported metadata type: {metadata_type}")


def run_server(
    host: str = "0.0.0.0",
    port: int = 5001,
    save_dir: Path | str = "received",
    *,
    log_callback: LogCallback | None = None,
    progress_callback: ProgressCallback | None = None,
) -> list[Path]:
    """Run a one-client receive server and return saved file paths."""
    resolved_save_dir = Path(save_dir)
    resolved_save_dir.mkdir(parents=True, exist_ok=True)

    _log(f"Starting server on {host}:{port}", log_callback)
    _log(f"Save directory: {resolved_save_dir}", log_callback)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((host, port))
        server_sock.listen(1)
        _log("Waiting for one client...", log_callback)

        conn, addr = server_sock.accept()
        with conn:
            _log(f"Connected by {addr[0]}:{addr[1]}", log_callback)
            try:
                saved_paths = handle_client(
                    conn,
                    resolved_save_dir,
                    log_callback=log_callback,
                    progress_callback=progress_callback,
                )
            except Exception as exc:
                try:
                    protocol.send_response(conn, protocol.STATUS_ERROR, str(exc))
                except Exception:
                    pass
                raise

    return saved_paths


def main() -> None:
    args = parse_args()

    try:
        saved_paths = run_server(args.host, args.port, args.save_dir)
        for saved_path in saved_paths:
            print(f"Receive complete: {saved_path}")
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
    except Exception as exc:
        print(f"Server error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
