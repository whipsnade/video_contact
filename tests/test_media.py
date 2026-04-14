import os
import tempfile
from pathlib import Path

from pyapp.core.media import (
    detect_media_type_from_path,
    parse_ffprobe_payload,
    probe_media,
)
from pyapp.core.paths import resolve_tool_path


def test_detect_media_type_from_path_distinguishes_video_and_image():
    assert detect_media_type_from_path("/tmp/source.mp4") == "video"
    assert detect_media_type_from_path("/tmp/source.jpeg") == "image"


def test_detect_media_type_from_path_rejects_unknown_extensions():
    try:
        detect_media_type_from_path("/tmp/source.txt")
    except ValueError as exc:
        assert "Unsupported media type" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_parse_ffprobe_payload_normalizes_video_metadata():
    payload = {
        "streams": [
            {
                "codec_type": "video",
                "width": 5760,
                "height": 360,
                "duration": "5.0",
                "avg_frame_rate": "30/1",
                "codec_name": "h264",
            },
            {"codec_type": "audio"},
        ],
        "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "5.0"},
    }

    info = parse_ffprobe_payload(payload, media_type="video")

    assert info["media_type"] == "video"
    assert info["source_width"] == 5760
    assert info["source_height"] == 360
    assert info["duration_seconds"] == 5.0
    assert info["fps"] == 30.0
    assert info["has_audio"] is True
    assert info["codec_name"] == "h264"


def test_parse_ffprobe_payload_normalizes_image_metadata():
    payload = {
        "streams": [
            {
                "codec_type": "video",
                "width": 7168,
                "height": 128,
                "codec_name": "png",
            }
        ],
        "format": {"format_name": "png_pipe"},
    }

    info = parse_ffprobe_payload(payload, media_type="image")

    assert info["media_type"] == "image"
    assert info["source_width"] == 7168
    assert info["source_height"] == 128
    assert info["duration_seconds"] is None
    assert info["fps"] is None
    assert info["has_audio"] is False


def test_resolve_tool_path_finds_executable_in_extra_search_dirs_when_path_is_empty():
    with tempfile.TemporaryDirectory() as temp_dir:
        tool_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
        tool_path = Path(temp_dir) / tool_name
        tool_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        tool_path.chmod(0o755)

        resolved = resolve_tool_path(
            "ffprobe",
            env={"PATH": ""},
            extra_search_dirs=[temp_dir],
        )

        assert resolved == str(tool_path)


def test_probe_media_uses_ffprobe_output(tmp_path, monkeypatch):
    payload = {
        "streams": [
            {
                "codec_type": "video",
                "width": 1920,
                "height": 1080,
                "duration": "10.0",
                "avg_frame_rate": "25/1",
                "codec_name": "h264",
            }
        ],
        "format": {"format_name": "mov,mp4", "duration": "10.0"},
    }

    fake_ffprobe = tmp_path / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
    fake_ffprobe.write_text("#!/bin/sh\ncat <<'EOF'\n{}\nEOF\n".format("{}"), encoding="utf-8")
    fake_ffprobe.chmod(0o755)

    class Result:
        stdout = (
            "{\"streams\":[{\"codec_type\":\"video\",\"width\":1920,\"height\":1080,"
            "\"duration\":\"10.0\",\"avg_frame_rate\":\"25/1\",\"codec_name\":\"h264\"}],"
            "\"format\":{\"format_name\":\"mov,mp4\",\"duration\":\"10.0\"}}"
        )

    monkeypatch.setattr("pyapp.core.media.resolve_tool_path", lambda *args, **kwargs: str(fake_ffprobe))
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: Result())

    info = probe_media("/tmp/input.mp4")

    assert info["media_type"] == "video"
    assert info["source_width"] == 1920
    assert info["source_height"] == 1080
