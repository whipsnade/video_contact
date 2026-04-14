from PySide6.QtWidgets import QAbstractItemView

from pyapp.ui.stage_grid import StageGrid


def test_stage_grid_preserves_original_numbers_and_reset(qtbot):
    grid = StageGrid(slice_count=3)
    qtbot.addWidget(grid)

    assert grid.order() == [0, 1, 2]

    grid.set_order([0, 2, 1])

    assert grid.order() == [0, 2, 1]
    assert grid.order_summary() == "#1 -> #3 -> #2"

    grid.reset_order()

    assert grid.order() == [0, 1, 2]


def test_stage_grid_repairs_lost_widgets_after_reorder(qtbot):
    grid = StageGrid(slice_count=3)
    qtbot.addWidget(grid)

    moved_item = grid.takeItem(0)
    grid.insertItem(2, moved_item)

    assert grid.order() == [1, 2, 0]
    assert grid.itemWidget(grid.item(2)) is None

    grid.repair_after_reorder()

    assert grid.order() == [1, 2, 0]
    assert all(grid.itemWidget(grid.item(index)) is not None for index in range(grid.count()))


def test_stage_grid_disables_drag_when_only_one_slice(qtbot):
    grid = StageGrid(slice_count=1)
    qtbot.addWidget(grid)

    assert grid.dragEnabled() is False
    assert grid.dragDropMode() == QAbstractItemView.DragDropMode.NoDragDrop


def test_stage_grid_dragging_a_card_swaps_order(qtbot):
    grid = StageGrid(slice_count=3)
    qtbot.addWidget(grid)

    first_card = grid.itemWidget(grid.item(0))
    assert first_card is not None

    grid._apply_reorder(0, 1)

    qtbot.waitUntil(lambda: grid.order() == [1, 0, 2], timeout=1000)


def test_stage_grid_keeps_original_badge_after_reorder(qtbot):
    grid = StageGrid(slice_count=3)
    qtbot.addWidget(grid)

    first_card = grid.itemWidget(grid.item(0))
    assert first_card is not None
    assert first_card.badge.text() == "01"

    grid._apply_reorder(0, 1)

    qtbot.waitUntil(lambda: grid.order() == [1, 0, 2], timeout=1000)

    moved_card = grid.itemWidget(grid.item(1))
    assert moved_card is not None
    assert moved_card.badge.text() == "01"
    assert moved_card.position_label.text() == "当前位置 · 第 2 位"
