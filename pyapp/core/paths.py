from __future__ import annotations

import os
import sys
from pathlib import Path


def runtime_root() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root)

    return Path(__file__).resolve().parents[2]


def resource_path(*parts: str) -> Path:
    return runtime_root().joinpath(*parts)


def _is_executable_file(file_path: Path) -> bool:
    return file_path.is_file() and os.access(file_path, os.X_OK)


def resolve_tool_path(
    tool_name: str,
    *,
    env: dict[str, str] | None = None,
    extra_search_dirs: list[str] | None = None,
) -> str:
    if not isinstance(tool_name, str) or not tool_name:
        raise ValueError("tool_name is required")

    env_map = env or os.environ
    extra_dirs = list(extra_search_dirs or [])
    base_name = Path(tool_name).stem
    env_key = f"{base_name.upper()}_PATH"
    env_value = env_map.get(env_key)

    if env_value:
        env_path = Path(env_value)
        if _is_executable_file(env_path):
            return str(env_path)

    candidate_path = Path(tool_name)
    if (candidate_path.is_absolute() or candidate_path.parent != Path(".")) and _is_executable_file(candidate_path):
        return str(candidate_path)

    search_dirs: list[Path] = []
    seen: set[str] = set()

    def add_dir(directory: str | Path | None) -> None:
        if not directory:
            return
        directory_path = Path(directory)
        key = str(directory_path)
        if key in seen:
            return
        seen.add(key)
        search_dirs.append(directory_path)

    for directory in extra_dirs:
        add_dir(directory)

    add_dir(resource_path("resources", "bin", platform_dir_name()))
    add_dir(resource_path("resources", "bin"))

    for entry in env_map.get("PATH", "").split(os.pathsep):
        add_dir(entry)

    candidate_names = [base_name]
    if sys.platform.startswith("win"):
        candidate_names = [base_name, f"{base_name}.exe", f"{base_name}.cmd", f"{base_name}.bat"]

    for directory in search_dirs:
        for candidate_name in candidate_names:
            candidate = directory / candidate_name
            if _is_executable_file(candidate):
                return str(candidate)

    raise ValueError(f"Unable to locate {base_name}. Set {env_key} or install it in PATH.")


def platform_dir_name() -> str:
    if sys.platform == "darwin":
        return "darwin"
    if sys.platform.startswith("win"):
        return "win32"
    return "linux"
