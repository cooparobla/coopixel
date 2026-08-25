"""
Unit tests for Hue, Saturation, and Contrast layer effect in Coopixel.
"""

from PySide6.QtWidgets import QApplication
from coopixel.models.document import PixelDocument
from coopixel.models.effects import HueSaturationContrastEffect
from coopixel.ui.appearance_panel import AppearancePanel
from coopixel.ui.color_panel import ColorPanel


def test_hue_sat_contrast_effect_processing():
    pixels = {"0,0": "#FF0000FF"}
    eff = HueSaturationContrastEffect(enabled=True, hue=120, saturation=0, contrast=0)

    # Shift red hue by +120 deg -> Green
    processed = eff.process_pixels(pixels)
    assert "0,0" in processed
    green_hex = processed["0,0"]
    assert green_hex.startswith("#00FF00")

    # Disabled effect returns original
    eff.enabled = False
    assert eff.process_pixels(pixels) == pixels


def test_hue_sat_contrast_serialization():
    eff = HueSaturationContrastEffect(enabled=True, hue=45, saturation=-20, contrast=30)
    d = eff.to_dict()
    assert d["type"] == "hue_sat_contrast"
    assert d["hue"] == 45
    assert d["saturation"] == -20
    assert d["contrast"] == 30

    restored = HueSaturationContrastEffect.from_dict(d)
    assert restored.hue == 45
    assert restored.saturation == -20
    assert restored.contrast == 30


def test_appearance_panel_add_hsc_effect():
    app = QApplication.instance() or QApplication([])
    doc = PixelDocument(32, 32)
    panel = AppearancePanel(doc)

    assert len(doc.active_layer.effects) == 0
    panel.add_hue_sat_contrast_effect()

    assert len(doc.active_layer.effects) == 1
    assert isinstance(doc.active_layer.effects[0], HueSaturationContrastEffect)
    assert panel.effects_layout.count() >= 1

    # Reset values test
    widget = panel.effects_layout.itemAt(0).widget()
    widget.hue_spin.setValue(90)
    assert doc.active_layer.effects[0].hue == 90
    widget._reset_values()
    assert doc.active_layer.effects[0].hue == 0

    panel.close()


def test_color_panel_minimize_palette():
    app = QApplication.instance() or QApplication([])
    cp = ColorPanel()

    # Defaults to minimized
    assert cp._palette_expanded is False
    assert cp.toggle_pal_btn.text() == "▶"

    cp.toggle_palette_visibility()
    assert cp._palette_expanded is True
    assert cp.toggle_pal_btn.text() == "▼"

    cp.toggle_palette_visibility()
    assert cp._palette_expanded is False
    assert cp.toggle_pal_btn.text() == "▶"

    cp.close()
