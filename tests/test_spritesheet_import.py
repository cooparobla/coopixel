"""
Unit tests for Spritesheet Import model, .pixpref YAML configs, frame slicing, and dialog setup.
"""

import os
import tempfile
import pytest
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from coopixel.models.document import PixelDocument
from coopixel.models.spritesheet_config import (
    DEFAULT_CONFIG_DIR,
    SpritesheetAnimationConfig,
    add_spritesheet_layers_to_document,
    build_document_from_spritesheet,
    load_spritesheet_configs,
    save_spritesheet_configs,
    slice_image_to_sparse_pixels,
)
from coopixel.ui.spritesheet_import_dialog import (
    AnimationManagerWidget,
    AnimationOptionsWidget,
    SpritesheetImportDialog,
    SpritesheetViewer,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_spritesheet_animation_config_properties():
    cfg = SpritesheetAnimationConfig(name="run", start_x=10, start_y=20, num_frames=4, fps=12)
    assert cfg.start_x == 10
    assert cfg.start_y == 20
    assert cfg.name == "run"
    assert cfg.num_frames == 4

    d = cfg.to_dict()
    assert d["name"] == "run"
    assert d["start_x"] == 10
    assert d["num_frames"] == 4

    restored = SpritesheetAnimationConfig.from_dict(d)
    assert restored.name == "run"
    assert restored.start_x == 10
    assert restored.fps == 12


def test_save_and_load_pixpref_yaml(tmp_path):
    config_file = str(tmp_path / "test_spritesheet.pixpref")
    configs = [
        SpritesheetAnimationConfig(name="idle", start_x=0, start_y=0, num_frames=2, fps=10),
        SpritesheetAnimationConfig(name="walk", start_x=0, start_y=32, num_frames=4, fps=12),
    ]

    save_spritesheet_configs(config_file, configs, global_frame_width=32, global_frame_height=32)
    assert os.path.exists(config_file)

    with open(config_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "version: 1" in content
    assert "global_frame_width: 32" in content
    assert "idle" in content
    assert "walk" in content

    loaded, fw, fh = load_spritesheet_configs(config_file)
    assert fw == 32
    assert fh == 32
    assert len(loaded) == 2
    assert loaded[0].name == "idle"
    assert loaded[0].num_frames == 2
    assert loaded[1].name == "walk"
    assert loaded[1].num_frames == 4


def test_slice_image_to_sparse_pixels():
    img = QImage(64, 32, QImage.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))  # Transparent

    painter = QPainter(img)
    painter.fillRect(0, 0, 16, 16, QColor(255, 0, 0, 255))  # Red square
    painter.end()

    sparse = slice_image_to_sparse_pixels(img, 0, 0, 32, 32)
    assert len(sparse) == 256  # 16x16 red pixels
    assert sparse["0,0"] == "#FF0000FF"
    assert sparse["15,15"] == "#FF0000FF"
    assert "16,16" not in sparse


def test_build_document_from_spritesheet():
    img = QImage(128, 64, QImage.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))

    painter = QPainter(img)
    painter.fillRect(0, 0, 32, 32, QColor(0, 255, 0, 255))  # Green on frame 1
    painter.fillRect(32, 0, 32, 32, QColor(0, 0, 255, 255))  # Blue on frame 2
    painter.end()

    configs = [
        SpritesheetAnimationConfig(name="idle", start_x=0, start_y=0, num_frames=2, fps=10),
    ]

    doc = build_document_from_spritesheet(img, configs, global_frame_width=32, global_frame_height=32, layer_name="BaseLayer")
    assert doc.width == 32
    assert doc.height == 32
    assert len(doc.animations) == 1
    anim = doc.animations[0]
    assert anim.name == "idle"
    assert len(anim.frames) == 2

    frame1 = anim.frames[0]
    assert len(frame1.layers) == 1
    assert frame1.layers[0].name == "BaseLayer"
    assert frame1.layers[0].get_pixel(0, 0) == "#00FF00FF"

    frame2 = anim.frames[1]
    assert frame2.layers[0].get_pixel(0, 0) == "#0000FFFF"


def test_add_spritesheet_layers_to_document_matching_names():
    doc = PixelDocument(32, 32)
    doc.animations[0].name = "idle"

    img = QImage(64, 32, QImage.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))

    painter = QPainter(img)
    painter.fillRect(0, 0, 16, 16, QColor(255, 255, 0, 255))  # Yellow
    painter.end()

    configs = [
        SpritesheetAnimationConfig(name="idle", start_x=0, start_y=0, num_frames=2, fps=10),
    ]

    add_spritesheet_layers_to_document(doc, img, configs, global_frame_width=32, global_frame_height=32, layer_name="ArmorLayer")

    anim = doc.animations[0]
    assert len(anim.frames) == 2
    frame1 = anim.frames[0]
    # Check ArmorLayer added to frame 1
    assert len(frame1.layers) >= 2
    assert frame1.layers[-1].name == "ArmorLayer"
    assert frame1.layers[-1].get_pixel(0, 0) == "#FFFF00FF"


