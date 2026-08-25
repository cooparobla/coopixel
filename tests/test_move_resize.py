"""
Unit tests for MoveTool layer resizing and square constraint in Coopixel.
"""

import pytest
from PySide6.QtCore import QPointF, Qt
from coopixel.models.document import PixelDocument
from coopixel.models.selection import SelectionModel
from coopixel.tools.move import MoveTool
from coopixel.ui.canvas import CanvasWidget


def test_move_tool_hit_test_handle():
    doc = PixelDocument(32, 32)
    layer = doc.active_layer
    # Create a 4x4 block at (10, 10) to (13, 13)
    for x in range(10, 14):
        for y in range(10, 14):
            layer.set_pixel(x, y, "#FF0000FF")

    bbox = layer.get_content_bbox()
    assert bbox == (10, 10, 4, 4)

    move_tool = MoveTool()
    pan_offset = QPointF(0, 0)
    zoom = 10.0

    # Bottom-right corner screen coord = pan_offset + (bx + bw)*zoom = (14 * 10, 14 * 10) = (140, 140)
    handle_center = QPointF(140.0, 140.0)

    # Hover near handle center -> should hit handle
    assert move_tool.is_over_resize_handle(doc, handle_center, pan_offset, zoom) is True
    assert move_tool.is_over_resize_handle(doc, QPointF(142.0, 138.0), pan_offset, zoom) is True

    # Hover far from handle -> should not hit
    assert move_tool.is_over_resize_handle(doc, QPointF(100.0, 100.0), pan_offset, zoom) is False


def test_move_tool_resize_layer():
    doc = PixelDocument(32, 32)
    layer = doc.active_layer
    # Create a 2x2 square at (5, 5) -> (6, 6)
    layer.set_pixel(5, 5, "#FF0000FF")
    layer.set_pixel(6, 5, "#FF0000FF")
    layer.set_pixel(5, 6, "#FF0000FF")
    layer.set_pixel(6, 6, "#FF0000FF")

    move_tool = MoveTool()
    pan_offset = QPointF(0.0, 0.0)
    zoom = 1.0

    # Press on handle (bottom-right is at x=7, y=7 in canvas space)
    move_tool.mouse_press(
        doc,
        7,
        7,
        "#FF0000FF",
        "#00000000",
        screen_pos=QPointF(7.0, 7.0),
        pan_offset=pan_offset,
        zoom=zoom,
    )
    assert move_tool.is_resizing is True

    # Drag to double the size: x=9, y=9 (new_w = 9-5 = 4, new_h = 9-5 = 4)
    changed = move_tool.mouse_move(doc, 9, 9, "#FF0000FF", "#00000000")
    assert changed is True

    # Check that layer now spans (5, 5) to (8, 8) -> 4x4 box
    assert len(layer.pixels) == 16
    for x in range(5, 9):
        for y in range(5, 9):
            assert layer.get_pixel(x, y) == "#FF0000FF"

    # Mouse release
    committed = move_tool.mouse_release(doc, 9, 9, "#FF0000FF", "#00000000")
    assert committed is True
    assert move_tool.is_resizing is False


def test_move_tool_resize_square_constraint():
    doc = PixelDocument(32, 32)
    layer = doc.active_layer
    # Create 2x2 square at (10, 10)
    for x in range(10, 12):
        for y in range(10, 12):
            layer.set_pixel(x, y, "#00FF00FF")

    move_tool = MoveTool()
    pan_offset = QPointF(0.0, 0.0)
    zoom = 1.0

    # Press on handle at (12, 12)
    move_tool.mouse_press(
        doc,
        12,
        12,
        "#FF0000FF",
        "#00000000",
        screen_pos=QPointF(12.0, 12.0),
        pan_offset=pan_offset,
        zoom=zoom,
    )

    # Enable square constraint (Shift key)
    move_tool.constrain_square = True

    # Drag rectangularly to x=18, y=14 -> without shift w=8, h=4; with shift w=8, h=8
    move_tool.mouse_move(doc, 18, 14, "#FF0000FF", "#00000000")

    # Content bbox should be 8x8 square at (10, 10, 8, 8)
    bbox = layer.get_content_bbox()
    assert bbox == (10, 10, 8, 8)


def test_canvas_widget_move_handle_cursor(qtbot):
    doc = PixelDocument(32, 32)
    layer = doc.active_layer
    layer.set_pixel(5, 5, "#FF0000FF")
    layer.set_pixel(6, 6, "#FF0000FF")

    canvas = CanvasWidget(doc)
    qtbot.addWidget(canvas)
    canvas.show()

    move_tool = MoveTool()
    canvas.active_tool = move_tool

    # Bottom-right handle is at (ox + 7*zoom, oy + 7*zoom) = (40 + 112, 40 + 112) = (152, 152)
    handle_pos = QPointF(canvas.pan_offset.x() + 7 * canvas.zoom_level, canvas.pan_offset.y() + 7 * canvas.zoom_level)

    assert move_tool.is_over_resize_handle(doc, handle_pos, canvas.pan_offset, canvas.zoom_level) is True


def test_tool_size_hotkeys(qtbot):
    from coopixel.ui.main_window import MainWindow

    mw = MainWindow()
    qtbot.addWidget(mw)
    mw.show()

    # Initial size should be 1
    assert mw.tool_panel.size_spin.value() == 1
    assert mw.canvas.brush_size == 1

    # Trigger increase hotkey ]
    mw._increase_brush_size()
    assert mw.tool_panel.size_spin.value() == 2
    assert mw.canvas.brush_size == 2

    # Trigger decrease hotkey [
    mw._decrease_brush_size()
    assert mw.tool_panel.size_spin.value() == 1
    assert mw.canvas.brush_size == 1


def test_hover_cursor_brush_size(qtbot):
    from coopixel.tools.drawing import PencilTool

    doc = PixelDocument(32, 32)
    canvas = CanvasWidget(doc)
    qtbot.addWidget(canvas)
    canvas.show()

    pencil = PencilTool()
    canvas.active_tool = pencil
    canvas.brush_size = 4
    canvas.hover_coord = (10, 10)

def test_center_canvas_hotkey(qtbot):
    from coopixel.ui.main_window import MainWindow

    mw = MainWindow()
    qtbot.addWidget(mw)
    mw.resize(800, 600)
    mw.show()

    # Move pan offset off center
    mw.canvas.pan_offset = QPointF(500.0, 500.0)

    # Press A hotkey / trigger _center_canvas
    mw._center_canvas()

    # Canvas should be centered
    expected_x = (mw.canvas.width() - (mw.doc.width * mw.canvas.zoom_level)) / 2.0
    expected_y = (mw.canvas.height() - (mw.doc.height * mw.canvas.zoom_level)) / 2.0
    assert abs(mw.canvas.pan_offset.x() - expected_x) < 1.0
    assert abs(mw.canvas.pan_offset.y() - expected_y) < 1.0



