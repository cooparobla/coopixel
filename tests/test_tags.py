"""
Unit tests for layer tagging and Tag Manager functionality in Coopixel.
"""

from PySide6.QtWidgets import QApplication
from coopixel.models.document import PixelDocument, Layer
from coopixel.ui.main_window import MainWindow
from coopixel.ui.tag_panel import TagPanel


def test_layer_tag_model_and_serialization():
    doc = PixelDocument(16, 16)
    l1 = doc.active_layer
    l1.tag = "character"
    assert l1.tag == "character"

    # Test serialization
    data = doc.to_dict()
    doc2 = PixelDocument.from_dict(data)
    assert doc2.active_layer.tag == "character"

    # Test clone
    l1_clone = l1.clone()
    assert l1_clone.tag == "character"


def test_tag_query_and_global_visibility():
    doc = PixelDocument(16, 16)
    f1_l1 = doc.active_layer
    f1_l1.name = "Hero"
    f1_l1.tag = "character"

    f1_l2 = doc.add_layer("Shadow")
    f1_l2.tag = "shadow"

    # Add second frame
    f2 = doc.add_frame("Frame 2")
    f2_l1 = doc.active_layer
    f2_l1.name = "Hero F2"
    f2_l1.tag = "character"

    # Verify get_all_tags
    tags = doc.get_all_tags()
    assert tags == ["character", "shadow"]

    # Verify get_layers_by_tag
    char_layers = doc.get_layers_by_tag("character")
    assert len(char_layers) == 2
    assert all(l.visible for l in char_layers)

    # Disable all 'character' layers globally across all frames
    doc.set_tag_visibility("character", False)
    assert not f1_l1.visible
    assert not f2_l1.visible
    assert f1_l2.visible  # shadow layer remains visible
    assert not doc.is_tag_visible("character")

    # Re-enable 'character' layers
    doc.set_tag_visibility("character", True)
    assert f1_l1.visible
    assert f2_l1.visible
    assert doc.is_tag_visible("character")


def test_tag_panel_ui_integration():
    app = QApplication.instance() or QApplication([])
    mw = MainWindow()

    mw.doc.active_layer.tag = "background"
    mw.tag_panel.refresh_tags()

    assert "background" in mw.doc.get_all_tags()
    assert mw.tag_panel.container_layout.count() == 1

    # Toggle eye in tag panel
    mw.canvas._render_cache = "mock_cache"
    mw.doc.set_tag_visibility("background", False)
    mw.on_tag_visibility_changed()

    assert mw.canvas._render_cache is None
    assert not mw.doc.active_layer.visible
    mw.close()
