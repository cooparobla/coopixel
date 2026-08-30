"""
Pytest configuration for Coopixel unit tests.
Forces Qt to run in offscreen headless mode so no GUI windows launch on the desktop screen.
"""

import os
import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture(autouse=True)
def auto_dismiss_message_boxes(monkeypatch):
    """Automatically dismiss modal QMessageBox dialogs in test runs."""
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Discard)
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: QMessageBox.Ok)


class SimpleQtBot:
    def addWidget(self, widget):
        pass


@pytest.fixture
def qtbot(qapp):
    return SimpleQtBot()



