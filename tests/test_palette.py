"""
Unit tests for Palette PNG loading in Coopixel (including Lospec palettes).
"""

import os
import tempfile
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication
from coopixel.ui.color_panel import ColorPanel, extract_palette_from_image


def test_extract_palette_from_image():
    # Create a 4x1 test palette image with 4 distinct colors
    test_img = QImage(4, 1, QImage.Format_ARGB32)
    test_colors = ["#FF0000FF", "#00FF00FF", "#0000FFFF", "#FFFF00FF"]
    for idx, hex_c in enumerate(test_colors):
        qcol = QColor(hex_c[:7])
        test_img.setPixelColor(idx, 0, qcol)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        test_img.save(tmp_path, "PNG")
        extracted = extract_palette_from_image(tmp_path)
        assert len(extracted) == 4
        assert extracted[0] == "#FF0000FF"
        assert extracted[1] == "#00FF00FF"
        assert extracted[2] == "#0000FFFF"
        assert extracted[3] == "#FFFF00FF"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_color_panel_load_palette_png():
    app = QApplication.instance() or QApplication([])
    cp = ColorPanel()

    # Verify default palette loads from default-palette.png on initialization
    assert len(cp.current_swatches) == 64
    assert "default-palette" in cp.palette_header.text()

    sample_palette_path = "/home/coopa/downloads/endesga-64-1x.png"
    if os.path.exists(sample_palette_path):
        success = cp.load_palette_from_image(sample_palette_path)
        assert success is True
        assert len(cp.current_swatches) == 64
        assert cp.palette_header.text().startswith("Palette: endesga-64-1x (64)")

    # Reset back to default palette
    cp.reset_to_default_palette()
    assert len(cp.current_swatches) == 64
    assert "default-palette" in cp.palette_header.text()
    cp.close()
