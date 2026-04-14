from pathlib import Path


def test_windows_workflow_contains_portable_build_steps():
    workflow_path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "windows-portable.yml"
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert "windows-latest" in workflow_text
    assert "workflow_dispatch" in workflow_text
    assert "scripts/build_portable.py" in workflow_text
    assert "--onefile" in workflow_text
    assert "dist/Video Grid Compositor.exe" in workflow_text
    assert "FFMPEG_PATH" in workflow_text
    assert "FFPROBE_PATH" in workflow_text
    assert "upload-artifact" in workflow_text
