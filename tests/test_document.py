"""
Unit tests for Coopixel document model, sparse storage, pycaml .pix serialization, PNG export, selection model, bucket fill, layer effects, and CLI file loading.
"""

import os
import tempfile
import pytest
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication
from coopixel.models.document import Layer, PixelDocument
from coopixel.models.effects import StrokeEffect
from coopixel.models.selection import SelectionModel
from coopixel.tools.drawing import BucketFillTool
from coopixel.tools.selection import SelectionTool
from coopixel.ui.main_window import MainWindow


def test_layer_sparse_storage():
    layer = Layer(name="Test Layer")
    assert len(layer.pixels) == 0

    # Set pixel
    layer.set_pixel(5, 10, "#FF0000FF")
    assert layer.get_pixel(5, 10) == "#FF0000FF"
    assert len(layer.pixels) == 1
    assert "5,10" in layer.pixels

    # Setting transparent clears the pixel (sparse storage)
    layer.set_pixel(5, 10, "#00000000")
    assert layer.get_pixel(5, 10) is None
    assert len(layer.pixels) == 0
    assert "5,10" not in layer.pixels


def test_document_layers_and_pycaml_pix_storage():
    doc = PixelDocument(16, 16)
    assert len(doc.layers) == 1
    assert doc.layers[0].name == "Background"

    # Add second layer
    top_layer = doc.add_layer("Foreground")
    assert len(doc.layers) == 2
    assert doc.active_layer == top_layer

    # Paint pixels on both layers
    doc.layers[0].set_pixel(0, 0, "#0000FFFF")  # Blue on background
    doc.layers[1].set_pixel(2, 2, "#FF0000FF")  # Red on foreground

    # Save to temp .pix file using pycaml
    with tempfile.NamedTemporaryFile(suffix=".pix", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        doc.save_to_pix(tmp_path)
        assert os.path.exists(tmp_path)
        assert os.path.getsize(tmp_path) > 0

        # Load back from .pix file using pycaml
        loaded_doc = PixelDocument.load_from_pix(tmp_path)
        assert loaded_doc.width == 16
        assert loaded_doc.height == 16
        assert len(loaded_doc.layers) == 2
        assert loaded_doc.layers[0].name == "Background"
        assert loaded_doc.layers[1].name == "Foreground"
        assert loaded_doc.layers[0].get_pixel(0, 0) == "#0000FFFF"
        assert loaded_doc.layers[1].get_pixel(2, 2) == "#FF0000FF"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_document_png_export():
    doc = PixelDocument(8, 8)
    layer = doc.active_layer
    layer.set_pixel(1, 1, "#00FF00FF")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        success = doc.export_png(tmp_path)
        assert success is True
        assert os.path.exists(tmp_path)
        assert os.path.getsize(tmp_path) > 0

        img = QImage(tmp_path)
        assert img.width() == 8
        assert img.height() == 8
        col = QColor(img.pixelColor(1, 1))
        assert col.green() > 200
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_selection_and_bucket_fill():
    doc = PixelDocument(10, 10)
    sel = SelectionModel()

    # Test selection operations
    sel.select([(1, 1), (1, 2), (2, 1), (2, 2)])
    assert len(sel.selected) == 4
    assert sel.is_selected(1, 1)
    assert not sel.is_selected(5, 5)

    sel.invert(doc)
    assert len(sel.selected) == 96
    assert not sel.is_selected(1, 1)
    assert sel.is_selected(5, 5)

    sel.clear()
    assert sel.is_empty()

    # Test SelectionTool box mode
    sel_tool = SelectionTool(sel)
    sel_tool.mode = SelectionTool.BOX
    sel_tool._drag_start = (0, 0)
    sel_tool.mouse_release(doc, 2, 2, "#FF0000FF", "#00000000")
    assert len(sel.selected) == 9

    # Test bucket fill contiguous mode
    fill_tool = BucketFillTool()
    fill_tool.fill_mode = BucketFillTool.CONTIGUOUS
    doc.active_layer.set_pixel(5, 5, "#00FF00FF")
    doc.active_layer.set_pixel(5, 6, "#00FF00FF")

    fill_tool.mouse_press(doc, 5, 5, "#FF0000FF", "#00000000")
    assert doc.active_layer.get_pixel(5, 5) == "#FF0000FF"
    assert doc.active_layer.get_pixel(5, 6) == "#FF0000FF"


def test_layer_stroke_effect():
    doc = PixelDocument(10, 10)
    layer = doc.active_layer
    layer.set_pixel(5, 5, "#FF0000FF")  # Single red pixel in center

    stroke = StrokeEffect(enabled=True, size=1, color="#0000FFFF", position="outside")
    layer.effects.append(stroke)

    below_map, above_map = stroke.render_effect(layer.pixels, doc.width, doc.height)
    assert len(below_map) == 8
    assert "4,5" in below_map
    assert "6,5" in below_map
    assert "5,4" in below_map
    assert "5,6" in below_map
    assert below_map["4,5"] == "#0000FFFF"


def test_cli_file_opening():
    app = QApplication.instance() or QApplication([])
    mw = MainWindow()
    assert mw.windowTitle() == "Coopixel - Pixel Art Editor"
    mw.close()


def test_copy_paste_across_layers():
    app = QApplication.instance() or QApplication([])
    mw = MainWindow()

    # Draw pixel on layer 1
    l1 = mw.doc.active_layer
    l1.set_pixel(2, 3, "#FF0000FF")

    # Select all canvas and copy
    mw.on_select_all()
    assert len(mw.canvas.selection.selected) == mw.doc.width * mw.doc.height
    mw.on_copy()
    assert hasattr(mw, "clipboard_data")
    assert (2, 3) in mw.clipboard_data["pixels"]
    assert mw.clipboard_data["pixels"][(2, 3)] == "#FF0000FF"

    # Add layer 2 and paste
    l2 = mw.doc.add_layer("Layer 2")
    assert mw.doc.active_layer == l2
    assert l2.get_pixel(2, 3) is None

    mw.on_paste()
    assert l2.get_pixel(2, 3) == "#FF0000FF"
    mw.close()


def test_cli_file_loading_actual():
    app = QApplication.instance() or QApplication([])
    doc = PixelDocument(12, 12)
    doc.active_layer.set_pixel(3, 4, "#FF004DFF")

    with tempfile.NamedTemporaryFile(suffix=".pix", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        doc.save_to_pix(tmp_path)
        window = MainWindow()
        success = window.open_file(tmp_path)
        assert success is True
        assert window.doc.active_layer.get_pixel(3, 4) == "#FF004DFF"
        assert tmp_path in window.windowTitle()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_copy_paste_entire_layer():
    app = QApplication.instance() or QApplication([])
    mw = MainWindow()

    # Configure active layer
    l1 = mw.doc.active_layer
    l1.name = "Custom Layer 1"
    l1.set_pixel(1, 1, "#00FF00FF")
    l1.opacity = 0.8

    # Copy layer via layer panel
    mw.layer_panel.on_copy_layer()

    # Switch frame and paste layer
    mw.doc.add_frame("Frame 2")
    assert len(mw.doc.layers) == 1
    assert mw.doc.active_layer.get_pixel(1, 1) is None

    mw.layer_panel.on_paste_layer()
    assert len(mw.doc.layers) == 2
    pasted = mw.doc.active_layer
    assert pasted.name == "Custom Layer 1 Copy"
    assert pasted.get_pixel(1, 1) == "#00FF00FF"
    assert pasted.opacity == 0.8
    mw.close()

