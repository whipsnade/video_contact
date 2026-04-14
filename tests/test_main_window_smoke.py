from PySide6.QtWidgets import QPlainTextEdit, QSplitter

from pyapp.ui.main_window import MainWindow


def test_main_window_smoke(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "Video Grid Compositor"
    assert window.hero_card is not None
    assert "重组" in window.hero_title_label.text()
    assert window.stage_grid is not None
    assert window.stage_grid.order() == [0, 1, 2]
    assert window.reset_order_button.text() == "恢复默认顺序"


def test_main_window_does_not_show_top_hero_section(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    layout = window.centralWidget().layout()
    assert layout.count() == 1
    assert isinstance(layout.itemAt(0).widget(), QSplitter)


def test_main_window_job_config_includes_selected_aspect_ratio(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.aspect_combo.setCurrentIndex(1)
    config = window._build_job_config()

    assert config["aspect_preset"] == "4:3"


def test_main_window_right_panel_prioritizes_stage_area_over_log_area(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.stage_grid.minimumHeight() >= 320
    assert window.log_view.maximumHeight() <= 220
    assert window.log_view.lineWrapMode() == QPlainTextEdit.LineWrapMode.NoWrap


def test_main_window_shows_friendly_message_when_ffprobe_is_missing(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)

    def fake_probe_media(*_args, **_kwargs):
        raise ValueError("Unable to locate ffprobe. Set FFPROBE_PATH or install it in PATH.")

    monkeypatch.setattr("pyapp.ui.main_window.probe_media", fake_probe_media)

    window._load_source_metadata("/tmp/input.mp4")

    log_text = window.log_view.toPlainText()
    assert "未找到 ffprobe" in log_text
    assert "FFPROBE_PATH" in log_text


def test_main_window_shows_friendly_message_when_ffmpeg_is_missing(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)

    window._source_path = "/tmp/input.mp4"
    window._media_type = "video"
    window._source_info = {
        "source_width": 5760,
        "source_height": 360,
        "duration_seconds": 10.0,
    }
    window._output_path = "/tmp/output.mp4"
    window._output_path_is_auto = False

    def fake_run_export(*_args, **_kwargs):
        raise ValueError("Unable to locate ffmpeg. Set FFMPEG_PATH or install it in PATH.")

    monkeypatch.setattr("pyapp.ui.main_window.run_export", fake_run_export)
    monkeypatch.setattr("pyapp.ui.main_window.QMessageBox.critical", lambda *args, **kwargs: None)

    window._start_export()

    log_text = window.log_view.toPlainText()
    assert "未找到 ffmpeg" in log_text
    assert "FFMPEG_PATH" in log_text
