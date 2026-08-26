"""
Tests for per-tool brush size persistence and Pen Tool size lock in Coopixel.
"""

import pytest
from PySide6.QtWidgets import QApplication

from coopixel.models.document import PixelDocument
from coopixel.ui.main_window import MainWindow
from coopixel.ui.tool_panel import ToolPanel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_per_tool_brush_size_persistence(qapp):
    win = MainWindow()

    # 1. Select pencil tool and set size to 4
    win.tool_panel.select_tool_by_key("pencil")
    win.tool_panel.size_spin.setValue(4)
    assert win.canvas.brush_size == 4
    assert win.tool_panel.tool_sizes["pencil"] == 4

    # 2. Select line tool and set size to 2
    win.tool_panel.select_tool_by_key("line")
    win.tool_panel.size_spin.setValue(2)
    assert win.canvas.brush_size == 2
    assert win.tool_panel.tool_sizes["line"] == 2

    # 3. Select Pen tool -> size indicator is always 1
    win.tool_panel.select_tool_by_key("pen")
    assert win.tool_panel.size_spin.value() == 1
    assert win.canvas.brush_size == 1

    # Attempt to change size on Pen tool -> stays 1
    win.tool_panel.size_spin.setValue(8)
    assert win.tool_panel.size_spin.value() == 1
    assert win.canvas.brush_size == 1

    # 4. Switch back to pencil tool -> restores 4
    win.tool_panel.select_tool_by_key("pencil")
    assert win.tool_panel.size_spin.value() == 4
    assert win.canvas.brush_size == 4

    # 5. Switch back to line tool -> restores 2
    win.tool_panel.select_tool_by_key("line")
    assert win.tool_panel.size_spin.value() == 2
    assert win.canvas.brush_size == 2

    # 6. Switch back to pen tool -> restores 1
    win.tool_panel.select_tool_by_key("pen")
    assert win.tool_panel.size_spin.value() == 1
    assert win.canvas.brush_size == 1
