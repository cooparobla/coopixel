"""
Tests for Shortcuts configuration and Path node / Bezier handle editing in Coopixel.
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication

from coopixel.models.document import PixelDocument
from coopixel.models.path import AnchorPoint, VectorPath
from coopixel.tools.pen import PenTool
from coopixel.tools.move import MoveTool
from coopixel.ui.shortcuts_dialog import DEFAULT_SHORTCUTS, load_shortcuts, save_shortcuts, ShortcutsDialog


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_shortcuts_default_pen_key():
    shortcuts = load_shortcuts()
    assert shortcuts["tool_pen"] == "P"
    assert shortcuts["tool_pivot"] == "Shift+P"


def test_shortcuts_dialog(qapp):
    dlg = ShortcutsDialog()
    assert dlg.table.rowCount() == len(DEFAULT_SHORTCUTS)


def test_pen_tool_shift_only_bezier_handles(qapp):
    doc = PixelDocument(20, 20)
    pen = PenTool()

    # Add first point without shift -> node point, no handle dragging
    pen.mouse_press(doc, 5, 5, "#FF0000FF", "#00000000", shift_pressed=False)
    assert pen.is_dragging_handle is False

    path = doc.active_path
    assert len(path.anchors) == 1
    anchor = path.anchors[0]
    assert anchor.handle_out_x == 0.0
    assert anchor.handle_out_y == 0.0

    # Add second point WITH shift -> handle dragging enabled
    pen.mouse_press(doc, 10, 5, "#FF0000FF", "#00000000", shift_pressed=True)
    assert pen.is_dragging_handle is True

    # Drag to edit Bezier handles
    pen.mouse_move(doc, 12, 8, "#FF0000FF", "#00000000", shift_pressed=True)
    anchor2 = path.anchors[1]
    assert anchor2.handle_out_x != 0.0 or anchor2.handle_out_y != 0.0


def test_pen_tool_handle_knob_dragging(qapp):
    doc = PixelDocument(20, 20)
    doc.add_path()
    path = doc.active_path

    # Anchor with pre-existing handle knob
    a = AnchorPoint(10, 10, handle_in_x=-2, handle_in_y=0, handle_out_x=2, handle_out_y=0)
    path.add_anchor(a)

    pen = PenTool()
    pen.selected_anchor_idx = 0

    # Click on handle_out knob at (12, 10) without shift
    pen.mouse_press(doc, 12, 10, "#FF0000FF", "#00000000", shift_pressed=False)
    assert pen.selected_handle == "handle_out"

    # Drag handle_out knob to (14, 12)
    pen.mouse_move(doc, 14, 12, "#FF0000FF", "#00000000", shift_pressed=False)
    assert path.anchors[0].handle_out_x == 4.0
    assert path.anchors[0].handle_out_y == 2.0


def test_move_tool_path_node_movement(qapp):
    doc = PixelDocument(20, 20)
    doc.add_path()
    path = doc.active_path
    path.add_anchor(AnchorPoint(2, 2))
    path.add_anchor(AnchorPoint(8, 8))

    move = MoveTool()
    move.mouse_press(doc, 0, 0, "#FF0000FF", "#00000000", path_panel_open=True)
    move.mouse_move(doc, 5, 5, "#FF0000FF", "#00000000", path_panel_open=True)

    assert path.anchors[0].x == 7.0
    assert path.anchors[0].y == 7.0
    assert path.anchors[1].x == 13.0
    assert path.anchors[1].y == 13.0
