"""
Unit tests for Coopixel animation frames, animation panel UI, minimum frame enforcement, and backward compatibility.
"""

import os
import tempfile
import pytest
from PySide6.QtWidgets import QApplication
from coopixel.models.document import AnimationFrame, PixelDocument
from coopixel.ui.main_window import MainWindow


def test_default_document_has_at_least_one_frame():
    doc = PixelDocument(16, 16)
    # Must have at least 1 frame by default
    assert len(doc.frames) == 1
    assert doc.active_frame_index == 0
    assert doc.active_frame.name == "Frame 1"

    # Cannot delete the only frame
    deleted = doc.delete_frame(0)
    assert deleted is False
    assert len(doc.frames) == 1
    assert doc.active_frame is not None


def test_frame_crud_and_reordering():
    doc = PixelDocument(16, 16)
    # Add frame
    f2 = doc.add_frame("Frame 2")
    assert len(doc.frames) == 2
    assert doc.active_frame_index == 1
    assert doc.active_frame == f2

    # Draw on frame 1 layer
    doc.select_frame(0)
    doc.active_layer.set_pixel(0, 0, "#FF0000FF")

    # Draw on frame 2 layer
    doc.select_frame(1)
    doc.active_layer.set_pixel(1, 1, "#00FF00FF")

    assert doc.frames[0].layers[0].get_pixel(0, 0) == "#FF0000FF"
    assert doc.frames[1].layers[0].get_pixel(1, 1) == "#00FF00FF"

    # Duplicate frame
    dup = doc.duplicate_frame(0)
    assert len(doc.frames) == 3
    assert dup.layers[0].get_pixel(0, 0) == "#FF0000FF"

    # Reorder frame
    doc.select_frame(1)
    doc.move_frame_right(1)
    assert doc.frames[2] == dup

    # Delete frame
    assert doc.delete_frame(0) is True
    assert len(doc.frames) == 2

    # Attempt to delete remaining frames down to 1
    assert doc.delete_frame(0) is True
    assert len(doc.frames) == 1

    # Final delete attempt must fail
    assert doc.delete_frame(0) is False
    assert len(doc.frames) == 1


def test_serialization_and_legacy_compatibility():
    doc = PixelDocument(8, 8)
    doc.active_layer.set_pixel(2, 2, "#FF0000FF")
    doc.add_frame("Frame 2")
    doc.active_layer.set_pixel(3, 3, "#0000FFFF")

    with tempfile.NamedTemporaryFile(suffix=".pix", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        doc.save_to_pix(tmp_path)
        assert os.path.exists(tmp_path)

        loaded = PixelDocument.load_from_pix(tmp_path)
        assert len(loaded.frames) == 2
        assert loaded.frames[0].layers[0].get_pixel(2, 2) == "#FF0000FF"
        assert loaded.frames[1].layers[0].get_pixel(3, 3) == "#0000FFFF"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # Legacy format without "frames" key
    legacy_data = {
        "format": "coopixel",
        "width": 16,
        "height": 16,
        "layers": [{"name": "Legacy Layer", "pixels": {"0,0": "#00FF00FF"}}]
    }
    legacy_doc = PixelDocument.from_dict(legacy_data)
    assert len(legacy_doc.frames) == 1
    assert legacy_doc.frames[0].layers[0].name == "Legacy Layer"
    assert legacy_doc.frames[0].layers[0].get_pixel(0, 0) == "#00FF00FF"


def test_multiple_distinct_animations():
    doc = PixelDocument(16, 16)
    # Default animation name must be "new-animation"
    assert len(doc.animations) == 1
    assert doc.active_animation.name == "new-animation"

    # Add second animation
    anim2 = doc.add_animation("walk-cycle")
    assert len(doc.animations) == 2
    assert doc.active_animation_index == 1
    assert doc.active_animation.name == "walk-cycle"

    # Draw on walk-cycle animation
    doc.active_layer.set_pixel(5, 5, "#FF0000FF")
    assert doc.active_layer.get_pixel(5, 5) == "#FF0000FF"

    # Switch back to new-animation
    doc.select_animation(0)
    assert doc.active_animation.name == "new-animation"
    assert doc.active_layer.get_pixel(5, 5) is None

    # Rename animation
    doc.rename_animation(0, "idle-anim")
    assert doc.animations[0].name == "idle-anim"

    # Delete animation
    doc.select_animation(1)
    deleted = doc.delete_animation(1)
    assert deleted is True
    assert len(doc.animations) == 1

    # Cannot delete the last remaining animation
    assert doc.delete_animation(0) is False
    assert len(doc.animations) == 1


def test_main_window_right_toolbar_and_animation_panel():
    app = QApplication.instance() or QApplication([])
    mw = MainWindow()
    assert mw.animation_panel is not None
    assert mw.animation_panel.isHidden()

    # Toolbar action toggle
    actions = mw.findChildren(QApplication, "")
    # Check animation panel toggle action
    toggle_act = mw.animation_panel.toggleViewAction()
    assert toggle_act is not None

    mw.animation_panel.setVisible(True)
    assert not mw.animation_panel.isHidden()

    # Check default animation in panel dropdown
    assert mw.animation_panel.anim_combo.count() == 1
    assert mw.animation_panel.anim_combo.currentText() == "new-animation"

    # Animation panel frame controls
    assert len(mw.doc.frames) == 1
    mw.animation_panel.on_add_frame()
    assert len(mw.doc.frames) == 2

    # Delete down to 1 frame
    mw.animation_panel.on_delete_frame()
    assert len(mw.doc.frames) == 1

    # Deleting at 1 frame must fail / keep 1 frame
    mw.animation_panel.on_delete_frame()
    assert len(mw.doc.frames) == 1

    mw.close()

