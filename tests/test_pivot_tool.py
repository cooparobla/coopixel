"""
Unit tests for Animation Pivot Point model, default center calculation, serialization, PivotTool, and UI controls.
"""

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QApplication

from coopixel.models.document import Animation, PixelDocument
from coopixel.tools.pivot import PivotTool
from coopixel.ui.tool_panel import ToolPanel


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_animation_pivot_default_and_properties():
    # 64x64 document defaults pivot to (32, 32)
    doc = PixelDocument(64, 64)
    anim = doc.active_animation
    assert anim.pivot_x == 32
    assert anim.pivot_y == 32
    assert anim.pivot == (32, 32)

    anim.pivot = (5, 10)
    assert anim.pivot_x == 5
    assert anim.pivot_y == 10

    d = anim.to_dict()
    assert d["pivot_x"] == 5
    assert d["pivot_y"] == 10

    restored = Animation.from_dict(d)
    assert restored.pivot_x == 5
    assert restored.pivot_y == 10

    cloned = anim.clone()
    assert cloned.pivot_x == 5
    assert cloned.pivot_y == 10


def test_pivot_tool_interaction():
    doc = PixelDocument(64, 64)
    tool = PivotTool()

    # Move pivot to (12, 18)
    changed = tool.mouse_press(doc, 12, 18, "#FF0000FF", "#00000000")
    assert changed is True
    anim = doc.active_animation
    assert anim.pivot_x == 12
    assert anim.pivot_y == 18

    # Drag pivot to (20, 25)
    changed_move = tool.mouse_move(doc, 20, 25, "#FF0000FF", "#00000000")
    assert changed_move is True
    assert anim.pivot_x == 20
    assert anim.pivot_y == 25

    # Release
    tool.mouse_release(doc, 20, 25, "#FF0000FF", "#00000000")
    assert tool.is_dragging is False


def test_tool_panel_pivot_options(qapp):
    panel = ToolPanel()
    assert panel.pivot_tool is not None
    assert panel.pivot_x_spin is not None
    assert panel.pivot_y_spin is not None

    panel.select_tool_by_key("pivot")
    assert panel.ctx_stack.currentIndex() == 6

    received = []
    panel.pivot_changed.connect(lambda x, y: received.append((x, y)))

    panel.pivot_x_spin.setValue(14)
    panel.pivot_y_spin.setValue(22)
    assert (14, 22) in received

    panel.update_pivot_spins(30, 40)
    assert panel.pivot_x_spin.value() == 30
    assert panel.pivot_y_spin.value() == 40
