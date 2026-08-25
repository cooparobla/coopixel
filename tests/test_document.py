"""
Unit tests for Coopixel document model, sparse storage, pycaml .pix serialization, PNG export, selection model, bucket fill, layer effects, and CLI file loading.
"""

import os
import tempfile
import pytest
from PySide6.QtGui import QAction, QColor, QImage
from PySide6.QtWidgets import QApplication
from coopixel.models.document import Layer, PixelDocument
from coopixel.models.effects import StrokeEffect
from coopixel.models.selection import SelectionModel
from coopixel.tools.drawing import BucketFillTool
from coopixel.tools.selection import SelectionTool
from coopixel.ui.dialogs import CanvasSizeDialog, CropCanvasDialog, ImportImageDialog
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
    assert mw.windowTitle() == "COOPIXEL"
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


def test_import_png_as_layer():
    doc = PixelDocument(16, 16)

    # Create a temporary PNG image
    test_img = QImage(4, 4, QImage.Format_ARGB32)
    test_img.fill(QColor(0, 0, 0, 0))
    test_img.setPixelColor(1, 2, QColor(255, 0, 0, 255))

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        test_img.save(tmp_path, "PNG")
        imported_layer = doc.import_image_as_layer(tmp_path)
        assert imported_layer is not None
        assert imported_layer.get_pixel(1, 2) == "#FF0000FF"
        assert len(doc.layers) == 2
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_add_and_delete_layer_effects():
    app = QApplication.instance() or QApplication([])
    mw = MainWindow()

    # Add stroke effect
    mw.appearance_panel.add_stroke_effect()
    active = mw.doc.active_layer
    assert len(active.effects) == 1

    # Find the StrokeEffectWidget and trigger deletion button click
    effect_widget = mw.appearance_panel.effects_layout.itemAt(0).widget()
    assert effect_widget is not None
    effect_widget.del_btn.click()

    assert len(active.effects) == 0
    mw.close()


def test_canvas_resize_and_crop():
    doc = PixelDocument(10, 10)
    layer = doc.active_layer
    layer.set_pixel(2, 2, "#FF0000FF")
    layer.set_pixel(8, 8, "#00FF00FF")

    assert doc.get_content_bbox() == (2, 2, 7, 7)

    # Test top-left resize
    doc.resize_canvas(15, 15, anchor="top-left")
    assert doc.width == 15
    assert doc.height == 15
    assert layer.get_pixel(2, 2) == "#FF0000FF"
    assert layer.get_pixel(8, 8) == "#00FF00FF"

    # Test center resize
    doc.resize_canvas(20, 20, anchor="center")
    # off_x = (20 - 15) // 2 = 2, off_y = 2
    assert layer.get_pixel(4, 4) == "#FF0000FF"

    # Test crop canvas
    doc.crop_canvas(4, 4, 10, 10)
    assert doc.width == 10
    assert doc.height == 10
    assert layer.get_pixel(0, 0) == "#FF0000FF"
    # (8, 8) was at (10, 10) in 20x20 space, cropped to (6, 6) in 10x10 space
    assert layer.get_pixel(6, 6) == "#00FF00FF"


def test_crop_all_layers_purges_outside_data():
    doc = PixelDocument(32, 32)
    layer1 = doc.active_layer
    layer2 = doc.add_layer("Layer 2")

    # Set pixels inside and outside target crop box (x=8, y=8, w=16, h=16)
    layer1.set_pixel(2, 2, "#FF0000FF")    # Outside (top-left)
    layer1.set_pixel(10, 10, "#00FF00FF")  # Inside -> will become (2, 2)
    layer1.set_pixel(30, 30, "#0000FFFF")  # Outside (bottom-right)

    layer2.set_pixel(5, 5, "#FFFF00FF")    # Outside
    layer2.set_pixel(12, 12, "#FF00FFFF")  # Inside -> will become (4, 4)

    # Perform crop
    doc.crop_canvas(8, 8, 16, 16)

    assert doc.width == 16
    assert doc.height == 16

    # Verify layer 1: outside pixels purged, inside pixel shifted
    assert layer1.get_pixel(2, 2) == "#00FF00FF"
    assert len(layer1.pixels) == 1  # Only 1 pixel remains inside bounds

    # Verify layer 2: outside pixels purged, inside pixel shifted
    assert layer2.get_pixel(4, 4) == "#FF00FFFF"
    assert len(layer2.pixels) == 1  # Only 1 pixel remains inside bounds


