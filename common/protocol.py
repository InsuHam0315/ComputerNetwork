"""Shared TCP protocol helpers for ConnectBox.

Wire format for every metadata message:
    4 bytes: unsigned big-endian JSON byte length
    N bytes: UTF-8 encoded JSON object

Protocol v1, kept for MVP compatibility:
    FILE_SEND -> READY -> file bytes -> COMPLETE/ERROR

Protocol v2, used for multi-file and folder transfer sessions:
    TRANSFER_START -> READY
    (FILE_ITEM -> READY -> file bytes -> FILE_DONE) * item_count
    TRANSFER_END -> COMPLETE/ERROR
"""

from __future__ import annotations

import json
import socket
import struct
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


ENCODING = "utf-8"
LENGTH_FORMAT = "!I"
LENGTH_SIZE = struct.calcsize(LENGTH_FORMAT)
MAX_METADATA_SIZE = 64 * 1024

TYPE_FILE_SEND = "FILE_SEND"
TYPE_RESPONSE = "RESPONSE"
TYPE_TRANSFER_START = "TRANSFER_START"
TYPE_FILE_ITEM = "FILE_ITEM"
TYPE_FILE_DONE = "FILE_DONE"
TYPE_TRANSFER_END = "TRANSFER_END"

PROTOCOL_VERSION_V2 = 2

STATUS_READY = "READY"
STATUS_COMPLETE = "COMPLETE"
STATUS_ERROR = "ERROR"

VALID_RESPONSE_STATUSES = {STATUS_READY, STATUS_COMPLETE, STATUS_ERROR}
VALID_DONE_STATUSES = {STATUS_COMPLETE, STATUS_ERROR}


class ProtocolError(Exception):
    """Raised when a peer sends invalid or incomplete protocol data."""


@dataclass(frozen=True)
class TransferItem:
    """One file entry in a v2 transfer session."""

    path: Path
    relative_path: str
    filesize: int


def recv_exact(sock: socket.socket, size: int) -> bytes:
    """Receive exactly size bytes or raise ProtocolError."""
    if size < 0:
        raise ValueError("size must be non-negative")

    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            raise ProtocolError("connection closed before expected bytes arrived")
        chunks.extend(chunk)
    return bytes(chunks)


def send_metadata(sock: socket.socket, metadata: dict[str, Any]) -> None:
    """Send a length-prefixed JSON metadata object."""
    payload = json.dumps(metadata, ensure_ascii=False, separators=(",", ":")).encode(
        ENCODING
    )
    if len(payload) > MAX_METADATA_SIZE:
        raise ProtocolError("metadata is too large")

    sock.sendall(struct.pack(LENGTH_FORMAT, len(payload)))
    sock.sendall(payload)


def recv_metadata(sock: socket.socket) -> dict[str, Any]:
    """Receive and decode a length-prefixed JSON metadata object."""
    length_bytes = recv_exact(sock, LENGTH_SIZE)
    (payload_size,) = struct.unpack(LENGTH_FORMAT, length_bytes)

    if payload_size == 0:
        raise ProtocolError("metadata length cannot be zero")
    if payload_size > MAX_METADATA_SIZE:
        raise ProtocolError("metadata is too large")

    payload = recv_exact(sock, payload_size)
    try:
        metadata = json.loads(payload.decode(ENCODING))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("metadata is not valid UTF-8 JSON") from exc

    if not isinstance(metadata, dict):
        raise ProtocolError("metadata must be a JSON object")
    return metadata


def build_file_metadata(file_path: Path) -> dict[str, Any]:
    """Build v1 FILE_SEND metadata for one regular file."""
    path = Path(file_path)
    if not path.is_file():
        raise ProtocolError("only a single regular file can be sent")

    return {
        "type": TYPE_FILE_SEND,
        "filename": path.name,
        "filesize": path.stat().st_size,
    }


