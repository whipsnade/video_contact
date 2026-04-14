from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .paths import resolve_tool_path

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def detect_media_type_from_path(file_path: str) -> str:
    extension = Path(str(file_path or "")).suffix.lower()

    if extension in VIDEO_EXTENSIONS:
        return "video"
    if extension in IMAGE_EXTENSIONS:
        return "image"

    raise ValueError(f"Unsupported media type for path: {file_path}")


def parse_fraction(value: str | None) -> float | None:
    if not value or not isinstance(value, str):
        return None

    numerator, _, denominator = value.partition("/")
    try:
        num = float(numerator)
        den = float(denominator)
    except ValueError:
        return None

    if den == 0:
        return None

    return num / den


def parse_timecode(value: str | None) -> float | None:
    if not value or not isinstance(value, str):
        return None

    parts = value.strip().split(":")
    if len(parts) != 3:
        return None

    try:
        hours = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
    except ValueError:
        return None

    return (hours * 3600) + (minutes * 60) + seconds


def parse_ffprobe_payload(payload: dict[str, object], media_type: str | None = None) -> dict[str, object]:
    streams = payload.get("streams") or []
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)

    if not video_stream:
        raise ValueError("No video stream found in source file")

    format_data = payload.get("format") or {}
    duration_value = video_stream.get("duration") or format_data.get("duration")
    try:
        duration_seconds = float(duration_value) if duration_value is not None else 0.0
    except (TypeError, ValueError):
        duration_seconds = 0.0

    normalized_duration = duration_seconds if duration_seconds > 0 else None
    fps = parse_fraction(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate"))
    media_kind = media_type or "video"
    has_audio = media_kind == "video" and any(stream.get("codec_type") == "audio" for stream in streams)

    return {
        "media_type": media_kind,
        "source_width": video_stream["width"],
        "source_height": video_stream["height"],
        "duration_seconds": normalized_duration,
        "fps": fps if media_kind == "video" else None,
        "has_audio": has_audio,
        "format_name": format_data.get("format_name"),
        "codec_name": video_stream.get("codec_name"),
    }


def probe_media(
    file_path: str,
    *,
    ffprobe_path: str | None = None,
    env: dict[str, str] | None = None,
    extra_search_dirs: list[str] | None = None,
) -> dict[str, object]:
    if not isinstance(file_path, str) or not file_path:
        raise ValueError("file_path is required")

    media_type = detect_media_type_from_path(file_path)
    resolved_ffprobe = resolve_tool_path(ffprobe_path or "ffprobe", env=env, extra_search_dirs=extra_search_dirs)
    result = subprocess.run(
        [
            resolved_ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            file_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    return parse_ffprobe_payload(payload, media_type=media_type)
