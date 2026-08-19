"""
Dialog windows for Coopixel (New Canvas, Canvas Size, About).
"""

from typing import Optional, Tuple
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class NewCanvasDialog(QDialog):
    """Dialog for creating a new pixel canvas document."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Create New Image")
        self.setFixedSize(300, 220)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setSpacing(12)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 512)
        self.width_spin.setValue(32)
        self.width_spin.setSuffix(" px")

        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 512)
        self.height_spin.setValue(32)
        self.height_spin.setSuffix(" px")

        self.bg_combo = QComboBox()
        self.bg_combo.addItems(["Transparent", "White", "Black"])

        form.addRow("Width:", self.width_spin)
        form.addRow("Height:", self.height_spin)
        form.addRow("Background:", self.bg_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> Tuple[int, int, str]:
        return self.width_spin.value(), self.height_spin.value(), self.bg_combo.currentText()


class CanvasSizeDialog(QDialog):
    """Dialog for resizing existing canvas."""

    def __init__(self, current_width: int, current_height: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Resize Canvas")
        self.setFixedSize(280, 180)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setSpacing(12)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 512)
        self.width_spin.setValue(current_width)
        self.width_spin.setSuffix(" px")

        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 512)
        self.height_spin.setValue(current_height)
        self.height_spin.setSuffix(" px")

        form.addRow("New Width:", self.width_spin)
        form.addRow("New Height:", self.height_spin)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> Tuple[int, int]:
        return self.width_spin.value(), self.height_spin.value()


class AboutDialog(QDialog):
    """About Coopixel information dialog."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("About Coopixel")
        self.setFixedSize(360, 240)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title_lbl = QLabel("🎨 Coopixel")
        title_lbl.setStyleSheet("font-size: 22px; font-weight: bold; color: #3B82F6;")
        title_lbl.setAlignment(Qt.AlignCenter)

        ver_lbl = QLabel("Version 0.1.0 (Dark Mode Edition)")
        ver_lbl.setStyleSheet("color: #94A3B8; font-weight: 500;")
        ver_lbl.setAlignment(Qt.AlignCenter)

        desc = QLabel(
            "A dark-mode pixel art editor written in Python with PySide6.\n\n"
            "Features:\n"
            "• pycaml compressed & encrypted .pix / .caml save format\n"
            "• Layer management system with sparse pixel storage\n"
            "• Full drawing & shape tools suite\n"
            "• PNG export capability"
        )
        desc.setWordWrap(True)

        layout.addWidget(title_lbl)
        layout.addWidget(ver_lbl)
        layout.addWidget(desc)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