def validate_file_metadata(metadata: dict[str, Any]) -> tuple[str, int]:
    """Validate v1 FILE_SEND metadata and return (filename, filesize)."""
    if metadata.get("type") != TYPE_FILE_SEND:
        raise ProtocolError("metadata type must be FILE_SEND")

    filename = metadata.get("filename")
    filesize = metadata.get("filesize")

    if not isinstance(filename, str) or not filename:
        raise ProtocolError("filename must be a non-empty string")
    if Path(filename).name != filename:
        raise ProtocolError("filename must not contain a path")
    if not isinstance(filesize, int) or filesize < 0:
        raise ProtocolError("filesize must be a non-negative integer")

    return filename, filesize


def normalize_relative_path(relative_path: str) -> str:
    """Return a safe POSIX relative path or raise ProtocolError.

    The protocol stores relative paths with forward slashes so folder transfers
    restore the same tree on Windows, macOS, or Linux. Absolute paths, parent
    traversal, drive prefixes, and empty path parts are rejected.
    """
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ProtocolError("relative_path must be a non-empty string")

    normalized = relative_path.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute():
        raise ProtocolError("relative_path must not be absolute")

    parts = path.parts
    if not parts:
        raise ProtocolError("relative_path must not be empty")

    for part in parts:
        if part in {"", ".", ".."}:
            raise ProtocolError("relative_path must not contain empty/current/parent parts")
        if ":" in part:
            raise ProtocolError("relative_path must not contain drive prefixes")
        if "\x00" in part:
            raise ProtocolError("relative_path must not contain NUL bytes")

    return "/".join(parts)


def relative_path_parts(relative_path: str) -> tuple[str, ...]:
    """Return normalized relative path parts safe for joining under save_dir."""
    return PurePosixPath(normalize_relative_path(relative_path)).parts


def build_transfer_start_metadata(item_count: int, total_size: int) -> dict[str, Any]:
    """Build v2 transfer-session start metadata."""
    if item_count <= 0:
        raise ProtocolError("item_count must be greater than zero")
    if total_size < 0:
        raise ProtocolError("total_size must be non-negative")

    return {
        "type": TYPE_TRANSFER_START,
        "version": PROTOCOL_VERSION_V2,
        "item_count": item_count,
        "total_size": total_size,
    }


def validate_transfer_start_metadata(metadata: dict[str, Any]) -> tuple[int, int]:
    """Validate TRANSFER_START metadata and return (item_count, total_size)."""
    if metadata.get("type") != TYPE_TRANSFER_START:
        raise ProtocolError("metadata type must be TRANSFER_START")
    if metadata.get("version") != PROTOCOL_VERSION_V2:
        raise ProtocolError("unsupported transfer protocol version")

    item_count = metadata.get("item_count")
    total_size = metadata.get("total_size")
    if not isinstance(item_count, int) or item_count <= 0:
        raise ProtocolError("item_count must be a positive integer")
    if not isinstance(total_size, int) or total_size < 0:
        raise ProtocolError("total_size must be a non-negative integer")

    return item_count, total_size


def build_file_item_metadata(
    index: int, relative_path: str, filesize: int
) -> dict[str, Any]:
    """Build v2 metadata for one file item."""
    if index <= 0:
        raise ProtocolError("file item index must be greater than zero")
    if filesize < 0:
        raise ProtocolError("filesize must be non-negative")

    safe_relative_path = normalize_relative_path(relative_path)
    filename = PurePosixPath(safe_relative_path).name
    return {
        "type": TYPE_FILE_ITEM,
        "index": index,
        "filename": filename,
        "relative_path": safe_relative_path,
        "filesize": filesize,
    }


def validate_file_item_metadata(metadata: dict[str, Any]) -> tuple[int, str, int]:
    """Validate FILE_ITEM metadata and return (index, relative_path, filesize)."""
    if metadata.get("type") != TYPE_FILE_ITEM:
        raise ProtocolError("metadata type must be FILE_ITEM")

    index = metadata.get("index")
    relative_path = metadata.get("relative_path")
    filesize = metadata.get("filesize")

    if not isinstance(index, int) or index <= 0:
        raise ProtocolError("file item index must be a positive integer")
    if not isinstance(filesize, int) or filesize < 0:
        raise ProtocolError("filesize must be a non-negative integer")

    safe_relative_path = normalize_relative_path(relative_path)
    filename = metadata.get("filename", PurePosixPath(safe_relative_path).name)
    if not isinstance(filename, str) or not filename:
        raise ProtocolError("filename must be a non-empty string")
    if PurePosixPath(safe_relative_path).name != filename:
        raise ProtocolError("filename must match the relative_path leaf name")

    return index, safe_relative_path, filesize


