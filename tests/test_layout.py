import pytest

from pyapp.core.layout import (
    build_filter_graph,
    build_slice_plan,
    distribute_slice_widths,
    validate_grid_config,
)


def test_distribute_slice_widths_spreads_remainder_left_to_right():
    assert distribute_slice_widths(10, 3) == [4, 3, 3]
    assert distribute_slice_widths(9, 3) == [3, 3, 3]


def test_validate_grid_config_rejects_mismatched_grid_shape():
    result = validate_grid_config(
        {
            "slice_count": 3,
            "rows": 2,
            "cols": 2,
            "output_width": 1920,
            "output_height": 1080,
        }
    )

    assert result["ok"] is False
    assert "rows × cols" in "\n".join(result["errors"])


def test_validate_grid_config_accepts_valid_16_9_job():
    result = validate_grid_config(
        {
            "slice_count": 3,
            "rows": 3,
            "cols": 1,
            "output_width": 1920,
            "output_height": 1080,
        }
    )

    assert result == {"ok": True, "errors": []}


def test_build_slice_plan_tracks_widths_and_offsets():
    plan = build_slice_plan(5760, 3)

    assert [item["width"] for item in plan] == [1920, 1920, 1920]
    assert [item["x"] for item in plan] == [0, 1920, 3840]


def test_build_filter_graph_emits_cover_layout_for_three_slices():
    graph = build_filter_graph(
        {
            "source_width": 5760,
            "source_height": 360,
            "slice_count": 3,
            "rows": 3,
            "cols": 1,
            "output_width": 1920,
            "output_height": 1080,
            "fit_mode": "cover",
        }
    )

    assert graph["cell_width"] == 1920
    assert graph["cell_height"] == 360
    assert "crop=1920:360:0:0" in graph["filter_complex"]
    assert "crop=1920:360:1920:0" in graph["filter_complex"]
    assert "crop=1920:360:3840:0" in graph["filter_complex"]
    assert graph["filter_complex"].count("setpts=PTS-STARTPTS") == 3
    assert "xstack=inputs=3:layout=0_0|0_360|0_720" in graph["filter_complex"]


def test_build_filter_graph_handles_single_slice_without_split_labels():
    graph = build_filter_graph(
        {
            "source_width": 1920,
            "source_height": 1080,
            "slice_count": 1,
            "rows": 1,
            "cols": 1,
            "output_width": 1920,
            "output_height": 1080,
            "fit_mode": "cover",
        }
    )

    assert "split=1" not in graph["filter_complex"]
    assert graph["filter_complex"].startswith("[0:v]crop=1920:1080:0:0")
    assert graph["filter_complex"].endswith("[v0]xstack=inputs=1:layout=0_0[outv]")


def test_build_filter_graph_stretches_slices_without_cropping():
    graph = build_filter_graph(
        {
            "source_width": 7168,
            "source_height": 128,
            "slice_count": 3,
            "rows": 3,
            "cols": 1,
            "output_width": 1920,
            "output_height": 1080,
            "fit_mode": "stretch",
        }
    )

    assert "scale=1920:360:flags=lanczos" in graph["filter_complex"]
    assert "force_original_aspect_ratio" not in graph["filter_complex"]
    assert "pad=1920:360" not in graph["filter_complex"]
    assert "crop=1920:360" not in graph["filter_complex"]


def test_build_filter_graph_uses_explicit_slice_order():
    graph = build_filter_graph(
        {
            "source_width": 5760,
            "source_height": 360,
            "slice_count": 3,
            "rows": 3,
            "cols": 1,
            "output_width": 1920,
            "output_height": 1080,
            "fit_mode": "cover",
            "slice_order": [0, 2, 1],
        }
    )

    assert "[v0][v2][v1]xstack=inputs=3:layout=0_0|0_360|0_720[outv]" in graph["filter_complex"]


def test_build_filter_graph_rejects_invalid_slice_order():
    with pytest.raises(ValueError, match="slice_order"):
        build_filter_graph(
            {
                "source_width": 5760,
                "source_height": 360,
                "slice_count": 3,
                "rows": 3,
                "cols": 1,
                "output_width": 1920,
                "output_height": 1080,
                "fit_mode": "cover",
                "slice_order": [0, 2, 2],
            }
        )

    with pytest.raises(ValueError, match="slice_order"):
        build_filter_graph(
            {
                "source_width": 5760,
                "source_height": 360,
                "slice_count": 3,
                "rows": 3,
                "cols": 1,
                "output_width": 1920,
                "output_height": 1080,
                "fit_mode": "cover",
                "slice_order": [0, 2],
            }
        )
