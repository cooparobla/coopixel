"""
Unit tests for multi-layer editing (simultaneous drawing and erasing across multiple layers)
and live editing performance optimizations in Coopixel.
"""

import time
import pytest
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QKeyEvent
from coopixel.models.document import PixelDocument, Layer
from coopixel.tools.drawing import PencilTool, EraserTool, BucketFillTool
from coopixel.tools.shapes import LineTool, RectangleTool, CircleTool
from coopixel.ui.canvas import CanvasWidget
from coopixel.ui.layer_panel import LayerPanel
from coopixel.ui.main_window import MainWindow


def test_multi_layer_pencil_drawing():
    """Verify drawing with PencilTool applies pixels across all selected editable layers."""
    doc = PixelDocument(16, 16)
    l1 = doc.active_layer
    l1.name = "Layer 1"

    l2 = doc.add_layer("Layer 2")
    l3 = doc.add_layer("Layer 3")

    # Select Layer 1 and Layer 2
    doc.set_selected_layer_indices([0, 1])
    assert len(doc.editable_layers) == 2

    tool = PencilTool()
    tool.mouse_press(doc, 5, 5, "#FF0000FF", "#00000000", size=1)
    tool.mouse_release(doc, 5, 5, "#FF0000FF", "#00000000", size=1)

    # Layer 1 and Layer 2 should have pixel at (5, 5)
    assert l1.get_pixel(5, 5) == "#FF0000FF"
    assert l2.get_pixel(5, 5) == "#FF0000FF"
    # Layer 3 was not selected, so should remain empty
    assert l3.get_pixel(5, 5) is None


def test_multi_layer_eraser():
    """Verify EraserTool clears pixels across all selected editable layers."""
    doc = PixelDocument(16, 16)
    l1 = doc.active_layer
    l1.set_pixel(3, 3, "#FF0000FF")

    l2 = doc.add_layer("Layer 2")
    l2.set_pixel(3, 3, "#00FF00FF")

    l3 = doc.add_layer("Layer 3")
    l3.set_pixel(3, 3, "#0000FFFF")

    # Select all three layers
    doc.set_selected_layer_indices([0, 1, 2])
    assert len(doc.editable_layers) == 3

    tool = EraserTool()
    tool.mouse_press(doc, 3, 3, "#00000000", "#00000000", size=1)
    tool.mouse_release(doc, 3, 3, "#00000000", "#00000000", size=1)

    assert l1.has_pixel(3, 3) is False
    assert l2.has_pixel(3, 3) is False
    assert l3.has_pixel(3, 3) is False


def test_multi_layer_shapes_and_fill():
    """Verify shape tools (Rectangle, Circle, Line) and Bucket Fill draw on all selected layers."""
    doc = PixelDocument(16, 16)
    l1 = doc.active_layer
    l2 = doc.add_layer("Layer 2")
    doc.set_selected_layer_indices([0, 1])

    rect_tool = RectangleTool()
    rect_tool.mouse_press(doc, 1, 1, "#FFFF00FF", "#00000000", size=1, filled=True)
    rect_tool.mouse_release(doc, 3, 3, "#FFFF00FF", "#00000000", size=1, filled=True)

    assert l1.get_pixel(2, 2) == "#FFFF00FF"
    assert l2.get_pixel(2, 2) == "#FFFF00FF"

    # Bucket Fill
    fill_tool = BucketFillTool()
    fill_tool.mouse_press(doc, 2, 2, "#00FFFFFF", "#00000000")
    assert l1.get_pixel(2, 2) == "#00FFFFFF"
    assert l2.get_pixel(2, 2) == "#00FFFFFF"


def test_multi_layer_locked_and_invisible_protection():
    """Verify locked or invisible layers are protected from multi-layer edits."""
    doc = PixelDocument(16, 16)
    l1 = doc.active_layer
    l1.name = "Normal"

    l2 = doc.add_layer("Locked")
    l2.locked = True

    l3 = doc.add_layer("Hidden")
    l3.visible = False

    # Select all layers
    doc.set_selected_layer_indices([0, 1, 2])
    assert doc.editable_layers == [l1]

    tool = PencilTool()
    tool.mouse_press(doc, 4, 4, "#FF0000FF", "#00000000", size=1)
    tool.mouse_release(doc, 4, 4, "#FF0000FF", "#00000000", size=1)

    assert l1.get_pixel(4, 4) == "#FF0000FF"
    assert l2.get_pixel(4, 4) is None
    assert l3.get_pixel(4, 4) is None


def test_layer_panel_select_all_toggle(qapp):
    """Verify clicking the 'All' button in LayerPanel toggles select-all across all layers."""
    doc = PixelDocument(16, 16)
    doc.add_layer("Layer 2")
    doc.add_layer("Layer 3")

    panel = LayerPanel(doc)
    assert len(panel.list_widget.selectedItems()) == 1

    # Click 'All' -> selects all 3 layers
    panel.on_toggle_select_all()
    assert len(panel.list_widget.selectedItems()) == 3
    assert len(doc.selected_layers) == 3

    # Click 'All' again -> deselects back to active layer
    panel.on_toggle_select_all()
    assert len(panel.list_widget.selectedItems()) == 1


def test_selection_delete_across_multiple_layers(qapp):
    """Verify pressing Delete key clears selection across all selected editable layers."""
    doc = PixelDocument(16, 16)
    l1 = doc.active_layer
    l1.set_pixel(2, 2, "#FF0000FF")

    l2 = doc.add_layer("Layer 2")
    l2.set_pixel(2, 2, "#00FF00FF")

    doc.set_selected_layer_indices([0, 1])

    canvas = CanvasWidget(doc)
    canvas.selection.replace({(2, 2)})

    event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier)
    canvas.keyPressEvent(event)

    assert l1.has_pixel(2, 2) is False
    assert l2.has_pixel(2, 2) is False