def test_crop_tool_interactive():
    app = QApplication.instance() or QApplication([])
    mw = MainWindow()
    mw.doc.active_layer.set_pixel(3, 3, "#FFFF00FF")
    mw.doc.active_layer.set_pixel(4, 4, "#00FFFFFF")

    # Select crop tool
    mw.tool_panel.select_tool_by_key("crop")
    assert mw.canvas.active_tool.name == "crop"

    # Simulate mouse press & drag on canvas
    crop_tool = mw.canvas.active_tool
    crop_tool.mouse_press(mw.doc, 3, 3, "#000", "#000")
    crop_tool.mouse_move(mw.doc, 4, 4, "#000", "#000")
    crop_tool.mouse_release(mw.doc, 4, 4, "#000", "#000")

    assert crop_tool.crop_box == (3, 3, 2, 2)

    # Commit crop via MainWindow
    mw.on_crop_tool_commit_requested()

    assert mw.doc.width == 2
    assert mw.doc.height == 2
    assert mw.doc.active_layer.get_pixel(0, 0) == "#FFFF00FF"
    assert mw.doc.active_layer.get_pixel(1, 1) == "#00FFFFFF"
    mw.close()


def test_dialogs_crop_and_resize():
    app = QApplication.instance() or QApplication([])

    # Test CanvasSizeDialog
    resize_dlg = CanvasSizeDialog(32, 32)
    resize_dlg.width_spin.setValue(64)
    resize_dlg.height_spin.setValue(48)
    resize_dlg._on_anchor_clicked(4)  # center
    nw, nh, anchor = resize_dlg.get_values()
    assert nw == 64
    assert nh == 48
    assert anchor == "center"
    resize_dlg.close()

    # Test CropCanvasDialog
    crop_dlg = CropCanvasDialog(32, 32, selection_bbox=(4, 4, 16, 16), content_bbox=(2, 2, 20, 20))
    crop_dlg._apply_selection_bbox()
    x, y, w, h = crop_dlg.get_values()
    assert (x, y, w, h) == (4, 4, 16, 16)

    crop_dlg._apply_content_bbox()
    x, y, w, h = crop_dlg.get_values()
    assert (x, y, w, h) == (2, 2, 20, 20)
    crop_dlg.close()


def test_draw_tool_encompasses_shapes_and_pencil():
    app = QApplication.instance() or QApplication([])
    sel_tool = SelectionTool()
    assert sel_tool.mode == SelectionTool.BOX

    mw = MainWindow()
    order = mw.tool_panel._tool_order
    assert "draw" in order
    assert order == ["move", "selection", "draw", "eraser", "picker", "fill", "crop"]

    # Test sub-mode selection via select_tool_by_key
    mw.tool_panel.select_tool_by_key("pencil")
    assert mw.tool_panel.draw_tool.mode == "pencil"

    mw.tool_panel.select_tool_by_key("line")
    assert mw.tool_panel.draw_tool.mode == "line"

    mw.tool_panel.select_tool_by_key("rectangle")
    assert mw.tool_panel.draw_tool.mode == "rectangle"

    mw.tool_panel.select_tool_by_key("circle")
    assert mw.tool_panel.draw_tool.mode == "circle"

    mw.close()


