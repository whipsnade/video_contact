from __future__ import annotations

from .order import build_default_order


def _ensure_positive_integer(value: int, name: str) -> None:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def distribute_dimension(total: int, parts: int) -> list[int]:
    _ensure_positive_integer(total, "total")
    _ensure_positive_integer(parts, "parts")

    if parts > total:
        raise ValueError("parts cannot exceed total")

    base, remainder = divmod(total, parts)
    return [base + (1 if index < remainder else 0) for index in range(parts)]


def distribute_slice_widths(source_width: int, slice_count: int) -> list[int]:
    return distribute_dimension(source_width, slice_count)


def build_slice_plan(source_width: int, slice_count: int) -> list[dict[str, int | str]]:
    widths = distribute_slice_widths(source_width, slice_count)
    plan: list[dict[str, int | str]] = []
    x = 0

    for index, width in enumerate(widths):
        plan.append(
            {
                "index": index,
                "x": x,
                "width": width,
                "label": f"s{index}",
            }
        )
        x += width

    return plan


def validate_grid_config(config: dict[str, int]) -> dict[str, object]:
    errors: list[str] = []
    slice_count = config.get("slice_count")
    rows = config.get("rows")
    cols = config.get("cols")
    output_width = config.get("output_width")
    output_height = config.get("output_height")

    for name, value in (
        ("slice_count", slice_count),
        ("rows", rows),
        ("cols", cols),
        ("output_width", output_width),
        ("output_height", output_height),
    ):
        if not isinstance(value, int) or value <= 0:
            errors.append(f"{name} must be a positive integer")

    if (
        isinstance(slice_count, int)
        and isinstance(rows, int)
        and isinstance(cols, int)
        and rows * cols != slice_count
    ):
        errors.append("rows × cols must equal slice_count")

    if isinstance(output_width, int) and output_width % 2 != 0:
        errors.append("output_width must be even")

    if isinstance(output_height, int) and output_height % 2 != 0:
        errors.append("output_height must be even")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
    }


def _cumulative_offsets(values: list[int]) -> list[int]:
    offsets: list[int] = []
    total = 0

    for value in values:
        offsets.append(total)
        total += value

    return offsets


def _validate_slice_order(slice_order: list[int] | None, slice_count: int) -> list[int]:
    if slice_order is None:
        return build_default_order(slice_count)

    if not isinstance(slice_order, list):
        raise ValueError("slice_order must be a list")

    if len(slice_order) != slice_count:
        raise ValueError("slice_order length must equal slice_count")

    seen: set[int] = set()
    for value in slice_order:
        if not isinstance(value, int):
            raise ValueError("slice_order must only contain integers")
        if value < 0 or value >= slice_count:
            raise ValueError("slice_order contains an out-of-range slice index")
        if value in seen:
            raise ValueError("slice_order must not contain duplicate slice indexes")
        seen.add(value)

    return list(slice_order)


def build_filter_graph(config: dict[str, object]) -> dict[str, object]:
    source_width = config["source_width"]
    source_height = config["source_height"]
    slice_count = config["slice_count"]
    rows = config["rows"]
    cols = config["cols"]
    output_width = config["output_width"]
    output_height = config["output_height"]
    fit_mode = config.get("fit_mode", "cover")
    slice_order = config.get("slice_order")

    validation = validate_grid_config(
        {
            "slice_count": slice_count,
            "rows": rows,
            "cols": cols,
            "output_width": output_width,
            "output_height": output_height,
        }
    )
    if not validation["ok"]:
        raise ValueError("; ".join(validation["errors"]))

    slice_plan = build_slice_plan(source_width, slice_count)
    resolved_slice_order = _validate_slice_order(slice_order, slice_count)
    column_widths = distribute_dimension(output_width, cols)
    row_heights = distribute_dimension(output_height, rows)
    column_offsets = _cumulative_offsets(column_widths)
    row_offsets = _cumulative_offsets(row_heights)

    split_labels = "".join(f"[s{index}]" for index in range(slice_count)) if slice_count > 1 else ""
    crop_and_scale_labels: list[str] = []

    for index, slice_item in enumerate(slice_plan):
        row = index // cols
        col = index % cols
        cell_width = column_widths[col]
        cell_height = row_heights[row]
        input_label = "[0:v]" if slice_count == 1 else f"[s{index}]"
        output_label = f"[v{index}]"
        base_crop = f"crop={slice_item['width']}:{source_height}:{slice_item['x']}:0"
        scale_cover = f"scale={cell_width}:{cell_height}:force_original_aspect_ratio=increase:flags=lanczos"
        scale_contain = f"scale={cell_width}:{cell_height}:force_original_aspect_ratio=decrease:flags=lanczos"
        scale_stretch = f"scale={cell_width}:{cell_height}:flags=lanczos"
        pad = f"pad={cell_width}:{cell_height}:(ow-iw)/2:(oh-ih)/2:color=black"
        crop_to_cell = f"crop={cell_width}:{cell_height}"

        if fit_mode == "contain":
            chain = f"{input_label}{base_crop},{scale_contain},{pad},setsar=1,setpts=PTS-STARTPTS{output_label}"
        elif fit_mode == "stretch":
            chain = f"{input_label}{base_crop},{scale_stretch},setsar=1,setpts=PTS-STARTPTS{output_label}"
        else:
            chain = f"{input_label}{base_crop},{scale_cover},{crop_to_cell},setsar=1,setpts=PTS-STARTPTS{output_label}"

        crop_and_scale_labels.append(chain)

    layout = "|".join(
        f"{column_offsets[index % cols]}_{row_offsets[index // cols]}"
        for index in range(slice_count)
    )
    stack_inputs = "".join(f"[v{slice_index}]" for slice_index in resolved_slice_order)

    filter_complex_parts: list[str] = []
    if slice_count > 1:
        filter_complex_parts.append(f"[0:v]split={slice_count}{split_labels}")
    filter_complex_parts.extend(crop_and_scale_labels)
    filter_complex_parts.append(f"{stack_inputs}xstack=inputs={slice_count}:layout={layout}[outv]")

    return {
        "slice_plan": slice_plan,
        "column_widths": column_widths,
        "row_heights": row_heights,
        "cell_width": column_widths[0],
        "cell_height": row_heights[0],
        "layout": layout,
        "slice_order": resolved_slice_order,
        "filter_complex": ";".join(filter_complex_parts),
        "output_label": "[outv]",
    }
