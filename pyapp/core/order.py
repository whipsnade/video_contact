from __future__ import annotations


def build_default_order(slice_count: int) -> list[int]:
    if not isinstance(slice_count, int) or slice_count <= 0:
        return []

    return list(range(slice_count))


def normalize_order(order: list[int] | None, slice_count: int) -> list[int]:
    default_order = build_default_order(slice_count)

    if not isinstance(order, list) or len(order) != len(default_order):
        return default_order

    seen: set[int] = set()
    for value in order:
        if not isinstance(value, int):
            return default_order
        if value < 0 or value >= len(default_order):
            return default_order
        if value in seen:
            return default_order
        seen.add(value)

    return list(order)


def swap_order(order: list[int], from_index: int, to_index: int) -> list[int]:
    if not isinstance(order, list):
        return []

    next_order = list(order)
    if not isinstance(from_index, int) or not isinstance(to_index, int):
        return next_order
    if from_index < 0 or to_index < 0:
        return next_order
    if from_index >= len(next_order) or to_index >= len(next_order):
        return next_order
    if from_index == to_index:
        return next_order

    next_order[from_index], next_order[to_index] = next_order[to_index], next_order[from_index]
    return next_order


def is_default_order(order: list[int] | None) -> bool:
    if not isinstance(order, list):
        return False

    return all(value == index for index, value in enumerate(order))


def format_order_summary(order: list[int] | None) -> str:
    if not order:
        return "未生成切片"

    return " -> ".join(f"#{value + 1}" for value in order)

