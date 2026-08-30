"""
Unit tests for Vector Paths, Bezier curves, Pen Tool, dynamic stroke/fill, and Paths Panel in Coopixel.
"""

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication
from coopixel.models.document import PixelDocument
from coopixel.models.path import AnchorPoint, VectorPath
from coopixel.tools.pen import PenTool
from coopixel.ui.path_panel import PathPanel, PathItemWidget


def test_anchor_point_and_handles():
    a = AnchorPoint(10.0, 20.0, handle_in_x=-2.0, handle_in_y=-3.0, handle_out_x=2.0, handle_out_y=3.0)
    assert a.x == 10.0
    assert a.y == 20.0
    assert a.handle_in_abs == QPointF(8.0, 17.0)
    assert a.handle_out_abs == QPointF(12.0, 23.0)

    # Set absolute handle
    a.set_handle_out_abs(15.0, 25.0)
    assert a.handle_out_x == 5.0
    assert a.handle_out_y == 5.0

    # Serialization
    d = a.to_dict()
    restored = AnchorPoint.from_dict(d)
    assert restored.x == 10.0
    assert restored.handle_out_x == 5.0


def test_vector_path_dynamic_stroke_and_fill_properties():
    vp = VectorPath("Test Path", layer_id="Background", closed=True, stroked=True, filled=True)
    vp.add_anchor(AnchorPoint(5, 5, 0, 0, 2, 0))
    vp.add_anchor(AnchorPoint(15, 5, -2, 0, 0, 2))
    vp.add_anchor(AnchorPoint(15, 15, 0, -2, 0, 0))

    assert vp.stroked is True
    assert vp.filled is True

    qpath = vp.to_qpainterpath()
    assert not qpath.isEmpty()
    assert qpath.elementCount() >= 3

    # Document serialization
    doc = PixelDocument(32, 32)
    doc.paths.append(vp)
    doc.active_path_index = 0

    serialized = doc.to_dict()
    assert len(serialized["paths"]) == 1
    assert serialized["paths"][0]["name"] == "Test Path"
    assert serialized["paths"][0]["stroked"] is True
    assert serialized["paths"][0]["filled"] is True

    restored_doc = PixelDocument.from_dict(serialized)
    assert len(restored_doc.paths) == 1
    assert restored_doc.paths[0].name == "Test Path"
    assert restored_doc.paths[0].closed is True
    assert restored_doc.paths[0].stroked is True
    assert restored_doc.paths[0].filled is True


def test_path_stroke_and_fill_rasterization():
    doc = PixelDocument(32, 32)
    path = doc.add_path("Box Path", layer_id="Background")
    path.add_anchor(AnchorPoint(5, 5))
    path.add_anchor(AnchorPoint(20, 5))
    path.add_anchor(AnchorPoint(20, 20))
    path.add_anchor(AnchorPoint(5, 20))
    path.closed = True

    # Stroke path
    stroked_pixels = doc.stroke_path(path, "#FF0000FF", size=1)
    assert stroked_pixels > 0
    assert len(doc.active_layer.pixels) > 0

    # Clear & Fill path
    doc.active_layer.pixels.clear()
    filled_pixels = doc.fill_path(path, "#00FF00FF")
    assert filled_pixels > 0
    assert len(doc.active_layer.pixels) > 0


def test_pen_tool_mouse_interaction():
    app = QApplication.instance() or QApplication([])
    doc = PixelDocument(32, 32)
    pen = PenTool()

    # Click 1: Add first anchor point
    pen.mouse_press(doc, 5, 5, "#FF0000FF", "#000000FF")
    pen.mouse_release(doc, 5, 5, "#FF0000FF", "#000000FF")
    assert len(doc.paths) == 1
    assert len(doc.active_path.anchors) == 1

    # Click 2: Add second anchor point and drag handle
    pen.mouse_press(doc, 15, 10, "#FF0000FF", "#000000FF", shift_pressed=True)
    pen.mouse_move(doc, 18, 12, "#FF0000FF", "#000000FF")
    pen.mouse_release(doc, 18, 12, "#FF0000FF", "#000000FF")
    assert len(doc.active_path.anchors) == 2
    assert doc.active_path.anchors[1].handle_out_x != 0.0

    # Normal Click & Drag node 0: moves node position
    pen.mouse_press(doc, 5, 5, "#FF0000FF", "#000000FF", shift_pressed=False)
    pen.mouse_move(doc, 7, 8, "#FF0000FF", "#000000FF")
    pen.mouse_release(doc, 7, 8, "#FF0000FF", "#000000FF")
    assert doc.active_path.anchors[0].x == 7.0
    assert doc.active_path.anchors[0].y == 8.0

    # Shift-Click & Drag node 0: alters Bezier curve factor (handles)
    pen.mouse_press(doc, 7, 8, "#FF0000FF", "#000000FF", shift_pressed=True)
    pen.mouse_move(doc, 10, 10, "#FF0000FF", "#000000FF")
    pen.mouse_release(doc, 10, 10, "#FF0000FF", "#000000FF")
    assert doc.active_path.anchors[0].handle_out_x == 3.0
    assert doc.active_path.anchors[0].handle_out_y == 2.0
    assert doc.active_path.anchors[0].handle_in_x == -3.0
    assert doc.active_path.anchors[0].handle_in_y == -2.0


