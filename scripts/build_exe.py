"""Build Windows executables for ConnectBox with PyInstaller.

PyInstaller is intentionally not a project dependency. Install it only on the
packaging PC when an exe build is needed:

    python -m pip install pyinstaller
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BuildTarget:
    key: str
    name: str
    entry: Path
    windowed: bool = False


TARGETS = {
    "gui": BuildTarget("gui", "ConnectBox", Path("gui/connectbox_gui.py"), True),
    "client": BuildTarget("client", "ConnectBoxClient", Path("client/client_main.py")),
    "server": BuildTarget("server", "ConnectBoxServer", Path("server/server_main.py")),
}

GUI_ICON = Path("assets/connectbox_icon.ico")
GUI_ASSETS = (
    Path("assets/connectbox_logo.png"),
    Path("assets/connectbox_icon.ico"),
    Path("assets/connectbox_icon.png"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build ConnectBox Windows exe files.")
    parser.add_argument(
        "--target",
        choices=["all", *TARGETS.keys()],
        default="all",
        help="build target (default: all)",
    )
    parser.add_argument(
        "--onedir",
        action="store_true",
        help="build one-folder apps instead of one-file executables",
    )
    return parser.parse_args()


def ensure_pyinstaller() -> bool:
    try:
        __import__("PyInstaller")
    except ImportError:
        print("PyInstaller is not installed.")
        print("Install only on the packaging PC:")
        print("  python -m pip install pyinstaller")
        return False
    return True


def build_target(project_root: Path, target: BuildTarget, onefile: bool) -> None:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--name",
        target.name,
    ]
    if onefile:
        command.append("--onefile")
    if target.windowed:
        command.append("--windowed")
    if target.key == "gui":
        icon_path = project_root / GUI_ICON
        if icon_path.exists():
            command.extend(["--icon", str(GUI_ICON)])
        for asset_path in GUI_ASSETS:
            if (project_root / asset_path).exists():
                command.extend(["--add-data", f"{asset_path}{os.pathsep}assets"])
    command.append(str(target.entry))

    print(f"Building {target.name} from {target.entry}...")
    subprocess.run(command, cwd=project_root, check=True)


def main() -> int:
    args = parse_args()
    if not ensure_pyinstaller():
        return 1

    project_root = Path(__file__).resolve().parents[1]
    selected_targets = TARGETS.values() if args.target == "all" else [TARGETS[args.target]]
    onefile = not args.onedir

    for target in selected_targets:
        if not (project_root / target.entry).exists():
            print(f"Missing entry file: {target.entry}", file=sys.stderr)
            return 1
        build_target(project_root, target, onefile)

    print("Build complete. Check the dist/ folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
