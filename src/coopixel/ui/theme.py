"""
Dark theme configuration and stylesheet for Coopixel.
"""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

DARK_STYLESHEET = """
QMainWindow, QDialog, QWidget {
    background-color: #181818;
    color: #E2E8F0;
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Courier New', monospace;
    font-size: 11px;
}

QMenuBar {
    background-color: #202020;
    color: #CBD5E1;
    border-bottom: 1px solid #333333;
    padding: 2px 4px;
    font-size: 11px;
}

QMenuBar::item {
    background-color: transparent;
    padding: 4px 10px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #2E2E2E;
    color: #FFFFFF;
}

QMenu {
    background-color: #202020;
    color: #CBD5E1;
    border: 1px solid #333333;
    border-radius: 6px;
    padding: 4px;
    font-size: 11px;
}

QMenu::item {
    padding: 5px 20px 5px 10px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #2E2620;
    color: #F97316;
}

QMenu::separator {
    height: 1px;
    background: #333333;
    margin: 4px 8px;
}

QToolBar {
    background-color: #202020;
    border-bottom: 1px solid #333333;
    spacing: 6px;
    padding: 4px;
}

QToolButton {
    background-color: #282828;
    color: #E2E8F0;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 4px 8px;
    font-weight: 500;
    font-size: 11px;
}

QToolButton:hover {
    background-color: #332B25;
    border-color: #F97316;
}

QToolButton:checked {
    background-color: #2E2620;
    color: #F97316;
    border-color: #F97316;
}

QDockWidget {
    color: #D97706;
    font-weight: 600;
    font-size: 11px;
}

QDockWidget::title {
    background-color: #242424;
    padding: 6px 8px;
    border-bottom: 1px solid #333333;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    text-align: left;
}

QListWidget {
    background-color: #202020;
    border: 1px solid #333333;
    border-radius: 6px;
    color: #E2E8F0;
    padding: 4px;
    font-size: 11px;
}

QListWidget::item {
    padding: 6px;
    border-radius: 4px;
    margin-bottom: 2px;
}

QListWidget::item:hover {
    background-color: #2A2A2A;
}

QListWidget::item:selected {
    background-color: #2E2620;
    border-left: 3px solid #F97316;
    color: #F8FAFC;
}

QPushButton {
    background-color: #C25E00;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 5px 12px;
    font-weight: 600;
    font-size: 11px;
}

QPushButton:hover {
    background-color: #D97706;
}

QPushButton:pressed {
    background-color: #9A3412;
}

QPushButton:disabled {
    background-color: #2E2E2E;
    color: #64748B;
}

QPushButton#secondaryButton {
    background-color: #282828;
    color: #E2E8F0;
    border: 1px solid #333333;
}

QPushButton#secondaryButton:hover {
    background-color: #332B25;
    border-color: #F97316;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #333333;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #F97316;
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #FB923C;
}

QSpinBox, QLineEdit {
    background-color: #202020;
    border: 1px solid #333333;
    border-radius: 4px;
    color: #E2E8F0;
    padding: 4px 6px;
    font-size: 11px;
}

QSpinBox:focus, QLineEdit:focus {
    border-color: #F97316;
}

QComboBox {
    background-color: #242424;
    color: #F1F5F9;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
}

QComboBox QAbstractItemView {
    background-color: #202020;
    color: #F1F5F9;
    selection-background-color: #2E2620;
    selection-color: #F97316;
    font-size: 11px;
}

QStatusBar {
    background-color: #202020;
    color: #94A3B8;
    border-top: 1px solid #333333;
    font-size: 10px;
}

QToolTip {
    background-color: #1A1A1A;
    color: #F8FAFC;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 3px 6px;
    font-size: 10px;
}
"""


def apply_dark_theme(app: QApplication) -> None:
    """Applies high contrast dark theme palette and stylesheet to the application."""
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#181818"))
    palette.setColor(QPalette.WindowText, QColor("#E2E8F0"))
    palette.setColor(QPalette.Base, QColor("#202020"))
    palette.setColor(QPalette.AlternateBase, QColor("#282828"))
    palette.setColor(QPalette.ToolTipBase, QColor("#1A1A1A"))
    palette.setColor(QPalette.ToolTipText, QColor("#F8FAFC"))
    palette.setColor(QPalette.Text, QColor("#E2E8F0"))
    palette.setColor(QPalette.Button, QColor("#202020"))
    palette.setColor(QPalette.ButtonText, QColor("#E2E8F0"))
    palette.setColor(QPalette.BrightText, QColor("#FF4949"))
    palette.setColor(QPalette.Highlight, QColor("#2E2620"))
    palette.setColor(QPalette.HighlightedText, QColor("#F8FAFC"))
    app.setPalette(palette)
    app.setStyleSheet(DARK_STYLESHEET)


