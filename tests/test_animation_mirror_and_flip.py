"""
Unit tests for Animation Mirror (.R/.L) and Layer Horizontal/Vertical Flipping in Coopixel.
"""

from PySide6.QtWidgets import QApplication
from coopixel.models.document import PixelDocument, Animation
from coopixel.ui.animation_panel import AnimationPanel


def test_layer_flip_horizontal_and_vertical():
    doc = PixelDocument(32, 32)
    layer = doc.active_layer

    # Create pixels at (2, 5) and (10, 20)
    layer.set_pixel(2, 5, "#FF0000FF")
    layer.set_pixel(10, 20, "#00FF00FF")

    # Flip horizontal -> (2, 5) becomes (32-1-2=29, 5) and (10, 20) becomes (32-1-10=21, 20)
    doc.flip_active_layer_horizontal()

    assert layer.get_pixel(29, 5) == "#FF0000FF"
    assert layer.get_pixel(21, 20) == "#00FF00FF"
    assert layer.get_pixel(2, 5) is None
    assert layer.get_pixel(10, 20) is None

    # Flip vertical -> (29, 5) becomes (29, 32-1-5=26) and (21, 20) becomes (21, 32-1-20=11)
    doc.flip_active_layer_vertical()

    assert layer.get_pixel(29, 26) == "#FF0000FF"
    assert layer.get_pixel(21, 11) == "#00FF00FF"
    assert layer.get_pixel(29, 5) is None
    assert layer.get_pixel(21, 20) is None


def test_mirror_animation_suffix_and_flip():
    doc = PixelDocument(32, 32)

    # Setup animation ending in .R
    anim_r = doc.active_animation
    anim_r.name = "walk.R"

    f1 = anim_r.frames[0]
    l1 = f1.active_layer
    l1.set_pixel(4, 10, "#FFFF00FF")

    # Add second frame to walk.R
    f2 = anim_r.add_frame("Frame 2")
    l2 = f2.active_layer
    l2.set_pixel(8, 12, "#00FFFFFF")

    # Mirror animation
    mirrored = doc.mirror_animation()

    assert mirrored is not None
    assert mirrored.name == "walk.L"
    assert len(doc.animations) == 2
    assert doc.active_animation_index == 1

    # Verify all duplicated frames have ALL layers flipped horizontally across 32px canvas
    # Frame 1: (4, 10) -> (31 - 4 = 27, 10)
    mf1_l1 = mirrored.frames[0].layers[0]
    assert mf1_l1.get_pixel(27, 10) == "#FFFF00FF"
    assert mf1_l1.get_pixel(4, 10) is None

    # Frame 2: (8, 12) -> (31 - 8 = 23, 12)
    mf2_l2 = mirrored.frames[1].layers[0]
    assert mf2_l2.get_pixel(23, 12) == "#00FFFFFF"
    assert mf2_l2.get_pixel(8, 12) is None


def test_mirror_animation_left_to_right():
    doc = PixelDocument(32, 32)

    anim_l = doc.active_animation
    anim_l.name = "attack_slash.L"
    anim_l.frames[0].active_layer.set_pixel(1, 1, "#FF00FFFF")

    mirrored = doc.mirror_animation()

    assert mirrored is not None
    assert mirrored.name == "attack_slash.R"
    assert mirrored.frames[0].active_layer.get_pixel(30, 1) == "#FF00FFFF"


def test_animation_panel_mirror_button_enabled():
    app = QApplication.instance() or QApplication([])
    doc = PixelDocument(32, 32)
    panel = AnimationPanel(doc)

    # Single animation without .L or .R -> mirror button disabled
    doc.active_animation.name = "idle"
    panel.refresh_timeline()
    assert panel.mirror_anim_btn.isEnabled() is False

    # Rename to end in .R -> mirror button enabled
    doc.active_animation.name = "run.R"
    panel.refresh_timeline()
    assert panel.mirror_anim_btn.isEnabled() is True

    # Trigger mirror button click
    panel.mirror_anim_btn.click()

    assert len(doc.animations) == 2
    assert doc.active_animation.name == "run.L"
