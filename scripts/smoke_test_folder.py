"""Run a local smoke test for a ConnectBox folder transfer."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


DEFAULT_PORT = 5003


def tcp_port(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
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
        description="Start the local server and client, then verify folder transfer."
    )
    parser.add_argument("--port", type=tcp_port, default=DEFAULT_PORT)
    parser.add_argument("--startup-wait", type=positive_float, default=1.0)
    parser.add_argument("--client-timeout", type=positive_float, default=20.0)
    return parser.parse_args()


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


def create_folder_tree(source_folder: Path) -> dict[Path, bytes]:
    files: dict[Path, bytes] = {
        Path("root.txt"): "root file\n".encode("utf-8"),
        Path("docs/readme.txt"): "folder transfer keeps structure\n".encode("utf-8"),
        Path("data/nested/payload.bin"): (bytes(range(64)) * 16)[:777],
        Path("empty.dat"): b"",
    }
    for relative_path, content in files.items():
        target = source_folder / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return files


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    log_dir = project_root / "logs" / f"smoke_folder_{run_id}"
    source_folder = project_root / "testdata" / f"smoke_folder_{run_id}" / "folder_sample"
    save_dir = project_root / "received" / f"smoke_folder_{run_id}"
    log_dir.mkdir(parents=True, exist_ok=True)
    save_dir.mkdir(parents=True, exist_ok=True)

    server_stdout_path = log_dir / "server_stdout.log"
    server_stderr_path = log_dir / "server_stderr.log"
    client_stdout_path = log_dir / "client_stdout.log"
    client_stderr_path = log_dir / "client_stderr.log"

    server_process: subprocess.Popen[str] | None = None

    try:
        expected = create_folder_tree(source_folder)

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
            "--folder",
            str(source_folder),
        ]

        print(f"Source folder: {source_folder.resolve()}")
        print(f"Receive directory: {save_dir.resolve()}")
        print(f"Log directory: {log_dir.resolve()}")

        with server_stdout_path.open("w", encoding="utf-8", errors="replace") as out:
            with server_stderr_path.open("w", encoding="utf-8", errors="replace") as err:
                server_process = subprocess.Popen(
                    server_cmd,
                    cwd=project_root,
                    stdout=out,
                    stderr=err,
                    text=True,
                )

                time.sleep(args.startup_wait)
                if server_process.poll() is not None:
                    return fail("server exited before client ran", log_dir)

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
                    return fail("client timed out", log_dir)

                write_text_log(client_stdout_path, client_result.stdout)
                write_text_log(client_stderr_path, client_result.stderr)

                if client_result.returncode != 0:
                    return fail(
                        f"client exited with code {client_result.returncode}", log_dir
                    )

                try:
                    server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    return fail("server did not exit after client completed", log_dir)

        for relative_path, expected_bytes in expected.items():
            received_path = save_dir / source_folder.name / relative_path
            if not received_path.exists():
                return fail(f"missing received file: {received_path}", log_dir)
            if received_path.read_bytes() != expected_bytes:
                return fail(f"content mismatch: {received_path}", log_dir)

        print("PASS")
        print(f"Verified folder files: {len(expected)}")
        print(f"Logs: {log_dir.resolve()}")
        return 0
    finally:
        terminate_process(server_process)


if __name__ == "__main__":
    raise SystemExit(main())