def test_selection_undo_redo():
    app = QApplication.instance() or QApplication([])
    mw = MainWindow()

    assert mw.canvas.selection.is_empty()

    # Step 1: Create a selection
    mw.canvas.selection.replace([(2, 2), (2, 3), (3, 2), (3, 3)])
    mw.on_selection_committed()
    assert len(mw.canvas.selection.selected) == 4

    # Step 2: Undo selection -> should revert to empty
    mw.on_undo()
    assert mw.canvas.selection.is_empty()

    # Step 3: Redo selection -> should restore 4 points
    mw.on_redo()
    assert len(mw.canvas.selection.selected) == 4

    # Step 4: Deselect (clear selection)
    mw.on_deselect()
    assert mw.canvas.selection.is_empty()

    # Step 5: Undo deselect -> should restore selection
    mw.on_undo()
    assert len(mw.canvas.selection.selected) == 4

    mw.close()


def test_move_tool_interactive():
    app = QApplication.instance() or QApplication([])
    mw = MainWindow()

    # Draw pixel at (5, 5)
    mw.doc.active_layer.set_pixel(5, 5, "#FF0000FF")
    mw.on_stroke_committed()
    assert mw.doc.active_layer.get_pixel(5, 5) == "#FF0000FF"

    # Select Move Tool
    mw.tool_panel.select_tool_by_key("move")
    assert mw.canvas.active_tool.name == "move"

    # Drag pixel from (5, 5) to (7, 8)
    move_tool = mw.canvas.active_tool
    move_tool.mouse_press(mw.doc, 5, 5, "#000", "#000", selection=mw.canvas.selection)
    move_tool.mouse_move(mw.doc, 7, 8, "#000", "#000", selection=mw.canvas.selection)
    move_tool.mouse_release(mw.doc, 7, 8, "#000", "#000", selection=mw.canvas.selection)

    assert mw.doc.active_layer.get_pixel(5, 5) is None
    assert mw.doc.active_layer.get_pixel(7, 8) == "#FF0000FF"

    # Test nudge
    mw.on_move_nudge_requested(-1, -1)
    assert mw.doc.active_layer.get_pixel(7, 8) is None
    assert mw.doc.active_layer.get_pixel(6, 7) == "#FF0000FF"

    mw.close()


def test_import_image_dialog_and_canvas_resize(tmp_path):
    app = QApplication.instance() or QApplication([])
    doc = PixelDocument(16, 16)
    assert doc.width == 16 and doc.height == 16

    # Create a 64x48 test image file
    img_path = str(tmp_path / "test_img.png")
    test_img = QImage(64, 48, QImage.Format_ARGB32)
    test_img.fill(QColor(0, 255, 0, 255))
    test_img.save(img_path)

    # Test dialog instantiation and default checkbox state for different size image
    dlg = ImportImageDialog(img_path, img_width=64, img_height=48, canvas_width=16, canvas_height=16)
    name, resize_canvas, scale_to_canvas = dlg.get_values()
    assert name == "test_img"
    assert resize_canvas is False
    assert scale_to_canvas is False
    dlg.close()

    # Test doc.import_image_as_layer with resize_canvas=True
    layer = doc.import_image_as_layer(img_path, name="ResizedLayer", resize_canvas=True)
    assert layer is not None
    assert doc.width == 64
    assert doc.height == 48
    assert layer.get_pixel(0, 0) == "#00FF00FF"


def test_large_resolution_rendering_performance():
    import time
    app = QApplication.instance() or QApplication([])

    # Create a 512x512 document with 50,000 filled pixels
    doc = PixelDocument(512, 512)
    layer = doc.active_layer
    for x in range(0, 512, 2):
        for y in range(0, 200):
            layer.set_pixel(x, y, "#FF5500FF")

    t0 = time.perf_counter()
    img = doc.render_composite_qimage()
    elapsed = time.perf_counter() - t0

    assert img.width() == 512 and img.height() == 512
    # Composite rendering for 50,000 pixels should take less than 100ms
    assert elapsed < 0.1


def test_layer_content_bbox_and_toggle():
    app = QApplication.instance() or QApplication([])
    mw = MainWindow()
    layer = mw.doc.active_layer
    assert layer.get_content_bbox(mw.doc.width, mw.doc.height) is None

    layer.set_pixel(10, 10, "#FF0000FF")
    layer.set_pixel(20, 25, "#00FF00FF")

    bbox = layer.get_content_bbox(mw.doc.width, mw.doc.height)
    assert bbox == (10, 10, 11, 16)

    assert mw.canvas.show_layer_bounds is True
    mw.canvas.toggle_layer_bounds()
    assert mw.canvas.show_layer_bounds is False
    mw.canvas.toggle_layer_bounds()
    assert mw.canvas.show_layer_bounds is True

    mw.close()


