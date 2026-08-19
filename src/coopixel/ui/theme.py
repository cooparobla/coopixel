"""
Dark theme configuration and stylesheet for Coopixel.
"""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

DARK_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #121417;
    color: #E2E8F0;
    font-family: 'Segoe UI', Inter, Roboto, sans-serif;
}

QMenuBar {
    background-color: #1A1D24;
    color: #CBD5E1;
    border-bottom: 1px solid #2D3748;
    padding: 2px 4px;
    font-size: 13px;
}

QMenuBar::item {
    background-color: transparent;
    padding: 6px 12px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #2D3748;
    color: #FFFFFF;
}

QMenu {
    background-color: #1A1D24;
    color: #CBD5E1;
    border: 1px solid #2D3748;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #3B82F6;
    color: #FFFFFF;
}

QMenu::separator {
    height: 1px;
    background: #2D3748;
    margin: 4px 8px;
}

QToolBar {
    background-color: #1A1D24;
    border-bottom: 1px solid #2D3748;
    spacing: 6px;
    padding: 4px;
}

QToolButton {
    background-color: #262B36;
    color: #E2E8F0;
    border: 1px solid #333B4D;
    border-radius: 6px;
    padding: 6px 10px;
    font-weight: 500;
}

QToolButton:hover {
    background-color: #333B4D;
    border-color: #4A5568;
}

QToolButton:checked {
    background-color: #2563EB;
    color: #FFFFFF;
    border-color: #3B82F6;
}

QDockWidget {
    color: #94A3B8;
    font-weight: 600;
    titlebar-close-icon: url(close.png);
}

QDockWidget::title {
    background-color: #1E232A;
    padding: 8px;
    border-bottom: 1px solid #2D3748;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    text-align: left;
}

QListWidget {
    background-color: #1A1D24;
    border: 1px solid #2D3748;
    border-radius: 6px;
    color: #E2E8F0;
    padding: 4px;
}

QListWidget::item {
    padding: 8px;
    border-radius: 4px;
    margin-bottom: 2px;
}

QListWidget::item:hover {
    background-color: #262B36;
}

QListWidget::item:selected {
    background-color: #2563EB;
    color: #FFFFFF;
}

QPushButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #1D4ED8;
}

QPushButton:pressed {
    background-color: #1E40AF;
}

QPushButton:disabled {
    background-color: #333B4D;
    color: #64748B;
}

QPushButton#secondaryButton {
    background-color: #262B36;
    color: #E2E8F0;
    border: 1px solid #333B4D;
}

QPushButton#secondaryButton:hover {
    background-color: #333B4D;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #2D3748;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #3B82F6;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #60A5FA;
}

QSpinBox, QLineEdit {
    background-color: #1A1D24;
    border: 1px solid #333B4D;
    border-radius: 6px;
    color: #E2E8F0;
    padding: 6px;
}

QSpinBox:focus, QLineEdit:focus {
    border-color: #3B82F6;
}

QStatusBar {
    background-color: #1A1D24;
    color: #94A3B8;
    border-top: 1px solid #2D3748;
}

QToolTip {
    background-color: #0F172A;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 4px 8px;
}
"""


def apply_dark_theme(app: QApplication) -> None:
    """Applies high contrast dark theme palette and stylesheet to the application."""
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#121417"))
    palette.setColor(QPalette.WindowText, QColor("#E2E8F0"))
    palette.setColor(QPalette.Base, QColor("#1A1D24"))
    palette.setColor(QPalette.AlternateBase, QColor("#262B36"))
    palette.setColor(QPalette.ToolTipBase, QColor("#0F172A"))
    palette.setColor(QPalette.ToolTipText, QColor("#F8FAFC"))
    palette.setColor(QPalette.Text, QColor("#E2E8F0"))
    palette.setColor(QPalette.Button, QColor("#1A1D24"))
    palette.setColor(QPalette.ButtonText, QColor("#E2E8F0"))
    palette.setColor(QPalette.BrightText, QColor("#FF4949"))
    palette.setColor(QPalette.Highlight, QColor("#2563EB"))
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)
    app.setStyleSheet(DARK_STYLESHEET)