def test_spritesheet_import_dialog_ui(qapp):
    img = QImage(128, 64, QImage.Format_ARGB32)
    img.fill(QColor(255, 255, 255, 255))

    dlg = SpritesheetImportDialog(filepath="test_sheet.png", image=img)
    assert dlg.windowTitle().startswith("Import Spritesheet")
    assert dlg.manager_widget is not None
    assert dlg.viewer_widget is not None
    assert dlg.options_widget is not None

    # Test adding an animation
    dlg.manager_widget.on_add_anim()
    assert len(dlg.manager_widget.configs) == 2

    # Test selection update
    dlg.manager_widget.list_widget.setCurrentRow(1)
    cfg = dlg.manager_widget.get_selected_config()
    assert cfg is not None
    assert cfg.name.startswith("anim_")


def test_spritesheet_viewer_key_a_centering(qapp):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtGui import QKeyEvent

    img = QImage(128, 64, QImage.Format_ARGB32)
    img.fill(QColor(255, 255, 255, 255))

    viewer = SpritesheetViewer()
    viewer.resize(600, 400)
    viewer.set_image(img)

    viewer._pan_offset = viewer._pan_offset + QPoint(100, 100)
    old_pan = viewer._pan_offset

    event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_A, Qt.NoModifier)
    viewer.keyPressEvent(event)

    assert viewer._pan_offset != old_pan


def test_spritesheet_viewer_grid_and_snapping(qapp):
    from PySide6.QtCore import QPoint

    img = QImage(128, 64, QImage.Format_ARGB32)
    img.fill(QColor(255, 255, 255, 255))

    viewer = SpritesheetViewer()
    viewer.resize(600, 400)
    viewer.set_image(img)

    # Test Grid Toggling
    assert viewer._show_grid is True
    viewer.toggle_grid()
    assert viewer._show_grid is False
    viewer.set_show_grid(True)
    assert viewer._show_grid is True

    # Test Pixel Grid Snapping
    viewer._zoom = 2.0
    viewer._pan_offset = QPoint(0, 0)
    pt = viewer._widget_to_image_coords(QPoint(15, 25), snap_grid=True)
    assert isinstance(pt.x(), int)
    assert isinstance(pt.y(), int)


def test_delete_background_layer_on_import():
    img = QImage(64, 32, QImage.Format_ARGB32)
    img.fill(QColor(255, 0, 0, 255))

    configs = [
        SpritesheetAnimationConfig(name="run", layer_name="Body", start_x=0, start_y=0, num_frames=2),
    ]

    doc = build_document_from_spritesheet(img, configs, global_frame_width=32, global_frame_height=32)
    anim = doc.animations[0]
    frame1 = anim.frames[0]

    # Verify 'Background' layer is completely removed and only 'Body' exists
    layer_names = [l.name for l in frame1.layers]
    assert "Background" not in layer_names
    assert "Body" in layer_names
    assert len(frame1.layers) == 1


def test_spritesheet_viewer_cell_based_selection(qapp):
    from PySide6.QtCore import QPoint

    img = QImage(128, 64, QImage.Format_ARGB32)
    img.fill(QColor(255, 255, 255, 255))

    viewer = SpritesheetViewer()
    viewer.resize(600, 400)
    viewer.set_image(img)
    viewer.set_configs([SpritesheetAnimationConfig(name="idle", start_x=0, start_y=0, num_frames=1)], 0, global_fw=32, global_fh=32)

    viewer._zoom = 1.0
    viewer._pan_offset = QPoint(0, 0)

    # Click on second cell (x=35, y=5) -> cell (1, 0) -> start_x=32, start_y=0
    col, row = viewer._widget_to_cell_coords(QPoint(35, 5))
    assert col == 1
    assert row == 0


