import os
from pathlib import Path

from pyapp.core.packaging import (
    build_pyinstaller_args,
    bundle_executable_name,
    bundle_output_name,
    bundle_tool_destination,
    release_archive_base_name,
    release_archive_name,
)


def test_bundle_tool_destination_uses_platform_directory():
    assert bundle_tool_destination("darwin") == "resources/bin/darwin"
    assert bundle_tool_destination("win32") == "resources/bin/win32"


def test_bundle_output_name_matches_platform_convention():
    assert bundle_output_name("Video Grid Compositor", "darwin") == "Video Grid Compositor.app"
    assert bundle_output_name("Video Grid Compositor", "win32") == "Video Grid Compositor"


def test_bundle_executable_name_matches_platform_convention():
    assert bundle_executable_name("Video Grid Compositor", "win32") == "Video Grid Compositor.exe"
    assert bundle_executable_name("Video Grid Compositor", "darwin") == "Video Grid Compositor"


def test_release_archive_name_is_platform_specific():
    assert release_archive_name("Video Grid Compositor", "darwin") == "Video Grid Compositor-macos.zip"
    assert release_archive_name("Video Grid Compositor", "win32") == "Video Grid Compositor-windows.zip"


def test_release_archive_base_name_strips_zip_suffix():
    assert release_archive_base_name("Video Grid Compositor", "darwin") == "Video Grid Compositor-macos"
    assert release_archive_base_name("Video Grid Compositor", "win32") == "Video Grid Compositor-windows"


def test_build_pyinstaller_args_includes_theme_and_bundled_tools(tmp_path):
    args = build_pyinstaller_args(
        entry_point=tmp_path / "pyapp" / "main.py",
        theme_source=tmp_path / "pyapp" / "ui" / "theme.qss",
        ffmpeg_path=Path("/opt/homebrew/bin/ffmpeg"),
        ffprobe_path=Path("/opt/homebrew/bin/ffprobe"),
        platform_name="darwin",
        distpath=tmp_path / "dist",
        workpath=tmp_path / "build",
    )

    joined = " ".join(args)
    assert "--onedir" in args
    assert "--windowed" in args
    assert "--clean" in args
    assert "--name" in args
    assert "Video Grid Compositor" in args
    assert f"{tmp_path / 'pyapp' / 'ui' / 'theme.qss'}{os.pathsep}pyapp/ui" in args
    assert f"/opt/homebrew/bin/ffmpeg{os.pathsep}resources/bin/darwin" in args
    assert f"/opt/homebrew/bin/ffprobe{os.pathsep}resources/bin/darwin" in args
    assert str(tmp_path / "dist") in args
    assert str(tmp_path / "build") in args
    assert str(tmp_path / "pyapp" / "main.py") in args
    assert "PyInstaller" not in joined


def test_build_pyinstaller_args_can_build_onefile_executable(tmp_path):
    args = build_pyinstaller_args(
        entry_point=tmp_path / "pyapp" / "main.py",
        theme_source=tmp_path / "pyapp" / "ui" / "theme.qss",
        ffmpeg_path=Path("/opt/homebrew/bin/ffmpeg"),
        ffprobe_path=Path("/opt/homebrew/bin/ffprobe"),
        platform_name="win32",
        distpath=tmp_path / "dist",
        workpath=tmp_path / "build",
        onefile=True,
    )

    assert "--onefile" in args
    assert "--onedir" not in args
