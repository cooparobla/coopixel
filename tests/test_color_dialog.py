"""
Unit tests for ColorWheelWidget and ColorPickerDialog in Coopixel.
"""

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication
from coopixel.ui.color_dialog import ColorPickerDialog, ColorWheelWidget, _qcolor_from_hex, _hex_from_qcolor
from coopixel.ui.color_panel import ColorPanel


def test_color_wheel_widget_color_setting():
    app = QApplication.instance() or QApplication([])
    red = _qcolor_from_hex("#FF0000FF")
    wheel = ColorWheelWidget(red)

    assert wheel.get_color().red() == 255
    assert wheel.get_color().green() == 0
    assert wheel.get_color().blue() == 0
    assert wheel.get_color().alpha() == 255

    # Change to semitransparent green
    green_semi = _qcolor_from_hex("#00FF0080")
    wheel.set_color(green_semi)

    col = wheel.get_color()
    assert col.green() == 255
    assert col.alpha() == 128
    wheel.close()


def test_color_wheel_widget_mouse_interaction():
    app = QApplication.instance() or QApplication([])
    wheel = ColorWheelWidget(_qcolor_from_hex("#000000FF"))

    signal_received = []
    wheel.color_changed.connect(lambda c: signal_received.append(c))

    # Click center of wheel (Saturation = 0 -> white/gray)
    center = QPointF(wheel.width() / 2.0, wheel.height() / 2.0)
    wheel._update_from_mouse(center)

    assert len(signal_received) > 0
    latest = signal_received[-1]
    assert latest.saturationF() < 0.05
    wheel.close()


def test_color_picker_dialog_tabs_and_controls():
    app = QApplication.instance() or QApplication([])
    swatches = ["#000000FF", "#FF0000FF", "#00FF0080", "#0000FFFF"]
    dialog = ColorPickerDialog(initial_color="#FF0000FF", swatches=swatches)

    assert dialog.tab_widget.count() == 2
    assert "Palette" in dialog.tab_widget.tabText(0)
    assert "Wheel" in dialog.tab_widget.tabText(1)

    # Initial color check
    assert dialog.get_selected_color_hex() == "#FF0000FF"

    # Test RGB / Alpha spinbox modification in Wheel tab
    dialog.r_spin.setValue(100)
    dialog.g_spin.setValue(150)
    dialog.b_spin.setValue(200)
    dialog.a_spin.setValue(128)

    assert dialog.get_selected_color_hex() == "#6496C880"

    # Test Hex Edit Field
    dialog.hex_edit.setText("#00FF00FF")
    dialog._on_hex_edited("#00FF00FF")
    assert dialog.get_selected_color_hex() == "#00FF00FF"

    dialog.close()


def test_color_picker_dialog_palette_swatch_selection():
    app = QApplication.instance() or QApplication([])
    swatches = ["#112233FF", "#44556677"]
    dialog = ColorPickerDialog(initial_color="#FFFFFFFF", swatches=swatches)

    # Select second swatch in palette
    target = _qcolor_from_hex("#44556677")
    dialog._on_palette_swatch_clicked(target)

    assert dialog.get_selected_color_hex() == "#44556677"
    dialog.close()


def test_color_panel_custom_picker_integration():
    app = QApplication.instance() or QApplication([])
    cp = ColorPanel()
    assert cp.primary_color == cp.current_swatches[0]
    cp.close()
