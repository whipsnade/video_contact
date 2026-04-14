from __future__ import annotations

from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QAbstractItemView,
    QVBoxLayout,
    QWidget,
)

from pyapp.core.order import build_default_order, format_order_summary, normalize_order, swap_order


def _apply_card_shadow(widget: QWidget, *, blur_radius: int = 22, y_offset: int = 7, alpha: int = 22) -> None:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur_radius)
    shadow.setOffset(0, y_offset)
    shadow.setColor(QColor(34, 34, 34, alpha))
    widget.setGraphicsEffect(shadow)


def _build_drag_icon_pixmap(size: int = 18) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(153, 153, 153))

        dot_size = 3
        spacing_x = 7
        spacing_y = 5
        start_x = 4
        start_y = 3
        for col in range(2):
            for row in range(3):
                painter.drawEllipse(start_x + col * spacing_x, start_y + row * spacing_y, dot_size, dot_size)
    finally:
        painter.end()

    return pixmap


class StageCardWidget(QFrame):
    def __init__(self, original_index: int, position_index: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.original_index = original_index
        self._stage_grid = parent
        self._reorder_enabled = True
        self._drag_start_position: QPoint | None = None
        self._drag_active = False

        self.setObjectName("stageCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(16, 14, 16, 14)
        outer_layout.setSpacing(14)

        self.badge = QLabel(self)
        self.badge.setObjectName("stageCardBadge")
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setFixedSize(52, 52)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)

        self.position_label = QLabel(self)
        self.position_label.setObjectName("stageCardPosition")

        self.original_label = QLabel(self)
        self.original_label.setObjectName("stageCardOriginal")

        self.drag_hint = QLabel("拖动卡片可交换顺序", self)
        self.drag_hint.setObjectName("stageCardHint")

        content_layout.addWidget(self.position_label)
        content_layout.addWidget(self.original_label)
        content_layout.addWidget(self.drag_hint)

        outer_layout.addWidget(self.badge)
        outer_layout.addLayout(content_layout, 1)

        self.drag_icon = QLabel(self)
        self.drag_icon.setObjectName("stageCardDragIcon")
        self.drag_icon.setPixmap(_build_drag_icon_pixmap())
        self.drag_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drag_icon.setFixedSize(32, 32)
        self.drag_icon.setToolTip("拖动换序")

        outer_layout.addStretch(1)
        outer_layout.addWidget(self.drag_icon)

        for child in (self.badge, self.position_label, self.original_label, self.drag_hint, self.drag_icon):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        _apply_card_shadow(self, blur_radius=18, y_offset=4, alpha=16)
        self.set_position(position_index)

    def set_reorder_enabled(self, enabled: bool) -> None:
        self._reorder_enabled = enabled
        self.drag_icon.setVisible(enabled)
        if enabled:
            self.drag_hint.setText("拖动换序，保留原编号")
            self.drag_icon.setToolTip("拖动换序")
        else:
            self.drag_hint.setText("当前只有 1 个切片，无需换序")
            self.drag_icon.setToolTip("当前只有 1 个切片，无需换序")

    def set_position(self, position_index: int) -> None:
        display_position = position_index + 1
        display_original = self.original_index + 1
        self.badge.setText(f"{display_original:02d}")
        self.position_label.setText(f"当前位置 · 第 {display_position} 位")
        self.original_label.setText(f"原始编号 · #{display_original}")
        self.drag_hint.setText("拖动换序，原编号固定不变")

    def _trigger_reorder(self, global_position: QPoint) -> None:
        grid = self._stage_grid
        if grid is None:
            return

        reorder_handler = getattr(grid, "reorder_from_drag", None)
        if callable(reorder_handler):
            reorder_handler(self, global_position)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton and self._reorder_enabled:
            self._drag_start_position = event.position().toPoint()
            self._drag_active = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._drag_start_position is not None and event.buttons() & Qt.MouseButton.LeftButton:
            distance = (event.position().toPoint() - self._drag_start_position).manhattanLength()
            if distance >= QApplication.startDragDistance():
                self._drag_active = True
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if self._drag_start_position is None:
            event.accept()
            return

        dragging = self._drag_active
        self._drag_start_position = None
        self._drag_active = False
        self.unsetCursor()

        if dragging and self._reorder_enabled:
            self._trigger_reorder(event.globalPosition().toPoint())
            return

        event.accept()


class StageGrid(QListWidget):
    orderChanged = Signal(list)

    def __init__(self, slice_count: int = 3, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._slice_count = 0
        self._suspend_order_sync = False
        self._reorder_enabled = False

        self.setObjectName("stageGrid")
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSpacing(12)

        self.set_slice_count(slice_count)

    def set_slice_count(self, slice_count: int) -> None:
        if not isinstance(slice_count, int) or slice_count <= 0:
            slice_count = 1

        current_order = self.order()
        self._slice_count = slice_count
        if len(current_order) == slice_count:
            self.set_order(current_order)
        else:
            self.set_order(build_default_order(slice_count))

        self.set_reorder_enabled(slice_count > 1)

    def slice_count(self) -> int:
        return self._slice_count

    def reorder_enabled(self) -> bool:
        return self._reorder_enabled

    def set_reorder_enabled(self, enabled: bool) -> None:
        self._reorder_enabled = bool(enabled)
        self.setDragEnabled(False)
        self.setAcceptDrops(False)
        self.setDropIndicatorShown(False)
        self.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)

        self.viewport().update()
        self._refresh_cards()

    def order(self) -> list[int]:
        order: list[int] = []
        for index in range(self.count()):
            item = self.item(index)
            if item is None:
                continue
            value = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(value, int):
                order.append(value)
        return order

    def order_summary(self) -> str:
        return format_order_summary(self.order())

    def reset_order(self) -> None:
        self.set_order(build_default_order(self._slice_count))

    def repair_after_reorder(self) -> None:
        self.set_order(self.order())

    def reorder_from_drag(self, dragged_widget: QWidget, global_position: QPoint) -> None:
        source_index = self._widget_index(dragged_widget)
        target_index = self._index_for_global_position(global_position)

        if source_index is None or target_index is None or source_index == target_index:
            return

        QTimer.singleShot(1, lambda: self._apply_reorder(source_index, target_index))

    def _apply_reorder(self, source_index: int, target_index: int) -> None:
        if source_index < 0 or target_index < 0:
            return
        if source_index >= self.count() or target_index >= self.count():
            return
        self.set_order(swap_order(self.order(), source_index, target_index))

    def _widget_index(self, widget: QWidget) -> int | None:
        for index in range(self.count()):
            item = self.item(index)
            if item is None:
                continue
            if self.itemWidget(item) is widget:
                return index
        return None

    def _index_for_global_position(self, global_position: QPoint) -> int | None:
        if self.count() == 0:
            return None

        viewport_position = self.viewport().mapFromGlobal(global_position)
        item = self.itemAt(viewport_position)
        if item is not None:
            return self.row(item)

        nearest_index = 0
        nearest_distance: int | None = None
        for index in range(self.count()):
            item = self.item(index)
            if item is None:
                continue
            center_y = self.visualItemRect(item).center().y()
            distance = abs(center_y - viewport_position.y())
            if nearest_distance is None or distance < nearest_distance:
                nearest_index = index
                nearest_distance = distance

        return nearest_index

    def set_order(self, order: list[int] | None) -> None:
        if self._slice_count <= 0:
            self._slice_count = len(order or []) or 1

        resolved_order = normalize_order(order, self._slice_count)

        self._suspend_order_sync = True
        try:
            self.clear()
            for position_index, original_index in enumerate(resolved_order):
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, original_index)
                item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsDragEnabled
                    | Qt.ItemFlag.ItemIsDropEnabled
                )

                widget = StageCardWidget(original_index, position_index, self)
                item.setSizeHint(widget.sizeHint())
                self.addItem(item)
                self.setItemWidget(item, widget)
        finally:
            self._suspend_order_sync = False

        self._refresh_cards()
        self.orderChanged.emit(self.order())

    def _refresh_cards(self) -> None:
        reorder_enabled = self._reorder_enabled and self._slice_count > 1
        for position_index in range(self.count()):
            item = self.item(position_index)
            if item is None:
                continue
            widget = self.itemWidget(item)
            if isinstance(widget, StageCardWidget):
                widget.set_position(position_index)
                widget.set_reorder_enabled(reorder_enabled)
