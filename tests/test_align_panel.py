"""
Unit tests for AlignPanel layer alignment functionality in Coopixel.
"""

import pytest
from coopixel.models.document import PixelDocument
from coopixel.ui.align_panel import AlignPanel
from coopixel.ui.main_window import MainWindow


def test_align_panel_modes():
    doc = PixelDocument(32, 32)
    layer = doc.active_layer

    # Create a 4x4 block at (10, 10) -> bbox is (10, 10, 4, 4)
    for x in range(10, 14):
        for y in range(10, 14):
            layer.set_pixel(x, y, "#FF0000FF")

    align_panel = AlignPanel(doc)

    # 1. Align Left -> target bx = 0
    align_panel.align_active_layer("left")
    assert layer.get_content_bbox() == (0, 10, 4, 4)

    # 2. Align Right -> target bx = 32 - 4 = 28
    align_panel.align_active_layer("right")
    assert layer.get_content_bbox() == (28, 10, 4, 4)

    # 3. Align Center H -> target bx = (32 - 4) // 2 = 14
    align_panel.align_active_layer("center_h")
    assert layer.get_content_bbox() == (14, 10, 4, 4)

    # 4. Align Top -> target by = 0
    align_panel.align_active_layer("top")
    assert layer.get_content_bbox() == (14, 0, 4, 4)

    # 5. Align Bottom -> target by = 32 - 4 = 28
    align_panel.align_active_layer("bottom")
    assert layer.get_content_bbox() == (14, 28, 4, 4)

    # 6. Align Center V -> target by = (32 - 4) // 2 = 14
    align_panel.align_active_layer("center_v")
    assert layer.get_content_bbox() == (14, 14, 4, 4)

    # 7. Align Center Both -> target (14, 14, 4, 4)
    # Move off center first
    align_panel.align_active_layer("left")
    align_panel.align_active_layer("top")
    assert layer.get_content_bbox() == (0, 0, 4, 4)

    align_panel.align_active_layer("center_both")
    assert layer.get_content_bbox() == (14, 14, 4, 4)


def test_align_panel_main_window_integration(qtbot):
    mw = MainWindow()
    qtbot.addWidget(mw)
    mw.show()

    # Draw pixel block on layer
    mw.doc.active_layer.set_pixel(2, 2, "#00FF00FF")
    mw._push_history()

    # Toggle align panel
    assert mw.align_panel.isVisible() is False
    mw.align_panel.show()
    assert mw.align_panel.isVisible() is True

    # Click center both button
    mw.align_panel.btn_center_both.click()

    # 1x1 pixel in 32x32 canvas centered at (15, 15)
    bbox = mw.doc.active_layer.get_content_bbox()
    assert bbox == (15, 15, 1, 1)

    # Verify history undo restores original position (2, 2)
    mw.on_undo()
    bbox_after_undo = mw.doc.active_layer.get_content_bbox()
    assert bbox_after_undo == (2, 2, 1, 1)
