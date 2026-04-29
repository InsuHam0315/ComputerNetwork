"""Run a local smoke test for the TCP file-transfer MVP."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


CHUNK_SIZE = 64 * 1024
DEFAULT_PORT = 5001
DEFAULT_SIZE_KB = 100


def non_negative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be an integer") from exc

    if number < 0:
        raise argparse.ArgumentTypeError("value must be zero or greater")
    return number


def tcp_port(value: str) -> int:
    number = non_negative_int(value)
    if not 1 <= number <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return number


def positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a number") from exc

    if number <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return number


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start the local server and client, then verify one file transfer."
    )
    parser.add_argument(
        "--port",
        type=tcp_port,
        default=DEFAULT_PORT,
        help=f"server TCP port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--size-kb",
        type=non_negative_int,
        default=DEFAULT_SIZE_KB,
        help=f"test file size in KiB (default: {DEFAULT_SIZE_KB})",
    )
    parser.add_argument(
        "--startup-wait",
        type=positive_float,
        default=1.0,
        help="seconds to wait after starting the server (default: 1.0)",
    )
    parser.add_argument(
        "--client-timeout",
        type=positive_float,
        default=20.0,
        help="seconds before the client is considered hung (default: 20.0)",
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


def write_text_log(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", errors="replace")


def terminate_process(process: subprocess.Popen[str] | None) -> None:
    if process is None or process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def fail(reason: str, log_dir: Path) -> int:
    print("FAIL")
    print(f"Reason: {reason}")
    print(f"Logs: {log_dir.resolve()}")
    return 1


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    logs_dir = project_root / "logs"
    log_dir = logs_dir / f"smoke_test_{run_id}"
    log_dir.mkdir(parents=True, exist_ok=True)

    testdata_dir = project_root / "testdata"
    sample_path = testdata_dir / "smoke_sample.bin"
    received_root = project_root / "received"
    save_dir = received_root / f"smoke_test_{run_id}"
    received_path = save_dir / sample_path.name
    save_dir.mkdir(parents=True, exist_ok=True)

    server_stdout_path = log_dir / "server_stdout.log"
    server_stderr_path = log_dir / "server_stderr.log"
    client_stdout_path = log_dir / "client_stdout.log"
    client_stderr_path = log_dir / "client_stderr.log"

    server_process: subprocess.Popen[str] | None = None

    try:
        expected_size = create_dummy_file(sample_path, args.size_kb)

        server_cmd = [
            sys.executable,
            "-m",
            "server.server_main",
            "--host",
            "127.0.0.1",
            "--port",
            str(args.port),
            "--save-dir",
            str(save_dir),
        ]
        client_cmd = [
            sys.executable,
            "-m",
            "client.client_main",
            "--host",
            "127.0.0.1",
            "--port",
            str(args.port),
            "--file",
            str(sample_path),
        ]

        print(f"Test file: {sample_path.resolve()} ({expected_size} bytes)")
        print(f"Receive directory: {save_dir.resolve()}")
        print(f"Log directory: {log_dir.resolve()}")

        with server_stdout_path.open("w", encoding="utf-8", errors="replace") as server_stdout:
            with server_stderr_path.open("w", encoding="utf-8", errors="replace") as server_stderr:
                server_process = subprocess.Popen(
                    server_cmd,
                    cwd=project_root,
                    stdout=server_stdout,
                    stderr=server_stderr,
                    text=True,
                )

                time.sleep(args.startup_wait)
                early_server_code = server_process.poll()
                if early_server_code is not None:
                    return fail(
                        "server process exited before the client ran. "
                        "Check server logs for port conflicts, CLI argument mismatch, "
                        "or incomplete server implementation.",
                        log_dir,
                    )

                try:
                    client_result = subprocess.run(
                        client_cmd,
                        cwd=project_root,
                        capture_output=True,
                        text=True,
                        timeout=args.client_timeout,
                    )
                except subprocess.TimeoutExpired as exc:
                    write_text_log(client_stdout_path, exc.stdout or "")
                    write_text_log(client_stderr_path, exc.stderr or "")
                    return fail(
                        "client timed out. The server/client protocol may be waiting "
                        "for a response that never arrives.",
                        log_dir,
                    )

                write_text_log(client_stdout_path, client_result.stdout)
                write_text_log(client_stderr_path, client_result.stderr)

                if client_result.returncode != 0:
                    return fail(
                        f"client exited with code {client_result.returncode}. "
                        "This can indicate a connection failure, protocol mismatch, "
                        "or incomplete client/server implementation.",
                        log_dir,
                    )

                try:
                    server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    return fail(
                        "client finished successfully, but the server did not exit. "
                        "The server may not have completed the transfer cleanly.",
                        log_dir,
                    )

        if not received_path.exists():
            return fail(
                f"received file was not found at {received_path}. "
                "Check whether the server saved to another path or failed after "
                "accepting the client.",
                log_dir,
            )

        received_size = received_path.stat().st_size
        if received_size != expected_size:
            return fail(
                f"size mismatch: source={expected_size} bytes, "
                f"received={received_size} bytes.",
                log_dir,
            )

        print("PASS")
        print(f"Received file: {received_path.resolve()}")
        print(f"Verified size: {received_size} bytes")
        print(f"Logs: {log_dir.resolve()}")
        return 0
    finally:
        terminate_process(server_process)


if __name__ == "__main__":
    raise SystemExit(main())
