from __future__ import annotations

from typing import Sequence

from PySide6.QtWidgets import QApplication

from .core.paths import resource_path


def _load_stylesheet() -> str:
    style_path = resource_path("pyapp", "ui", "theme.qss")
    try:
        return style_path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _configure_application(app: QApplication) -> None:
    app.setApplicationName("Video Grid Compositor")
    app.setApplicationDisplayName("Video Grid Compositor")
    app.setOrganizationName("Hanxiang")
    app.setStyle("Fusion")

    stylesheet = _load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)


def create_app(argv: Sequence[str] | None = None) -> QApplication:
    app = QApplication.instance()
    if app is not None:
        _configure_application(app)
        return app

    created = QApplication(list(argv or []))
    _configure_application(created)
    return created
