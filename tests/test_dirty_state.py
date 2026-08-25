"""
Unit tests for Coopixel document dirty tracking, window title indicators (*), and unsaved changes prompting.
"""

import os
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QMessageBox

from coopixel.ui.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_dirty_state_new_file(qapp):
    """Verify new document starts clean and becomes dirty when modified."""
    mw = MainWindow()

    # Starts clean
    assert mw.is_dirty() is False
    assert "*" not in mw.windowTitle()

    # Modify active layer (draw a pixel)
    mw.doc.active_layer.set_pixel(0, 0, "#FF0000FF")
    mw._push_history()

    # Should now be dirty and display asterisk
    assert mw.is_dirty() is True
    assert mw.windowTitle().endswith("*")

    # Undo modification -> should revert to clean
    mw.on_undo()
    assert mw.is_dirty() is False
    assert "*" not in mw.windowTitle()

    mw.close()


def test_dirty_state_save(qapp, tmp_path):
    """Verify saving marks document clean and updates title."""
    mw = MainWindow()

    save_path = str(tmp_path / "dirty_test.pix")
    mw.doc.filepath = save_path
    mw.on_file_save()

    # Clean after save
    assert mw.is_dirty() is False
    assert "*" not in mw.windowTitle()

    # Make modification
    mw.doc.crop_canvas(0, 0, 16, 16)
    mw._push_history()
    assert mw.is_dirty() is True
    assert "*" in mw.windowTitle()

    # Save again -> clean
    mw.on_file_save()
    assert mw.is_dirty() is False
    assert "*" not in mw.windowTitle()

    mw.close()


def test_maybe_save_changes_clean(qapp):
    """Verify maybe_save_changes returns True immediately when clean."""
    mw = MainWindow()
    assert mw.maybe_save_changes("closing") is True
    mw.close()


def test_maybe_save_changes_discard(qapp, monkeypatch):
    """Verify selecting Discard allows proceeding without saving."""
    mw = MainWindow()
    mw.doc.active_layer.set_pixel(1, 1, "#00FF00FF")
    mw._push_history()
    assert mw.is_dirty() is True

    # Mock QMessageBox.question to return Discard
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Discard)

    assert mw.maybe_save_changes("closing") is True
    mw.close()


def test_maybe_save_changes_cancel(qapp, monkeypatch):
    """Verify selecting Cancel aborts the action."""
    mw = MainWindow()
    mw.doc.active_layer.set_pixel(1, 1, "#00FF00FF")
    mw._push_history()
    assert mw.is_dirty() is True

    # Mock QMessageBox.question to return Cancel
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Cancel)

    assert mw.maybe_save_changes("closing") is False
    mw.close()