def test_non_contiguous_frame_cells(tmp_path):
    img = QImage(128, 64, QImage.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))
    # Draw distinct pixel on cell 0 (0,0), cell 2 (64,0), cell 3 (0,32)
    img.setPixelColor(5, 5, QColor(255, 0, 0, 255))
    img.setPixelColor(69, 5, QColor(0, 255, 0, 255))
    img.setPixelColor(5, 37, QColor(0, 0, 255, 255))

    cfg = SpritesheetAnimationConfig(
        name="custom_attack",
        layer_name="Weapon",
        frame_cells=[(0, 0), (64, 0), (0, 32)],
        num_frames=3,
    )

    positions = cfg.get_frame_positions(32, 32, img_w=128)
    assert positions == [(0, 0), (64, 0), (0, 32)]

    doc = build_document_from_spritesheet(img, [cfg], global_frame_width=32, global_frame_height=32)
    anim = doc.animations[0]
    assert len(anim.frames) == 3

    # Frame 1 has red pixel from (0,0)
    assert len(anim.frames[0].layers[0].pixels) > 0
    assert "#FF0000FF" in anim.frames[0].layers[0].pixels.values()

    # Frame 2 has green pixel from (64,0)
    assert "#00FF00FF" in anim.frames[1].layers[0].pixels.values()

    # Frame 3 has blue pixel from (0,32)
    assert "#0000FFFF" in anim.frames[2].layers[0].pixels.values()

    # Save / Load test
    pref_file = str(tmp_path / "custom.pixpref")
    save_spritesheet_configs(pref_file, [cfg], global_frame_width=32, global_frame_height=32)

    loaded_cfgs, fw, fh = load_spritesheet_configs(pref_file)
    assert len(loaded_cfgs) == 1
    assert loaded_cfgs[0].frame_cells == [(0, 0), (64, 0), (0, 32)]


def test_add_anim_attribute_inheritance(qapp):
    img = QImage(128, 64, QImage.Format_ARGB32)
    dlg = SpritesheetImportDialog(filepath="hero.png", image=img)

    # Configure initial animation
    cfg0 = dlg.manager_widget.configs[0]
    cfg0.layer_name = "Player_Base"
    cfg0.pivot_x = 10
    cfg0.pivot_y = 20
    cfg0.fps = 15

    # Add new animation via manager
    dlg.manager_widget.on_add_anim()
    assert len(dlg.manager_widget.configs) == 2

    cfg1 = dlg.manager_widget.configs[1]
    assert cfg1.name == "anim_2"
    assert cfg1.layer_name == "Player_Base"
    assert cfg1.pivot_x == 10
    assert cfg1.pivot_y == 20
    assert cfg1.fps == 15


def test_multi_select_bulk_editing(qapp):
    img = QImage(128, 64, QImage.Format_ARGB32)
    dlg = SpritesheetImportDialog(filepath="hero.png", image=img)

    mgr = dlg.manager_widget
    mgr.on_add_anim()  # Add second anim
    mgr.on_add_anim()  # Add third anim
    assert len(mgr.configs) == 3

    # Multi-select items 0, 1, 2
    mgr.list_widget.selectAll()
    selected_indices = mgr.get_selected_indices()
    assert len(selected_indices) == 3

    # Verify options widget is in multi-selection mode
    opts = dlg.options_widget
    assert not opts.name_edit.isEnabled()
    assert not opts.start_x_spin.isEnabled()
    assert opts.layer_name_edit.isEnabled()
    assert opts.pivot_x_spin.isEnabled()
    assert opts.fps_spin.isEnabled()

    # Bulk edit fields
    opts.layer_name_edit.setText("Shared_Armor")
    opts.pivot_x_spin.setValue(14)
    opts.pivot_y_spin.setValue(28)
    opts.fps_spin.setValue(24)

    # Flush/sync
    opts.sync_current_options()

    # Verify all 3 configs updated bulk fields
    for cfg in mgr.configs:
        assert cfg.layer_name == "Shared_Armor"
        assert cfg.pivot_x == 14
        assert cfg.pivot_y == 28
        assert cfg.fps == 24


def test_spritesheet_import_confirmation_dialog(qapp, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    img = QImage(128, 64, QImage.Format_ARGB32)
    dlg = SpritesheetImportDialog(filepath="hero.png", image=img)

    # 1. Test clicking 'No' in confirmation dialog cancels import
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.No)
    dlg.on_accept_import()
    assert dlg.result_document is None

    # 2. Test clicking 'Yes' in confirmation dialog proceeds with import
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)
    dlg.on_accept_import()
    assert dlg.result_document is not None


def test_spritesheet_import_layer_tag(qapp, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    img = QImage(64, 32, QImage.Format_ARGB32)
    img.fill(QColor(255, 0, 0, 255))
    dlg = SpritesheetImportDialog(filepath="hero.png", image=img)

    # Set custom tag 'hero_body'
    dlg.options_widget.tag_edit.setText("hero_body")
    dlg.options_widget.sync_current_options()

    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)
    dlg.on_accept_import()

    doc = dlg.result_document
    assert doc is not None
    assert len(doc.animations) >= 1
    layer = doc.animations[0].frames[0].layers[0]
    assert layer.tag == "hero_body"
