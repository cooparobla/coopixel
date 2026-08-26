"""
Tests for Alt+Click color picker and Layer content selection features in Coopixel.
"""

import pytest
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from coopixel.models.document import PixelDocument, Layer
from coopixel.models.selection import SelectionModel
from coopixel.ui.canvas import CanvasWidget
from coopixel.ui.layer_panel import LayerPanel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_select_layer_pixels(qapp):
    doc = PixelDocument(10, 10)
    layer = doc.active_layer
    layer.set_pixel(2, 3, "#FF0000FF")
    layer.set_pixel(4, 5, "#00FF00FF")
    layer.set_pixel(9, 9, "#0000FFFF")

    sel = SelectionModel()
    sel.select_layer_pixels(layer, doc)

    assert sel.selected == {(2, 3), (4, 5), (9, 9)}


def test_select_layer_pixels_out_of_bounds(qapp):
    doc = PixelDocument(10, 10)
    layer = Layer(name="Test")
    layer.pixels["2,3"] = "#FF0000FF"
    layer.pixels["15,15"] = "#00FF00FF"  # out of bounds

    sel = SelectionModel()
    sel.select_layer_pixels(layer, doc)

    assert sel.selected == {(2, 3)}


def test_layer_panel_select_content_signal(qapp):
    doc = PixelDocument(16, 16)
    doc.add_layer("Layer 2")
    panel = LayerPanel(doc)

    emitted_indexes = []
    panel.select_layer_content_requested.connect(lambda idx: emitted_indexes.append(idx))

    panel._on_ctrl_click_layer(1)
    assert emitted_indexes == [1]
    assert doc.active_layer_index == 1


def test_canvas_alt_click_color_picker(qapp):
    doc = PixelDocument(10, 10)
    layer = doc.active_layer
    layer.set_pixel(3, 3, "#00FF00FF")

    canvas = CanvasWidget(doc)
    picked_colors = []
    canvas.color_picked.connect(lambda c: picked_colors.append(c))

    # Simulate Alt + Left click at canvas coordinate (3,3)
    # Target window coordinate for (3,3): pan_offset + 3 * zoom
    pos_x = canvas.pan_offset.x() + 3 * canvas.zoom_level + 2
    pos_y = canvas.pan_offset.y() + 3 * canvas.zoom_level + 2

    event = QMouseEvent(
        QMouseEvent.MouseButtonPress,
        QPointF(pos_x, pos_y),
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.AltModifier
    )

    canvas.mousePressEvent(event)

    assert len(picked_colors) == 1
    assert picked_colors[0] == "#00FF00FF"
