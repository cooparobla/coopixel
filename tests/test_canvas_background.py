"""
Unit tests for Canvas Background color and pattern settings in Coopixel.
"""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication
from coopixel.models.document import PixelDocument
from coopixel.ui.canvas import CanvasWidget
from coopixel.ui.main_window import MainWindow


def test_canvas_background_settings_mode_and_color():
    from PySide6.QtCore import QSettings
    QSettings("coopixel", "coopixel").clear()
    app = QApplication.instance() or QApplication([])
    doc = PixelDocument(16, 16)
    canvas = CanvasWidget(doc)

    # Default mode is dark checker
    assert canvas.bg_mode == "checker_dark"

    # Set to light checker
    canvas.set_canvas_background("checker_light")
    assert canvas.bg_mode == "checker_light"

    # Set to solid custom color #FF00FF (Magenta)
    canvas.set_canvas_background("solid", "#FF00FF")
    assert canvas.bg_mode == "solid"
    assert canvas.bg_color == QColor("#FF00FF")

    # Set to solid green #00FF00
    canvas.set_canvas_background("solid", QColor("#00FF00"))
    assert canvas.bg_mode == "solid"
    assert canvas.bg_color == QColor("#00FF00")


def test_main_window_canvas_background_menu_integration():
    app = QApplication.instance() or QApplication([])
    mw = MainWindow()

    # Trigger dark checker menu action
    mw.canvas.set_canvas_background("checker_dark")
    assert mw.canvas.bg_mode == "checker_dark"

    # Trigger solid white menu action
    mw.canvas.set_canvas_background("solid", "#FFFFFF")
    assert mw.canvas.bg_mode == "solid"
    assert mw.canvas.bg_color == QColor("#FFFFFF")

    mw.close()
