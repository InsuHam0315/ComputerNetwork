"""Shared TCP protocol helpers for the file transfer MVP.

Wire format for metadata messages:
    4 bytes: unsigned big-endian JSON byte length
    N bytes: UTF-8 encoded JSON object

For file transfer, the sender transmits one FILE_SEND metadata message
followed by exactly ``filesize`` bytes of file body.
"""

from __future__ import annotations

import json
import socket
import struct
from pathlib import Path
from typing import Any


ENCODING = "utf-8"
LENGTH_FORMAT = "!I"
LENGTH_SIZE = struct.calcsize(LENGTH_FORMAT)
MAX_METADATA_SIZE = 64 * 1024

TYPE_FILE_SEND = "FILE_SEND"
TYPE_RESPONSE = "RESPONSE"

STATUS_READY = "READY"
STATUS_COMPLETE = "COMPLETE"
STATUS_ERROR = "ERROR"

VALID_RESPONSE_STATUSES = {STATUS_READY, STATUS_COMPLETE, STATUS_ERROR}


class ProtocolError(Exception):
    """Raised when a peer sends invalid or incomplete protocol data."""


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
    """Build FILE_SEND metadata for one regular file."""
    path = Path(file_path)
    if not path.is_file():
        raise ProtocolError("only a single regular file can be sent")

    return {
        "type": TYPE_FILE_SEND,
        "filename": path.name,
        "filesize": path.stat().st_size,
    }


def validate_file_metadata(metadata: dict[str, Any]) -> tuple[str, int]:
    """Validate FILE_SEND metadata and return (filename, filesize)."""
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
