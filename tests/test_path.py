"""
Unit tests for Vector Paths, Bezier curves, Pen Tool, and Paths Panel in Coopixel.
"""

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication
from coopixel.models.document import PixelDocument
from coopixel.models.path import AnchorPoint, VectorPath
from coopixel.tools.pen import PenTool
from coopixel.ui.path_panel import PathPanel


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


def test_vector_path_qpainterpath_generation():
    vp = VectorPath("Test Path", layer_id="Background", closed=True)
    vp.add_anchor(AnchorPoint(5, 5, 0, 0, 2, 0))
    vp.add_anchor(AnchorPoint(15, 5, -2, 0, 0, 2))
    vp.add_anchor(AnchorPoint(15, 15, 0, -2, 0, 0))

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

    restored_doc = PixelDocument.from_dict(serialized)
    assert len(restored_doc.paths) == 1
    assert restored_doc.paths[0].name == "Test Path"
    assert restored_doc.paths[0].closed is True


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
    pen.mouse_press(doc, 15, 10, "#FF0000FF", "#000000FF")
    pen.mouse_move(doc, 18, 12, "#FF0000FF", "#000000FF")
    pen.mouse_release(doc, 18, 12, "#FF0000FF", "#000000FF")
    assert len(doc.active_path.anchors) == 2
    assert doc.active_path.anchors[1].handle_out_x != 0.0


def test_path_panel_ui():
    app = QApplication.instance() or QApplication([])
    doc = PixelDocument(32, 32)
    doc.add_path("Path Alpha")
    panel = PathPanel(doc)

    assert panel.list_widget.count() == 1
    assert "Path Alpha" in panel.list_widget.item(0).text()

    panel.on_add_path()
    assert panel.list_widget.count() == 2
    assert len(doc.paths) == 2

    panel.on_delete_path()
    assert panel.list_widget.count() == 1
    assert len(doc.paths) == 1

    panel.close()