def test_canvas_startup_centering():
    app = QApplication.instance() or QApplication([])
    mw = MainWindow()
    mw.resize(1000, 800)
    mw.show()
    app.processEvents()

    canvas = mw.canvas
    canvas_px_w = canvas.doc.width * canvas.zoom_level
    canvas_px_h = canvas.doc.height * canvas.zoom_level
    expected_dx = (canvas.width() - canvas_px_w) / 2.0
    expected_dy = (canvas.height() - canvas_px_h) / 2.0

    assert abs(canvas.pan_offset.x() - expected_dx) < 1.0
    assert abs(canvas.pan_offset.y() - expected_dy) < 1.0

    mw.close()



def test_import_large_image_without_resizing_preserves_offcanvas_pixels(tmp_path):
    app = QApplication.instance() or QApplication([])
    doc = PixelDocument(16, 16)

    # Create a 64x64 test image with a pixel at (50, 50)
    img_path = str(tmp_path / "large.png")
    img = QImage(64, 64, QImage.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))
    img.setPixelColor(50, 50, QColor(255, 0, 0, 255))
    img.save(img_path)

    # Import without resizing canvas
    layer = doc.import_image_as_layer(img_path, resize_canvas=False)
    assert layer is not None
    assert doc.width == 16 and doc.height == 16

    # Verify off-canvas pixel at (50, 50) is preserved in layer.pixels!
    assert layer.get_pixel(50, 50) == "#FF0000FF"
    assert layer.get_content_bbox() == (50, 50, 1, 1)

    # Verify cropping canvas to (0, 0, 16, 16) prunes pixels outside crop box
    doc.crop_canvas(0, 0, 16, 16)
    assert layer.get_pixel(50, 50) is None
    assert len(layer.pixels) == 0


def test_crop_layer_to_canvas():
    doc = PixelDocument(16, 16)
    layer = doc.active_layer
    layer.set_pixel(5, 5, "#FF0000FF")      # Inside canvas
    layer.set_pixel(-2, 5, "#00FF00FF")     # Outside left
    layer.set_pixel(20, 10, "#0000FFFF")    # Outside right

    assert len(layer.pixels) == 3
    removed = doc.crop_active_layer_to_canvas()
    assert removed == 2
    assert len(layer.pixels) == 1
    assert layer.get_pixel(5, 5) == "#FF0000FF"


def test_canvas_view_options_toggles():
    app = QApplication.instance() or QApplication([])
    mw = MainWindow()
    canvas = mw.canvas

    assert canvas.show_grid is True
    assert canvas.show_canvas_border is True
    assert canvas.show_layer_bounds is True

    mw._on_toggle_grid_clicked()
    assert canvas.show_grid is False
    assert mw.view_btn_grid.isChecked() is False

    mw._on_toggle_border_clicked()
    assert canvas.show_canvas_border is False
    assert mw.view_btn_border.isChecked() is False

    mw._on_toggle_bounds_clicked()
    assert canvas.show_layer_bounds is False
    assert mw.view_btn_bounds.isChecked() is False

    mw.close()


def test_delete_layer_hotkey():
    app = QApplication.instance() or QApplication([])
    mw = MainWindow()
    mw.layer_panel.on_add_layer()
    assert len(mw.doc.layers) == 2

    # Find the Delete Layer menu action
    del_act = None
    for action in mw.findChildren(QAction):
        if action.text() == "&Delete Layer":
            del_act = action
            break

    assert del_act is not None
    assert del_act.shortcut().toString() in ("Delete", "Del")

    # Trigger action shortcut callback
    del_act.trigger()
    assert len(mw.doc.layers) == 1
    mw.close()









