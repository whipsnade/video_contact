from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QGraphicsDropShadowEffect,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSizePolicy,
    QSpinBox,
    QComboBox,
    QVBoxLayout,
    QWidget,
)

from pyapp.core.app_state import (
    ASPECT_PRESETS,
    build_validation_errors,
    export_button_text,
    media_badge_text,
    quality_note_text,
    reset_slice_order,
    suggest_output_path,
)
from pyapp.core.errors import format_user_facing_error
from pyapp.core.export import run_export
from pyapp.core.media import detect_media_type_from_path, probe_media
from pyapp.core.order import format_order_summary

from .stage_grid import StageGrid


def _apply_card_shadow(widget: QWidget, *, blur_radius: int = 28, y_offset: int = 8, alpha: int = 24) -> None:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur_radius)
    shadow.setOffset(0, y_offset)
    shadow.setColor(QColor(34, 34, 34, alpha))
    widget.setGraphicsEffect(shadow)


class MainWindow(QMainWindow):
    progressUpdated = Signal(dict)
    stderrReceived = Signal(str)
    exportFinished = Signal(int)

    def __init__(self) -> None:
        super().__init__()

        self._source_path: str = ""
        self._source_info: dict[str, object] | None = None
        self._media_type: str | None = None
        self._output_path: str = ""
        self._output_path_is_auto = True
        self._job = None

        self.setWindowTitle("Video Grid Compositor")
        self.resize(1600, 980)

        self._build_ui()
        self._connect_signals()
        self._apply_default_state()

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(18)

        self.hero_card = self._build_hero_card()

        splitter = QSplitter(Qt.Orientation.Horizontal, central)
        splitter.setChildrenCollapsible(False)
        root_layout.addWidget(splitter, 1)

        self.left_panel = self._build_left_panel()
        self.right_panel = self._build_right_panel()

        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.left_panel.setMinimumWidth(460)
        self.left_panel.setMaximumWidth(580)

        _apply_card_shadow(self.hero_card, blur_radius=30, y_offset=10, alpha=28)
        _apply_card_shadow(self.left_panel, blur_radius=24, y_offset=8, alpha=22)
        _apply_card_shadow(self.right_panel, blur_radius=24, y_offset=8, alpha=22)

    def _build_hero_card(self) -> QWidget:
        hero = QFrame(self)
        hero.setObjectName("heroCard")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(24, 22, 24, 22)
        hero_layout.setSpacing(22)

        left_column = QVBoxLayout()
        left_column.setSpacing(10)

        self.hero_badge_label = QLabel("PORTABLE STUDIO", hero)
        self.hero_badge_label.setObjectName("heroBadge")
        self.hero_badge_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.hero_badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.hero_title_label = QLabel("把长条素材拆成片段，再重组为一个新文件", hero)
        self.hero_title_label.setObjectName("windowTitleLabel")
        self.hero_title_label.setWordWrap(True)

        self.hero_subtitle_label = QLabel(
            "白底、暖阴影、红色强调。视频和图片都支持，切片数、网格和输出比例都能手动配置，右侧卡片拖动即可换序。",
            hero,
        )
        self.hero_subtitle_label.setObjectName("windowSubtitleLabel")
        self.hero_subtitle_label.setWordWrap(True)

        left_column.addWidget(self.hero_badge_label)
        left_column.addWidget(self.hero_title_label)
        left_column.addWidget(self.hero_subtitle_label)

        pill_row = QHBoxLayout()
        pill_row.setSpacing(10)
        pill_row.setContentsMargins(0, 2, 0, 0)
        for pill_text in ("视频 / 图片", "手动切片", "网格拼接", "保留原编号", "无损 / 高质量 / 中质量"):
            pill_row.addWidget(self._build_feature_pill(pill_text))
        pill_row.addStretch(1)
        left_column.addLayout(pill_row)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(14)
        self.hero_slice_stat = self._build_hero_stat_card("切片", "3")
        self.hero_grid_stat = self._build_hero_stat_card("网格", "3 × 1")
        self.hero_output_stat = self._build_hero_stat_card("输出", "1920 × 1080")
        stats_row.addWidget(self.hero_slice_stat)
        stats_row.addWidget(self.hero_grid_stat)
        stats_row.addWidget(self.hero_output_stat)

        hero_layout.addLayout(left_column, 2)
        hero_layout.addLayout(stats_row, 1)
        return hero

    def _build_hero_stat_card(self, label_text: str, value_text: str) -> QWidget:
        card = QFrame(self)
        card.setObjectName("heroStatCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(4)

        label = QLabel(label_text, card)
        label.setObjectName("heroStatLabel")
        value = QLabel(value_text, card)
        value.setObjectName("heroStatValue")

        layout.addWidget(label)
        layout.addWidget(value)

        if label_text == "切片":
            self.hero_slice_value_label = value
        elif label_text == "网格":
            self.hero_grid_value_label = value
        elif label_text == "输出":
            self.hero_output_value_label = value

        _apply_card_shadow(card, blur_radius=18, y_offset=4, alpha=18)
        return card

    def _build_feature_pill(self, text: str) -> QLabel:
        pill = QLabel(text, self)
        pill.setObjectName("featurePill")
        pill.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return pill

    def _build_section_helper(self, text: str, parent: QWidget) -> QLabel:
        helper = QLabel(text, parent)
        helper.setObjectName("sectionHelperLabel")
        helper.setWordWrap(True)
        return helper

    def _build_left_panel(self) -> QWidget:
        panel = QScrollArea(self)
        panel.setWidgetResizable(True)
        panel.setFrameShape(QFrame.Shape.NoFrame)
        panel.setObjectName("surfaceScroll")

        content = QWidget(panel)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(14)

        layout.addWidget(self._build_source_group())
        layout.addWidget(self._build_slice_group())
        layout.addWidget(self._build_output_group())
        layout.addWidget(self._build_export_group())
        layout.addStretch(1)

        panel.setWidget(content)
        return panel

    def _build_right_panel(self) -> QWidget:
        container = QFrame(self)
        container.setObjectName("stagePanel")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        summary_card = QFrame(container)
        summary_card.setObjectName("summaryCard")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(16, 14, 16, 14)
        summary_layout.setSpacing(6)

        summary_title = QLabel("当前舞台顺序", summary_card)
        summary_title.setObjectName("sectionTitle")
        self.summary_hint_label = QLabel("拖动卡片即可换序，导出会按当前顺序生成。", summary_card)
        self.summary_hint_label.setObjectName("summaryHintLabel")
        self.summary_hint_label.setWordWrap(True)
        self.order_summary_label = QLabel("未生成切片", summary_card)
        self.order_summary_label.setObjectName("orderSummaryLabel")
        self.order_summary_label.setWordWrap(True)

        summary_layout.addWidget(summary_title)
        summary_layout.addWidget(self.summary_hint_label)
        summary_layout.addWidget(self.order_summary_label)
        _apply_card_shadow(summary_card, blur_radius=20, y_offset=6, alpha=18)

        self.stage_grid = StageGrid(slice_count=3, parent=container)
        self.stage_grid.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.stage_grid.setMinimumHeight(320)

        log_group = QGroupBox("处理日志", container)
        log_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        log_group.setMaximumHeight(220)
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(12, 12, 12, 12)
        log_layout.setSpacing(8)

        self.progress_bar = QProgressBar(log_group)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.status_label = QLabel("准备就绪。", log_group)
        self.status_label.setObjectName("statusLabel")

        self.log_view = QPlainTextEdit(log_group)
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.log_view.setPlaceholderText("导出进度和错误信息会显示在这里。")
        self.log_view.setMaximumBlockCount(500)
        self.log_view.setMinimumHeight(96)
        self.log_view.setMaximumHeight(130)

        log_layout.addWidget(self.progress_bar)
        log_layout.addWidget(self.status_label)
        log_layout.addWidget(self.log_view, 1)
        _apply_card_shadow(log_group, blur_radius=20, y_offset=6, alpha=18)

        layout.addWidget(summary_card)
        layout.addWidget(self.stage_grid, 3)
        layout.addWidget(log_group, 0)
        _apply_card_shadow(container, blur_radius=24, y_offset=8, alpha=22)
        return container

    def _build_source_group(self) -> QGroupBox:
        group = QGroupBox("输入文件", self)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(10)
        layout.addWidget(self._build_section_helper("选择长条视频或单张图片作为源素材。", group))

        row = QHBoxLayout()
        row.setSpacing(10)

        self.select_source_button = QPushButton("选择输入文件", group)
        self.select_source_button.setObjectName("primaryButton")
        self.select_source_button.clicked.connect(self._choose_source_file)

        self.media_badge_label = QLabel("等待输入", group)
        self.media_badge_label.setObjectName("mediaBadge")
        self.media_badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        row.addWidget(self.select_source_button, 0)
        row.addWidget(self.media_badge_label, 1)

        self.source_path_label = QLabel("尚未选择输入文件。", group)
        self.source_path_label.setObjectName("pathValueLabel")
        self.source_path_label.setWordWrap(True)
        self.source_path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )

        self.source_meta_label = QLabel("需要先读取视频或图片元数据。", group)
        self.source_meta_label.setObjectName("metaValueLabel")
        self.source_meta_label.setWordWrap(True)

        layout.addLayout(row)
        layout.addWidget(self.source_path_label)
        layout.addWidget(self.source_meta_label)
        _apply_card_shadow(group, blur_radius=20, y_offset=6, alpha=18)
        return group

    def _build_slice_group(self) -> QGroupBox:
        group = QGroupBox("切片与网格", self)
        form = QFormLayout(group)
        form.setContentsMargins(14, 16, 14, 14)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        helper = self._build_section_helper("切片数决定分段数量，行列决定最终网格。", group)
        form.addRow(helper)

        self.slice_count_spin = QSpinBox(group)
        self.slice_count_spin.setRange(1, 128)
        self.slice_count_spin.setValue(3)
        self.slice_count_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

        self.rows_spin = QSpinBox(group)
        self.rows_spin.setRange(1, 32)
        self.rows_spin.setValue(3)
        self.rows_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

        self.cols_spin = QSpinBox(group)
        self.cols_spin.setRange(1, 32)
        self.cols_spin.setValue(1)
        self.cols_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

        self.aspect_combo = QComboBox(group)
        self.aspect_combo.addItem("16:9", "16:9")
        self.aspect_combo.addItem("4:3", "4:3")
        self.aspect_combo.addItem("1:1", "1:1")
        self.aspect_combo.addItem("9:16", "9:16")
        self.aspect_combo.addItem("自定义", "custom")

        self.output_width_spin = QSpinBox(group)
        self.output_width_spin.setRange(2, 7680)
        self.output_width_spin.setSingleStep(2)
        self.output_width_spin.setValue(1920)
        self.output_width_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

        self.output_height_spin = QSpinBox(group)
        self.output_height_spin.setRange(2, 7680)
        self.output_height_spin.setSingleStep(2)
        self.output_height_spin.setValue(1080)
        self.output_height_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

        self.fit_mode_combo = QComboBox(group)
        self.fit_mode_combo.addItem("填满单元格（裁切）", "cover")
        self.fit_mode_combo.addItem("完整保留（留黑边）", "contain")
        self.fit_mode_combo.addItem("拉伸填满", "stretch")

        form.addRow("切片数", self.slice_count_spin)
        form.addRow("行数", self.rows_spin)
        form.addRow("列数", self.cols_spin)
        form.addRow("输出比例", self.aspect_combo)
        form.addRow("输出宽度", self.output_width_spin)
        form.addRow("输出高度", self.output_height_spin)
        form.addRow("适配模式", self.fit_mode_combo)
        _apply_card_shadow(group, blur_radius=20, y_offset=6, alpha=18)
        return group

    def _build_output_group(self) -> QGroupBox:
        group = QGroupBox("输出路径", self)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(10)
        layout.addWidget(self._build_section_helper("先选保存位置，再按当前参数自动建议文件名。", group))

        row = QHBoxLayout()
        row.setSpacing(10)

        self.select_output_button = QPushButton("选择位置", group)
        self.select_output_button.setObjectName("secondaryButton")
        self.select_output_button.clicked.connect(self._choose_output_file)

        row.addWidget(self.select_output_button, 0)

        layout.addLayout(row)

        self.output_path_label = QLabel("尚未选择输出路径。", group)
        self.output_path_label.setObjectName("outputPathValue")
        self.output_path_label.setWordWrap(True)
        self.output_path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        layout.addWidget(self.output_path_label)
        _apply_card_shadow(group, blur_radius=20, y_offset=6, alpha=18)
        return group

    def _build_export_group(self) -> QGroupBox:
        group = QGroupBox("导出设置", self)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(10)
        layout.addWidget(self._build_section_helper("无损、高质量、中质量可切换；拖动舞台即可改变合并顺序。", group))

        self.quality_combo = QComboBox(group)
        self.quality_combo.addItem("无损", "lossless")
        self.quality_combo.addItem("高质量", "high")
        self.quality_combo.addItem("中质量", "medium")

        self.audio_combo = QComboBox(group)
        self.audio_combo.addItem("复制原音轨", "copy")
        self.audio_combo.addItem("转码 AAC", "aac")

        self.quality_note_label = QLabel("", group)
        self.quality_note_label.setObjectName("qualityNoteLabel")
        self.quality_note_label.setWordWrap(True)

        self.validation_label = QLabel("", group)
        self.validation_label.setObjectName("validationLabel")
        self.validation_label.setWordWrap(True)

        row = QHBoxLayout()
        row.setSpacing(10)

        self.reset_order_button = QPushButton("恢复默认顺序", group)
        self.reset_order_button.setObjectName("secondaryButton")
        self.reset_order_button.clicked.connect(self._reset_order)

        self.export_button = QPushButton("开始导出", group)
        self.export_button.setObjectName("primaryButton")
        self.export_button.clicked.connect(self._start_export)

        self.cancel_button = QPushButton("取消", group)
        self.cancel_button.setObjectName("ghostButton")
        self.cancel_button.clicked.connect(self._cancel_export)
        self.cancel_button.setEnabled(False)

        row.addWidget(self.reset_order_button)
        row.addWidget(self.export_button)
        row.addWidget(self.cancel_button)

        layout.addWidget(self.quality_combo)
        layout.addWidget(self.audio_combo)
        layout.addWidget(self.quality_note_label)
        layout.addWidget(self.validation_label)
        layout.addLayout(row)
        _apply_card_shadow(group, blur_radius=20, y_offset=6, alpha=18)
        return group

    def _connect_signals(self) -> None:
        self.stage_grid.orderChanged.connect(self._on_order_changed)
        self.progressUpdated.connect(self._on_progress_updated)
        self.stderrReceived.connect(self._append_log)
        self.exportFinished.connect(self._on_export_finished)

        self.slice_count_spin.valueChanged.connect(self._on_slice_count_changed)
        self.rows_spin.valueChanged.connect(self._sync_state)
        self.cols_spin.valueChanged.connect(self._sync_state)
        self.output_width_spin.valueChanged.connect(self._on_output_dimension_changed)
        self.output_height_spin.valueChanged.connect(self._on_output_dimension_changed)
        self.aspect_combo.currentIndexChanged.connect(self._on_aspect_changed)
        self.fit_mode_combo.currentIndexChanged.connect(self._sync_state)
        self.quality_combo.currentIndexChanged.connect(self._sync_state)
        self.audio_combo.currentIndexChanged.connect(self._sync_state)

    def _apply_default_state(self) -> None:
        self.stage_grid.set_order(reset_slice_order(self.slice_count_spin.value()))
        self._sync_state()

    def _choose_source_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择输入文件",
            "",
            "媒体文件 (*.mp4 *.mov *.mkv *.webm *.m4v *.avi *.jpg *.jpeg *.png *.webp *.bmp);;所有文件 (*.*)",
        )
        if not file_path:
            return

        self._source_path = file_path
        self._output_path_is_auto = True
        self._append_log(f"已选择输入文件：{Path(file_path).name}")
        self._load_source_metadata(file_path)
        self._sync_state()

    def _load_source_metadata(self, file_path: str) -> None:
        try:
            self._media_type = detect_media_type_from_path(file_path)
        except ValueError as exc:
            self._source_info = None
            self._media_type = None
            self._append_log(f"错误：{exc}")
            return

        try:
            self._source_info = probe_media(file_path)
            self._append_log(
                f"元数据已读取：{self._source_info['source_width']} × {self._source_info['source_height']}"
            )
        except Exception as exc:  # noqa: BLE001 - UI needs to surface probe failures
            self._source_info = None
            self._append_log(format_user_facing_error("读取元数据", exc))

    def _choose_output_file(self) -> None:
        suggested = self._suggest_output_path()
        if self._media_type == "image":
            caption = "选择图片输出路径"
            file_filter = "JPEG 图片 (*.jpg *.jpeg)"
        else:
            caption = "选择视频输出路径"
            file_filter = "MP4 视频 (*.mp4)"

        file_path, _ = QFileDialog.getSaveFileName(self, caption, suggested, file_filter)
        if not file_path:
            return

        output_path = self._ensure_output_extension(file_path)
        self._output_path = output_path
        self._output_path_is_auto = False
        self._append_log(f"输出路径：{output_path}")
        self._sync_state()

    def _ensure_output_extension(self, file_path: str) -> str:
        suffix = ".jpg" if self._media_type == "image" else ".mp4"
        path = Path(file_path)
        if path.suffix.lower() not in {".jpg", ".jpeg", ".mp4"}:
            path = path.with_suffix(suffix)
        return str(path)

    def _on_slice_count_changed(self, *_args) -> None:
        self.stage_grid.set_slice_count(self.slice_count_spin.value())
        self._sync_state()

    def _on_output_dimension_changed(self, *_args) -> None:
        self._sync_aspect_combo_from_dimensions()
        self._sync_state()

    def _on_aspect_changed(self, *_args) -> None:
        preset_key = self.aspect_combo.currentData()
        if isinstance(preset_key, str) and preset_key in ASPECT_PRESETS:
            preset = ASPECT_PRESETS[preset_key]
            with QSignalBlocker(self.output_width_spin), QSignalBlocker(self.output_height_spin):
                self.output_width_spin.setValue(preset["width"])
                self.output_height_spin.setValue(preset["height"])
        self._sync_state()

    def _sync_aspect_combo_from_dimensions(self) -> None:
        width = self.output_width_spin.value()
        height = self.output_height_spin.value()
        matched_index = -1
        for index in range(self.aspect_combo.count()):
            key = self.aspect_combo.itemData(index)
            if key in ASPECT_PRESETS:
                preset = ASPECT_PRESETS[key]
                if width * preset["height"] == height * preset["width"]:
                    matched_index = index
                    break
        with QSignalBlocker(self.aspect_combo):
            if matched_index >= 0:
                self.aspect_combo.setCurrentIndex(matched_index)
            else:
                self.aspect_combo.setCurrentIndex(self.aspect_combo.count() - 1)

    def _reset_order(self) -> None:
        self.stage_grid.reset_order()
        self._append_log("已恢复默认顺序。")
        self._sync_state()

    def _on_order_changed(self, order: list[int]) -> None:
        self.order_summary_label.setText(format_order_summary(order))
        self._sync_state()

    def _sync_state(self, *_args) -> None:
        self._update_media_controls()
        self._update_output_path()
        self._update_quality_note()
        self._update_hero_stats()
        self._update_stage_reorder_hint()
        self._update_validation()

    def _update_media_controls(self) -> None:
        self.media_badge_label.setText(media_badge_text(self._media_type))
        self.export_button.setText(export_button_text(self._media_type))

        is_image = self._media_type == "image"
        self.quality_combo.setEnabled(not is_image)
        self.audio_combo.setEnabled(not is_image)

        if self._source_info:
            width = self._source_info.get("source_width")
            height = self._source_info.get("source_height")
            duration = self._source_info.get("duration_seconds")
            summary = [f"{width} × {height}"]
            if isinstance(duration, (int, float)) and duration > 0:
                summary.append(f"时长 {duration:.2f}s")
            self.source_meta_label.setText("，".join(summary))
        else:
            self.source_meta_label.setText("需要先读取视频或图片元数据。")

        if self._source_path:
            self.source_path_label.setText(self._source_path)
        else:
            self.source_path_label.setText("尚未选择输入文件。")

    def _update_output_path(self) -> None:
        if self._output_path_is_auto:
            auto_path = self._suggest_output_path()
            if auto_path:
                self._output_path = auto_path

        display_text = self._output_path or "尚未选择输出路径。"
        self.output_path_label.setText(display_text)
        self.output_path_label.setToolTip(display_text)

    def _update_quality_note(self) -> None:
        self.quality_note_label.setText(quality_note_text(self._media_type, self._quality_value()))

    def _update_hero_stats(self) -> None:
        self.hero_slice_value_label.setText(str(self.slice_count_spin.value()))
        self.hero_grid_value_label.setText(f"{self.rows_spin.value()} × {self.cols_spin.value()}")
        self.hero_output_value_label.setText(f"{self.output_width_spin.value()} × {self.output_height_spin.value()}")

    def _update_stage_reorder_hint(self) -> None:
        if self.slice_count_spin.value() <= 1:
            self.summary_hint_label.setText("当前只有 1 个切片，无需拖动换序。")
        else:
            self.summary_hint_label.setText("拖动卡片即可换序，导出会按当前顺序生成。")

    def _update_validation(self) -> None:
        errors = build_validation_errors(self._build_job_config())
        if errors:
            self.validation_label.setText("\n".join(errors))
            self.validation_label.show()
        else:
            self.validation_label.setText("状态正常，可以导出。")

    def _suggest_output_path(self) -> str:
        return suggest_output_path(
            source_path=self._source_path,
            media_type=self._media_type,
            slice_count=self.slice_count_spin.value(),
            rows=self.rows_spin.value(),
            cols=self.cols_spin.value(),
            output_width=self.output_width_spin.value(),
            output_height=self.output_height_spin.value(),
        )

    def _quality_value(self) -> str:
        value = self.quality_combo.currentData()
        return value if isinstance(value, str) else "lossless"

    def _fit_mode_value(self) -> str:
        value = self.fit_mode_combo.currentData()
        return value if isinstance(value, str) else "cover"

    def _audio_mode_value(self) -> str:
        value = self.audio_combo.currentData()
        return value if isinstance(value, str) else "copy"

    def _aspect_preset_value(self) -> str:
        value = self.aspect_combo.currentData()
        return value if isinstance(value, str) else "custom"

    def _build_job_config(self) -> dict[str, object]:
        return {
            "media_type": self._media_type,
            "source_path": self._source_path,
            "source_info": self._source_info,
            "output_path": self._output_path,
            "source_width": self._source_info["source_width"] if self._source_info else 0,
            "source_height": self._source_info["source_height"] if self._source_info else 0,
            "slice_count": self.slice_count_spin.value(),
            "rows": self.rows_spin.value(),
            "cols": self.cols_spin.value(),
            "slice_order": self.stage_grid.order(),
            "output_width": self.output_width_spin.value(),
            "output_height": self.output_height_spin.value(),
            "aspect_preset": self._aspect_preset_value(),
            "fit_mode": self._fit_mode_value(),
            "export_mode": self._quality_value(),
            "audio_mode": self._audio_mode_value(),
        }

    def _start_export(self) -> None:
        errors = build_validation_errors(self._build_job_config())
        if errors:
            QMessageBox.warning(self, "无法导出", "\n".join(errors))
            self._append_log("导出被阻止：\n" + "\n".join(errors))
            return

        try:
            self._job = run_export(
                self._build_job_config(),
                handlers={
                    "on_progress": self.progressUpdated.emit,
                    "on_stderr": self.stderrReceived.emit,
                },
            )
        except Exception as exc:  # noqa: BLE001 - surface subprocess and lookup errors
            friendly_error = format_user_facing_error("导出启动", exc)
            self._append_log(friendly_error)
            QMessageBox.critical(self, "导出失败", friendly_error)
            return

        self._set_running_state(True)
        self._append_log("开始导出任务。")

        watcher = threading.Thread(target=self._wait_for_export_job, daemon=True)
        watcher.start()

    def _wait_for_export_job(self) -> None:
        if self._job is None:
            return

        exit_code = self._job.wait()
        self.exportFinished.emit(-1 if exit_code is None else exit_code)

    def _cancel_export(self) -> None:
        if self._job is not None:
            self._job.cancel()
            self._append_log("已请求取消导出。")

    def _set_running_state(self, running: bool) -> None:
        controls = [
            self.select_source_button,
            self.select_output_button,
            self.slice_count_spin,
            self.rows_spin,
            self.cols_spin,
            self.aspect_combo,
            self.output_width_spin,
            self.output_height_spin,
            self.fit_mode_combo,
            self.quality_combo,
            self.audio_combo,
            self.reset_order_button,
            self.stage_grid,
        ]
        for control in controls:
            control.setEnabled(not running)

        self.export_button.setEnabled(not running)
        self.cancel_button.setEnabled(running)

    def _on_progress_updated(self, payload: dict) -> None:
        percent = payload.get("percent")
        if isinstance(percent, (int, float)):
            self.progress_bar.setValue(int(percent))
            self.status_label.setText(f"导出进度：{percent:.2f}%")

    def _on_export_finished(self, exit_code: int) -> None:
        self._set_running_state(False)
        self._job = None
        if exit_code == 0:
            self.progress_bar.setValue(100)
            self.status_label.setText("导出完成。")
            self._append_log("导出完成。")
        else:
            self.status_label.setText(f"导出结束，退出码 {exit_code}。")
            self._append_log(f"导出结束，退出码 {exit_code}。")

    def _append_log(self, message: str) -> None:
        text = message.strip()
        if not text:
            return
        self.log_view.appendPlainText(text)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self._job is not None:
            self._job.cancel()
        super().closeEvent(event)
