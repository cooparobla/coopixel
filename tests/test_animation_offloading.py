"""
Unit tests for Animation lazy loading, session disk offloading, and runtime performance in Coopixel.
"""

import os
import tempfile
import pytest
from coopixel.models.document import Animation, AnimationFrame, Layer, PixelDocument
from coopixel.ui.animation_panel import AnimationPanel


def test_inactive_animations_are_offloaded_to_disk():
    """Verify that when a document with multiple animations is loaded, inactive animations are offloaded to disk."""
    doc = PixelDocument(16, 16)
    a1 = doc.active_animation
    a1.name = "anim_one"
    a1.frames[0].layers[0].set_pixel(0, 0, "#FF0000FF")

    a2 = doc.add_animation("anim_two")
    a2.frames[0].layers[0].set_pixel(1, 1, "#00FF00FF")

    a3 = doc.add_animation("anim_three")
    a3.frames[0].layers[0].set_pixel(2, 2, "#0000FFFF")

    # doc.active_animation is a3 (index 2)
    assert doc.active_animation_index == 2
    assert a3.is_loaded is True
    assert len(a3.frames) == 1
    assert a1.is_loaded is False
    assert len(a1.frames) == 0
    assert a1._cache_file is not None
    assert os.path.exists(a1._cache_file)
    assert a2.is_loaded is False
    assert len(a2.frames) == 0
    assert a2._cache_file is not None
    assert os.path.exists(a2._cache_file)


def test_switching_animations_swaps_memory_and_disk():
    """Verify selecting a different animation offloads the current one and hydrates the selected one."""
    doc = PixelDocument(16, 16)
    doc.animations[0].name = "anim_0"
    doc.animations[0].frames[0].layers[0].set_pixel(0, 0, "#FF0000FF")

    anim1 = doc.add_animation("anim_1")
    anim1.frames[0].layers[0].set_pixel(5, 5, "#00FF00FF")

    assert doc.active_animation_index == 1
    assert doc.animations[0].is_loaded is False
    assert doc.animations[1].is_loaded is True

    # Switch back to anim_0
    success = doc.select_animation(0)
    assert success is True
    assert doc.active_animation_index == 0
    assert doc.animations[0].is_loaded is True
    assert len(doc.animations[0].frames) == 1
    assert doc.animations[0].frames[0].layers[0].get_pixel(0, 0) == "#FF0000FF"
    assert doc.animations[1].is_loaded is False
    assert len(doc.animations[1].frames) == 0


def test_single_file_save_and_load_persistence(tmp_path):
    """Verify that saving to a single .pix file saves all animations (including offloaded ones),
    and loading back restores all animations with offloading active.
    """
    file_path = str(tmp_path / "multi_anim_test.pix")

    doc = PixelDocument(16, 16)
    doc.animations[0].name = "walk"
    doc.animations[0].frames[0].layers[0].set_pixel(1, 1, "#112233FF")
    f2 = doc.add_frame("walk_2")
    f2.layers[0].set_pixel(2, 2, "#445566FF")

    jump = doc.add_animation("jump")
    jump.frames[0].layers[0].set_pixel(3, 3, "#778899FF")

    attack = doc.add_animation("attack")
    attack.frames[0].layers[0].set_pixel(4, 4, "#AABBCCFF")

    # Select walk as active before saving
    doc.select_animation(0)
    assert doc.animations[1].is_loaded is False
    assert doc.animations[2].is_loaded is False

    # Save to single file
    doc.save_to_pix(file_path)
    assert os.path.exists(file_path)

    # Load from file
    loaded_doc = PixelDocument.load_from_pix(file_path)
    assert len(loaded_doc.animations) == 3
    assert loaded_doc.active_animation_index == 0
    assert loaded_doc.animations[0].is_loaded is True
    assert loaded_doc.animations[1].is_loaded is False
    assert loaded_doc.animations[2].is_loaded is False

    # Verify walk animation frames and pixels
    assert len(loaded_doc.animations[0].frames) == 2
    assert loaded_doc.animations[0].frames[0].layers[0].get_pixel(1, 1) == "#112233FF"
    assert loaded_doc.animations[0].frames[1].layers[0].get_pixel(2, 2) == "#445566FF"

    # Select jump animation and verify
    loaded_doc.select_animation(1)
    assert loaded_doc.animations[1].is_loaded is True
    assert loaded_doc.animations[0].is_loaded is False
    assert loaded_doc.animations[1].frames[0].layers[0].get_pixel(3, 3) == "#778899FF"

    # Select attack animation and verify
    loaded_doc.select_animation(2)
    assert loaded_doc.animations[2].is_loaded is True
    assert loaded_doc.animations[2].frames[0].layers[0].get_pixel(4, 4) == "#AABBCCFF"


def test_canvas_resize_across_loaded_and_offloaded():
    """Verify that canvas resizing affects both active and offloaded animations correctly."""
    doc = PixelDocument(16, 16)
    doc.animations[0].name = "anim_1"
    doc.animations[0].frames[0].layers[0].set_pixel(2, 2, "#FF0000FF")

    anim2 = doc.add_animation("anim_2")
    anim2.frames[0].layers[0].set_pixel(4, 4, "#00FF00FF")

    # Currently anim_2 is active, anim_1 is offloaded
    assert doc.animations[0].is_loaded is False
    assert doc.animations[1].is_loaded is True

    # Resize canvas with top-left anchor (+8 width, +8 height)
    doc.resize_canvas(24, 24, anchor="top-left")
    assert doc.width == 24
    assert doc.height == 24
    assert doc.active_animation.frames[0].layers[0].get_pixel(4, 4) == "#00FF00FF"

    # Switch to anim_1 and check its pixel position
    doc.select_animation(0)
    assert doc.active_animation.frames[0].layers[0].get_pixel(2, 2) == "#FF0000FF"