def build_transfer_end_metadata(item_count: int, total_size: int) -> dict[str, Any]:
    """Build v2 transfer-session end metadata."""
    if item_count <= 0:
        raise ProtocolError("item_count must be greater than zero")
    if total_size < 0:
        raise ProtocolError("total_size must be non-negative")

    return {
        "type": TYPE_TRANSFER_END,
        "version": PROTOCOL_VERSION_V2,
        "item_count": item_count,
        "total_size": total_size,
    }


def validate_transfer_end_metadata(metadata: dict[str, Any]) -> tuple[int, int]:
    """Validate TRANSFER_END metadata and return (item_count, total_size)."""
    if metadata.get("type") != TYPE_TRANSFER_END:
        raise ProtocolError("metadata type must be TRANSFER_END")
    if metadata.get("version") != PROTOCOL_VERSION_V2:
        raise ProtocolError("unsupported transfer protocol version")

    item_count = metadata.get("item_count")
    total_size = metadata.get("total_size")
    if not isinstance(item_count, int) or item_count <= 0:
        raise ProtocolError("item_count must be a positive integer")
    if not isinstance(total_size, int) or total_size < 0:
        raise ProtocolError("total_size must be a non-negative integer")

    return item_count, total_size


def send_response(sock: socket.socket, status: str, message: str = "") -> None:
    """Send a protocol response with status READY, COMPLETE, or ERROR."""
    if status not in VALID_RESPONSE_STATUSES:
        raise ValueError(f"invalid response status: {status}")

    response = {"type": TYPE_RESPONSE, "status": status}
    if message:
        response["message"] = message
    send_metadata(sock, response)


def recv_response(sock: socket.socket) -> dict[str, Any]:
    """Receive and validate a protocol response."""
    response = recv_metadata(sock)
    if response.get("type") != TYPE_RESPONSE:
        raise ProtocolError("response type must be RESPONSE")

    status = response.get("status")
    if status not in VALID_RESPONSE_STATUSES:
        raise ProtocolError("response status is invalid")

    message = response.get("message", "")
    if not isinstance(message, str):
        raise ProtocolError("response message must be a string")

    return response


def send_file_done(
    sock: socket.socket,
    index: int,
    status: str = STATUS_COMPLETE,
    message: str = "",
    saved_path: str = "",
) -> None:
    """Send a v2 per-file completion message."""
    if index <= 0:
        raise ValueError("index must be greater than zero")
    if status not in VALID_DONE_STATUSES:
        raise ValueError(f"invalid file done status: {status}")

    metadata: dict[str, Any] = {
        "type": TYPE_FILE_DONE,
        "index": index,
        "status": status,
    }
    if message:
        metadata["message"] = message
    if saved_path:
        metadata["saved_path"] = saved_path
    send_metadata(sock, metadata)


def recv_file_done(sock: socket.socket) -> dict[str, Any]:
    """Receive and validate a v2 FILE_DONE message."""
    metadata = recv_metadata(sock)
    if metadata.get("type") == TYPE_RESPONSE and metadata.get("status") == STATUS_ERROR:
        message = metadata.get("message", "")
        raise ProtocolError(f"server error: {message}")
    if metadata.get("type") != TYPE_FILE_DONE:
        raise ProtocolError("metadata type must be FILE_DONE")

    index = metadata.get("index")
    status = metadata.get("status")
    message = metadata.get("message", "")
    saved_path = metadata.get("saved_path", "")

    if not isinstance(index, int) or index <= 0:
        raise ProtocolError("FILE_DONE index must be a positive integer")
    if status not in VALID_DONE_STATUSES:
        raise ProtocolError("FILE_DONE status is invalid")
    if not isinstance(message, str):
        raise ProtocolError("FILE_DONE message must be a string")
    if not isinstance(saved_path, str):
        raise ProtocolError("FILE_DONE saved_path must be a string")

    return metadata
