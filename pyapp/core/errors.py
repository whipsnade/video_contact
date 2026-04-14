from __future__ import annotations

from .paths import platform_dir_name


def _detect_tool_name(exc: Exception, explicit_tool_name: str | None = None) -> str | None:
    if explicit_tool_name:
        return explicit_tool_name

    pieces = [str(exc)]
    filename = getattr(exc, "filename", None)
    if isinstance(filename, str):
        pieces.append(filename)

    haystack = " ".join(part for part in pieces if part).lower()
    if "ffprobe" in haystack:
        return "ffprobe"
    if "ffmpeg" in haystack:
        return "ffmpeg"
    return None


def format_user_facing_error(action: str, exc: Exception, *, tool_name: str | None = None) -> str:
    action_text = action.strip() if isinstance(action, str) else ""
    action_text = action_text or "操作"

    detected_tool_name = _detect_tool_name(exc, tool_name)
    if detected_tool_name:
        env_key = f"{detected_tool_name.upper()}_PATH"
        return (
            f"{action_text}失败：未找到 {detected_tool_name}。"
            f"请确认 {env_key} 已设置，或将 {detected_tool_name} 放入 PATH，"
            f"或者放入便携包的 resources/bin/{platform_dir_name()}/ 目录。"
        )

    message = str(exc).strip()
    if message:
        return f"{action_text}失败：{message}"

    return f"{action_text}失败。"