def test_tag_visibility_across_offloaded_animations():
    """Verify that tag visibility operations query and update offloaded animations."""
    doc = PixelDocument(16, 16)
    doc.animations[0].frames[0].layers[0].tag = "player"

    anim2 = doc.add_animation("anim_2")
    anim2.frames[0].layers[0].tag = "weapon"

    # anim_2 is active, anim_0 is offloaded
    tags = doc.get_all_tags()
    assert "player" in tags
    assert "weapon" in tags

    doc.set_tag_visibility("player", False)
    assert doc.is_tag_visible("player") is False

    doc.select_animation(0)
    assert doc.active_animation.frames[0].layers[0].visible is False


def test_temp_directory_cleanup():
    """Verify document cleanup removes all temporary session cache files."""
    doc = PixelDocument(16, 16)
    doc.add_animation("anim_2")
    doc.add_animation("anim_3")

    temp_dir = doc._temp_dir
    assert os.path.exists(temp_dir)

    doc.cleanup()
    assert not os.path.exists(temp_dir) or len(os.listdir(temp_dir)) == 0


def test_timeline_thumbnail_caching(qapp):
    """Verify that AnimationPanel caches thumbnails and updates in-place during playback."""
    doc = PixelDocument(16, 16)
    doc.active_animation.frames[0].layers[0].set_pixel(0, 0, "#FF0000FF")
    doc.add_frame("Frame 2")
    doc.active_animation.frames[1].layers[0].set_pixel(1, 1, "#00FF00FF")

    panel = AnimationPanel(doc)
    doc.select_frame(0)
    panel.refresh_timeline()
    assert len(panel._cards) == 2
    assert len(panel._thumb_cache) == 2

    # Step playback — should update in-place without rebuilding cards
    initial_cards = list(panel._cards)
    panel._on_play_step()
    assert panel._cards == initial_cards
    assert doc.active_frame_index == 1

    # Invalidate thumbnail for frame 0
    panel.invalidate_thumbnail(0)
    assert (doc.active_animation_index, 0) in panel._thumb_cache


def test_switching_animations_composite_cache_isolation():
    """Verify that composite frame caching isolates images by (animation_index, frame_index) without bleed."""
    doc = PixelDocument(16, 16)
    a0 = doc.active_animation
    a0.name = "stand"
    a0.frames[0].layers[0].set_pixel(0, 0, "#FF0000FF")

    a1 = doc.add_animation("walk")
    a1.frames[0].layers[0].set_pixel(0, 0, "#0000FFFF")

    # Render frame 0 of walk (animation 1)
    img_walk = doc.render_frame_qimage(0)
    assert img_walk.pixelColor(0, 0).red() == 0
    assert img_walk.pixelColor(0, 0).blue() == 255

    # Switch to stand (animation 0)
    doc.select_animation(0)
    img_stand = doc.render_frame_qimage(0)
    assert img_stand.pixelColor(0, 0).red() == 255
    assert img_stand.pixelColor(0, 0).blue() == 0

    # Switch back to walk (animation 1)
    doc.select_animation(1)
    img_walk_2 = doc.render_frame_qimage(0)
    assert img_walk_2.pixelColor(0, 0).red() == 0
    assert img_walk_2.pixelColor(0, 0).blue() == 255


def test_switching_animations_preserves_per_frame_tag_visibility():
    """Verify that offloading/hydrating does not overwrite individual per-frame layer visibility."""
    doc = PixelDocument(16, 16)
    a0 = doc.active_animation
    a0.name = "attack"
    # Frame 0: weapon layer visible
    f0_weapon = a0.frames[0].layers[0]
    f0_weapon.name = "Weapon"
    f0_weapon.tag = "weapon"
    f0_weapon.visible = True

    # Frame 1: weapon layer hidden (e.g. sheathed)
    f1 = a0.add_frame("Frame 2")
    f1_weapon = f1.layers[0]
    f1_weapon.name = "Weapon"
    f1_weapon.tag = "weapon"
    f1_weapon.visible = False

    # Add second animation (forces a0 to offload)
    a1 = doc.add_animation("idle")
    assert a0.is_loaded is False

    # Switch back to a0
    doc.select_animation(0)
    assert doc.active_animation.frames[0].layers[0].visible is True
    assert doc.active_animation.frames[1].layers[0].visible is False


def test_offloaded_animation_tag_visibility_toggle():
    """Verify that explicit global tag toggles apply accurately to offloaded animations upon hydration."""
    doc = PixelDocument(16, 16)
    a0 = doc.active_animation
    a0.name = "anim_0"
    l_body = a0.frames[0].layers[0]
    l_body.tag = "body"
    l_body.visible = True

    l_armor = a0.frames[0].add_layer("Armor")
    l_armor.tag = "armor"
    l_armor.visible = True

    # Add anim_1 (offloads anim_0)
    a1 = doc.add_animation("anim_1")
    assert a0.is_loaded is False

    # Toggle 'armor' visibility to False while anim_0 is offloaded
    doc.set_tag_visibility("armor", False)

    # Switch back to anim_0
    doc.select_animation(0)
    assert doc.active_animation.frames[0].layers[0].visible is True  # body stays visible
    assert doc.active_animation.frames[0].layers[1].visible is False  # armor is hidden

