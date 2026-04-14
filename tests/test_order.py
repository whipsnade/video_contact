from pyapp.core.order import (
    build_default_order,
    format_order_summary,
    is_default_order,
    normalize_order,
    swap_order,
)


def test_build_default_order_returns_natural_sequence():
    assert build_default_order(4) == [0, 1, 2, 3]


def test_normalize_order_falls_back_to_default_when_invalid():
    assert normalize_order([0, 2], 3) == [0, 1, 2]
    assert normalize_order([0, 2, 2], 3) == [0, 1, 2]


def test_swap_order_preserves_original_slice_numbers():
    assert swap_order([0, 1, 2, 3], 1, 3) == [0, 3, 2, 1]


def test_is_default_order_detects_changes():
    assert is_default_order([0, 1, 2]) is True
    assert is_default_order([0, 2, 1]) is False


def test_format_order_summary_keeps_original_numbers():
    assert format_order_summary([0, 2, 1]) == "#1 -> #3 -> #2"
