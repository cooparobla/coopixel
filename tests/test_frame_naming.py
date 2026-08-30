"""
Unit tests for Frame Naming and Serialization in Coopixel.
"""

from PySide6.QtWidgets import QApplication
from coopixel.models.document import PixelDocument, AnimationFrame
from coopixel.ui.animation_panel import AnimationPanel


def test_frame_name_model_and_serialization():
    doc = PixelDocument(16, 16)
    assert doc.active_frame.name == "Frame 1"

    # Rename frame
    doc.rename_frame(0, "stone_wall_tile")
    assert doc.active_frame.name == "stone_wall_tile"

    # Add second frame with custom tile name
    f2 = doc.add_frame("grass_top_tile")
    assert f2.name == "grass_top_tile"
    assert doc.active_frame.name == "grass_top_tile"

    # Test serialization roundtrip
    data = doc.to_dict()
    doc2 = PixelDocument.from_dict(data)

    assert len(doc2.frames) == 2
    assert doc2.frames[0].name == "stone_wall_tile"
    assert doc2.frames[1].name == "grass_top_tile"


def test_frame_card_renaming_in_animation_panel():
    app = QApplication.instance() or QApplication([])
    doc = PixelDocument(16, 16)
    panel = AnimationPanel(doc)

    doc.rename_frame(0, "lava_tile")
    panel.refresh_timeline()

    assert panel.strip_layout.count() == 1
    card = panel.strip_layout.itemAt(0).widget()
    assert card is not None
    assert "lava_tile" in card.title_label.text()

    # Rename via panel slot
    doc.rename_frame(0, "water_tile")
    panel.refresh_timeline()
    card2 = panel.strip_layout.itemAt(0).widget()
    assert "water_tile" in card2.title_label.text()