def test_clicking_first_anchor_does_not_close_path():
    app = QApplication.instance() or QApplication([])
    doc = PixelDocument(32, 32)
    pen = PenTool()

    # Add 3 anchors
    pen.mouse_press(doc, 5, 5, "#FF0000FF", "#000000FF")
    pen.mouse_release(doc, 5, 5, "#FF0000FF", "#000000FF")
    pen.mouse_press(doc, 15, 5, "#FF0000FF", "#000000FF")
    pen.mouse_release(doc, 15, 5, "#FF0000FF", "#000000FF")
    pen.mouse_press(doc, 10, 15, "#FF0000FF", "#000000FF")
    pen.mouse_release(doc, 10, 15, "#FF0000FF", "#000000FF")

    assert doc.active_path.closed is False

    # Click first anchor (5, 5) — must NOT close loop automatically
    pen.mouse_press(doc, 5, 5, "#FF0000FF", "#000000FF")
    pen.mouse_release(doc, 5, 5, "#FF0000FF", "#000000FF")

    assert doc.active_path.closed is False

    # Path loop toggles explicitly via path.closed property / PathPanel checkbox
    doc.active_path.closed = True
    assert doc.active_path.closed is True




def test_path_panel_ui():
    app = QApplication.instance() or QApplication([])
    doc = PixelDocument(32, 32)
    doc.add_path("Path Alpha")
    panel = PathPanel(doc)

    assert panel.list_widget.count() == 1

    # Test PathItemWidget collapsible options drawer & variables
    item_widget = panel.list_widget.itemWidget(panel.list_widget.item(0))
    assert isinstance(item_widget, PathItemWidget)
    assert item_widget.stroke_btn.isChecked() is True
    assert item_widget.options_container.isHidden() is True  # Defaults to COLLAPSED

    item_widget._toggle_expand()
    assert item_widget.options_container.isHidden() is False  # Expanded

    item_widget.stroke_spin.setValue(5)
    assert doc.paths[0].stroke_width == 5

    doc.primary_color = "#00FF00FF"
    item_widget._set_stroke_to_primary()
    assert doc.paths[0].stroke_color == "#00FF00FF"

    item_widget._set_fill_to_primary()
    assert doc.paths[0].fill_color == "#00FF00FF"

    item_widget.fill_btn.setChecked(True)
    assert doc.paths[0].filled is True



    panel.on_add_path()
    assert panel.list_widget.count() == 2
    assert len(doc.paths) == 2

    panel.on_delete_path()
    assert panel.list_widget.count() == 1
    assert len(doc.paths) == 1

    panel.close()


def test_move_tool_path_translation_when_paths_panel_open():
    from coopixel.tools.move import MoveTool

    doc = PixelDocument(32, 32)
    doc.active_layer.set_pixel(0, 0, "#FF0000FF")
    doc.active_layer.set_pixel(1, 0, "#FF0000FF")
    doc.active_layer.set_pixel(0, 1, "#FF0000FF")

    path = doc.add_path("Move Test Path")
    path.add_anchor(AnchorPoint(10.0, 10.0))
    path.add_anchor(AnchorPoint(20.0, 20.0))

    move_tool = MoveTool()

    # 1. When path_panel_open is False: MoveTool moves layer pixels, NOT path
    move_tool.mouse_press(doc, 0, 0, "#FF0000FF", "#000000FF", path_panel_open=False)
    move_tool.mouse_move(doc, 3, 3, "#FF0000FF", "#000000FF", path_panel_open=False)
    move_tool.mouse_release(doc, 3, 3, "#FF0000FF", "#000000FF")

    assert path.anchors[0].x == 10.0  # Path did NOT move
    assert doc.active_layer.pixels.get("3,3") == "#FF0000FF"  # Layer pixels moved (dx=+3, dy=+3)

    # 2. When path_panel_open is True: MoveTool moves active vector path, NOT layer
    doc.active_layer.pixels = {"0,0": "#FF0000FF"}

    move_tool.mouse_press(doc, 10, 10, "#FF0000FF", "#000000FF", path_panel_open=True)
    move_tool.mouse_move(doc, 15, 12, "#FF0000FF", "#000000FF", path_panel_open=True)
    move_tool.mouse_release(doc, 15, 12, "#FF0000FF", "#000000FF")

    assert path.anchors[0].x == 15.0  # Path shifted dx=+5, dy=+2
    assert path.anchors[0].y == 12.0
    assert path.anchors[1].x == 25.0
    assert path.anchors[1].y == 22.0
    assert doc.active_layer.pixels.get("0,0") == "#FF0000FF"  # Layer pixels did NOT move!


