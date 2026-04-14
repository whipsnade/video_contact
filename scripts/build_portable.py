from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyapp.core.errors import format_user_facing_error
from pyapp.core.packaging import (
    APP_NAME,
    build_pyinstaller_args,
    bundle_executable_name,
    bundle_output_name,
    release_archive_base_name,
    release_archive_name,
)
from pyapp.core.paths import resolve_tool_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a portable PySide6 bundle with embedded ffmpeg tools.")
    parser.add_argument("--ffmpeg", help="Path to ffmpeg binary. Defaults to FFMPEG_PATH or PATH lookup.")
    parser.add_argument("--ffprobe", help="Path to ffprobe binary. Defaults to FFPROBE_PATH or PATH lookup.")
    parser.add_argument("--distpath", default="dist/portable", help="PyInstaller dist directory.")
    parser.add_argument("--workpath", default="build/portable", help="PyInstaller build directory.")
    parser.add_argument("--entry-point", default="pyapp/main.py", help="Application entry point.")
    parser.add_argument("--theme-source", default="pyapp/ui/theme.qss", help="Qt stylesheet source file.")
    parser.add_argument("--release-dir", default="release", help="Directory for optional zip archives.")
    parser.add_argument("--app-name", default=APP_NAME, help="Application display name used by PyInstaller.")
    parser.add_argument("--onefile", action="store_true", help="Build a single-file executable instead of a bundle directory.")
    parser.add_argument("--no-clean", action="store_true", help="Skip PyInstaller --clean.")
    parser.add_argument("--zip", action="store_true", help="Create a zip archive of the built bundle.")
    parser.add_argument(
        "--search-dir",
        action="append",
        default=[],
        help="Additional directory to search for ffmpeg/ffprobe before falling back to PATH.",
    )
    return parser


def _resolve_tool(tool_name: str, override: str | None, search_dirs: list[str]) -> str:
    if override:
        override_path = Path(override).expanduser()
        if override_path.is_file() and os.access(override_path, os.X_OK):
            return str(override_path)
        raise SystemExit(format_user_facing_error("打包", ValueError(f"Unable to locate {tool_name} at {override}")))

    try:
        return resolve_tool_path(tool_name, extra_search_dirs=search_dirs)
    except ValueError as exc:
        raise SystemExit(format_user_facing_error("打包", exc)) from exc


def _find_bundle_path(distpath: Path, app_name: str, *, onefile: bool = False) -> Path:
    candidates: list[Path] = []
    if onefile:
        candidates.extend(
            [
                distpath / bundle_executable_name(app_name),
                distpath / f"{app_name}.exe",
                distpath / app_name,
            ]
        )
    else:
        candidates.extend(
            [
                distpath / bundle_output_name(app_name),
                distpath / app_name,
            ]
        )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    if onefile:
        candidates = sorted(distpath.glob(f"{app_name}*"))
        if candidates:
            return candidates[0]
    else:
        candidates = sorted(distpath.glob(f"{app_name}*"))
        if candidates:
            return candidates[0]

    raise FileNotFoundError(f"Bundle not found in {distpath}")


def _zip_bundle(bundle_path: Path, release_dir: Path, app_name: str) -> Path:
    release_dir.mkdir(parents=True, exist_ok=True)
    archive_name = release_archive_name(app_name)
    archive_base = release_dir / release_archive_base_name(app_name)
    archive_path = release_dir / archive_name
    if archive_path.exists():
        archive_path.unlink()

    shutil.make_archive(
        base_name=str(archive_base),
        format="zip",
        root_dir=str(bundle_path.parent),
        base_dir=bundle_path.name,
    )
    return archive_path


def _prepare_output_tree(distpath: Path, app_name: str) -> None:
    for candidate in {
        distpath / app_name,
        distpath / f"{app_name}.exe",
        distpath / bundle_output_name(app_name),
    }:
        if candidate.exists():
            if candidate.is_dir():
                shutil.rmtree(candidate)
            else:
                candidate.unlink()


def _build_pyinstaller_env(project_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYINSTALLER_CONFIG_DIR"] = str(project_root / ".pyinstaller-config")
    return env


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    project_root = Path(__file__).resolve().parents[1]
    distpath = Path(args.distpath).expanduser().resolve()
    workpath = Path(args.workpath).expanduser().resolve()
    entry_point = (project_root / args.entry_point).resolve()
    theme_source = (project_root / args.theme_source).resolve()

    ffmpeg_path = _resolve_tool("ffmpeg", args.ffmpeg, args.search_dir)
    ffprobe_path = _resolve_tool("ffprobe", args.ffprobe, args.search_dir)
    _prepare_output_tree(distpath, args.app_name)

    pyinstaller_args = build_pyinstaller_args(
        entry_point=entry_point,
        theme_source=theme_source,
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
        app_name=args.app_name,
        distpath=distpath,
        workpath=workpath,
        clean=not args.no_clean,
        onefile=args.onefile,
    )

    command = [sys.executable, "-m", "PyInstaller", *pyinstaller_args]
    print("正在打包便携版...")
    subprocess.run(command, check=True, cwd=str(project_root), env=_build_pyinstaller_env(project_root))

    bundle_path = _find_bundle_path(distpath, args.app_name, onefile=args.onefile)
    print(f"打包完成：{bundle_path}")

    if args.zip:
        archive_path = _zip_bundle(bundle_path, Path(args.release_dir).expanduser().resolve(), args.app_name)
        print(f"压缩包已生成：{archive_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
