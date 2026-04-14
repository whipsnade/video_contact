from __future__ import annotations

from pathlib import Path

from .layout import validate_grid_config
from .media import detect_media_type_from_path
from .order import build_default_order

ASPECT_PRESETS = {
    "16:9": {"width": 1920, "height": 1080},
    "4:3": {"width": 1440, "height": 1080},
    "1:1": {"width": 1080, "height": 1080},
    "9:16": {"width": 1080, "height": 1920},
}


def media_badge_text(media_type: str | None) -> str:
    if media_type == "image":
        return "图片输入"
    if media_type == "video":
        return "视频输入"
    return "等待输入"


def export_button_text(media_type: str | None) -> str:
    if media_type == "image":
        return "开始生成图片"
    if media_type == "video":
        return "开始导出视频"
    return "开始导出"


def quality_note_text(media_type: str | None, export_mode: str | None) -> str:
    if media_type == "image":
        return "图片导出固定为高质量 JPG，不参与视频质量档位设置。"

    quality_label = {
        "lossless": "无损",
        "high": "高质量",
        "medium": "中质量",
    }.get(export_mode or "lossless", "无损")

    return f"{quality_label}视频会按当前切片和舞台顺序导出；图片导出固定为高质量 JPG。"


def reset_slice_order(slice_count: int) -> list[int]:
    return build_default_order(slice_count)


def suggest_output_path(
    *,
    source_path: str,
    media_type: str | None,
    slice_count: int,
    rows: int,
    cols: int,
    output_width: int,
    output_height: int,
) -> str:
    if not source_path:
        return ""

    source = Path(source_path)
    suffix = f"{slice_count}slice-{rows}x{cols}-{output_width}x{output_height}"
    extension = ".jpg" if media_type == "image" else ".mp4"
    return str(source.with_name(f"{source.stem}-{suffix}{extension}"))


def build_validation_errors(config: dict[str, object]) -> list[str]:
    errors: list[str] = []
    source_path = config.get("source_path")
    source_info = config.get("source_info") or {}
    output_path = config.get("output_path")
    media_type = config.get("media_type")
    aspect_preset = config.get("aspect_preset", "16:9")
    slice_count = config.get("slice_count")
    rows = config.get("rows")
    cols = config.get("cols")
    output_width = config.get("output_width")
    output_height = config.get("output_height")

    if not source_path:
        errors.append("请选择输入文件。")

    if not source_info:
        errors.append("需要先读取媒体元数据。")

    grid_validation = validate_grid_config(
        {
            "slice_count": slice_count if isinstance(slice_count, int) else 0,
            "rows": rows if isinstance(rows, int) else 0,
            "cols": cols if isinstance(cols, int) else 0,
            "output_width": output_width if isinstance(output_width, int) else 0,
            "output_height": output_height if isinstance(output_height, int) else 0,
        }
    )
    errors.extend(grid_validation["errors"])

    if (
        isinstance(aspect_preset, str)
        and aspect_preset != "custom"
        and aspect_preset in ASPECT_PRESETS
        and isinstance(output_width, int)
        and isinstance(output_height, int)
    ):
        preset = ASPECT_PRESETS[aspect_preset]
        if output_width * preset["height"] != output_height * preset["width"]:
            errors.append(f"output resolution must match {aspect_preset}")

    if isinstance(source_info, dict) and isinstance(slice_count, int):
        source_width = source_info.get("source_width")
        if isinstance(source_width, int) and slice_count > source_width:
            errors.append("slice_count cannot exceed source width")

    resolved_media_type = media_type
    if not resolved_media_type and isinstance(source_path, str):
        try:
            resolved_media_type = detect_media_type_from_path(source_path)
        except ValueError:
            resolved_media_type = None

    if not output_path:
        errors.append("请选择导出路径。")
    elif resolved_media_type == "image" and not str(output_path).lower().endswith((".jpg", ".jpeg")):
        errors.append("图片导出路径必须使用 JPG 扩展名。")
    elif resolved_media_type == "video" and not str(output_path).lower().endswith(".mp4"):
        errors.append("视频导出路径必须使用 MP4 扩展名。")

    return errors

