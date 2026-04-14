from pyapp.core.app_state import (
    build_validation_errors,
    export_button_text,
    media_badge_text,
    quality_note_text,
    reset_slice_order,
    suggest_output_path,
)


def test_build_validation_errors_rejects_invalid_grid_and_aspect_ratio():
    errors = build_validation_errors(
        {
            "source_path": "/tmp/input.mp4",
            "source_info": {"source_width": 5760, "source_height": 360},
            "output_path": "/tmp/output.mp4",
            "slice_count": 3,
            "rows": 2,
            "cols": 2,
            "output_width": 1921,
            "output_height": 1080,
            "aspect_preset": "16:9",
        }
    )

    joined = "\n".join(errors)
    assert "rows × cols" in joined
    assert "even" in joined
    assert "16:9" in joined


def test_suggest_output_path_keeps_source_basename_and_suffix():
    path = suggest_output_path(
        source_path="/Users/test/video.mp4",
        media_type="video",
        slice_count=3,
        rows=3,
        cols=1,
        output_width=1920,
        output_height=1080,
    )

    assert path.endswith("/Users/test/video-3slice-3x1-1920x1080.mp4")


def test_media_and_export_labels_change_with_media_type():
    assert media_badge_text("video") == "视频输入"
    assert media_badge_text("image") == "图片输入"
    assert export_button_text("video") == "开始导出视频"
    assert export_button_text("image") == "开始生成图片"
    assert "JPG" in quality_note_text("image", "lossless")


def test_reset_slice_order_returns_default_sequence():
    assert reset_slice_order(3) == [0, 1, 2]
