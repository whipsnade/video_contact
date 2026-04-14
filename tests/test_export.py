import io

from pyapp.core.export import build_export_command, parse_progress_line, run_export


def test_parse_progress_line_converts_out_time_ms_into_percent():
    parsed = parse_progress_line("out_time_ms=5000000", 10)

    assert parsed["seconds"] == 5
    assert parsed["percent"] == 50


def test_build_export_command_wires_grid_filter_and_output_mapping(monkeypatch):
    monkeypatch.setattr("pyapp.core.export.resolve_tool_path", lambda *args, **kwargs: "ffmpeg")

    command = build_export_command(
        {
            "media_type": "video",
            "source_path": "/tmp/input.mp4",
            "output_path": "/tmp/output.mp4",
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

    assert command["ffmpeg_path"].endswith("ffmpeg")
    assert "-filter_complex" in command["args"]
    assert "-map" in command["args"]
    assert "[outv]" in command["args"]
    assert "crop=1920:360:0:0" in command["filter_complex"]
    assert "xstack=inputs=3:layout=0_0|0_360|0_720" in command["filter_complex"]


def test_build_export_command_supports_high_and_medium_quality_video_presets(monkeypatch):
    monkeypatch.setattr("pyapp.core.export.resolve_tool_path", lambda *args, **kwargs: "ffmpeg")

    high_command = build_export_command(
        {
            "media_type": "video",
            "source_path": "/tmp/input.mp4",
            "output_path": "/tmp/output.mp4",
            "source_width": 5760,
            "source_height": 360,
            "slice_count": 3,
            "rows": 3,
            "cols": 1,
            "output_width": 1920,
            "output_height": 1080,
            "fit_mode": "cover",
            "export_mode": "high",
        }
    )
    medium_command = build_export_command(
        {
            "media_type": "video",
            "source_path": "/tmp/input.mp4",
            "output_path": "/tmp/output.mp4",
            "source_width": 5760,
            "source_height": 360,
            "slice_count": 3,
            "rows": 3,
            "cols": 1,
            "output_width": 1920,
            "output_height": 1080,
            "fit_mode": "cover",
            "export_mode": "medium",
        }
    )

    assert "-preset" in high_command["args"]
    assert "slow" in high_command["args"]
    assert "12" in high_command["args"]
    assert "-pix_fmt" in high_command["args"]

    assert "medium" in medium_command["args"]
    assert "20" in medium_command["args"]
    assert "-pix_fmt" in medium_command["args"]


def test_build_export_command_builds_a_single_frame_jpg_export_for_images(monkeypatch):
    monkeypatch.setattr("pyapp.core.export.resolve_tool_path", lambda *args, **kwargs: "ffmpeg")

    command = build_export_command(
        {
            "media_type": "image",
            "source_path": "/tmp/input.jpg",
            "output_path": "/tmp/output.jpg",
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

    args = command["args"]
    assert "-map 0:a?" not in " ".join(args)
    assert "-frames:v" in args
    assert "1" in args
    assert "-c:v" in args
    assert "mjpeg" in args
    assert "-q:v" in args
    assert "scale=1920:360:flags=lanczos" in command["filter_complex"]


def test_build_export_command_forwards_slice_order_into_the_filter_graph(monkeypatch):
    monkeypatch.setattr("pyapp.core.export.resolve_tool_path", lambda *args, **kwargs: "ffmpeg")

    command = build_export_command(
        {
            "media_type": "video",
            "source_path": "/tmp/input.mp4",
            "output_path": "/tmp/output.mp4",
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

    assert "[v0][v2][v1]xstack=inputs=3:layout=0_0|0_360|0_720[outv]" in command["filter_complex"]


def test_run_export_cancel_calls_terminate(monkeypatch):
    monkeypatch.setattr("pyapp.core.export.resolve_tool_path", lambda *args, **kwargs: "ffmpeg")

    class FakeProcess:
        def __init__(self):
            self.stdout = io.StringIO("")
            self.stderr = io.StringIO("")
            self.terminated = False

        def poll(self):
            return None if not self.terminated else 0

        def terminate(self):
            self.terminated = True

    fake_process = FakeProcess()
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: fake_process)

    job = run_export(
        {
            "media_type": "video",
            "source_path": "/tmp/input.mp4",
            "output_path": "/tmp/output.mp4",
            "source_width": 5760,
            "source_height": 360,
            "slice_count": 3,
            "rows": 3,
            "cols": 1,
            "output_width": 1920,
            "output_height": 1080,
            "fit_mode": "cover",
            "duration_seconds": 10,
        }
    )

    job.cancel()

    assert fake_process.terminated is True
