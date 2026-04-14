from __future__ import annotations

import os
from pathlib import Path

from .paths import platform_dir_name

APP_NAME = "Video Grid Compositor"
THEME_SOURCE = Path("pyapp/ui/theme.qss")
THEME_DESTINATION = "pyapp/ui"


def bundle_tool_destination(platform_name: str | None = None) -> str:
    return f"resources/bin/{platform_name or platform_dir_name()}"


def _platform_label(platform_name: str | None = None) -> str:
    resolved = platform_name or platform_dir_name()
    if resolved == "darwin":
        return "macos"
    if resolved == "win32":
        return "windows"
    return resolved


def bundle_output_name(app_name: str = APP_NAME, platform_name: str | None = None) -> str:
    if (platform_name or platform_dir_name()) == "darwin":
        return f"{app_name}.app"
    return app_name


def bundle_executable_name(app_name: str = APP_NAME, platform_name: str | None = None) -> str:
    resolved = platform_name or platform_dir_name()
    if resolved == "win32":
        return f"{app_name}.exe"
    return app_name


def release_archive_name(app_name: str = APP_NAME, platform_name: str | None = None) -> str:
    return f"{app_name}-{_platform_label(platform_name)}.zip"


def release_archive_base_name(app_name: str = APP_NAME, platform_name: str | None = None) -> str:
    return f"{app_name}-{_platform_label(platform_name)}"


def _path_arg(source: str | Path, destination: str) -> str:
    return f"{Path(source)}{os.pathsep}{destination}"


def build_pyinstaller_args(
    *,
    entry_point: str | Path,
    theme_source: str | Path = THEME_SOURCE,
    ffmpeg_path: str | Path,
    ffprobe_path: str | Path,
    app_name: str = APP_NAME,
    platform_name: str | None = None,
    distpath: str | Path | None = None,
    workpath: str | Path | None = None,
    clean: bool = True,
    onefile: bool = False,
) -> list[str]:
    args = ["--noconfirm", "--windowed", "--name", app_name]
    args.append("--onefile" if onefile else "--onedir")
    if clean:
        args.append("--clean")
    if distpath is not None:
        args.extend(["--distpath", str(distpath)])
    if workpath is not None:
        args.extend(["--workpath", str(workpath)])

    args.extend(["--add-data", _path_arg(theme_source, THEME_DESTINATION)])
    tool_destination = bundle_tool_destination(platform_name)
    args.extend(["--add-binary", _path_arg(ffmpeg_path, tool_destination)])
    args.extend(["--add-binary", _path_arg(ffprobe_path, tool_destination)])
    args.append(str(entry_point))
    return args
