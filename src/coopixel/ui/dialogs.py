"""
Dialog windows for Coopixel (New Canvas, Canvas Size, About).
"""

import os
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


from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QGridLayout,
    QVBoxLayout,
    QWidget,
)


class CanvasSizeDialog(QDialog):
    """Dialog for resizing existing canvas with anchor selection."""

    ANCHORS = [
        ("top-left", "↖"), ("top-center", "↑"), ("top-right", "↗"),
        ("middle-left", "←"), ("center", "•"), ("middle-right", "→"),
        ("bottom-left", "↙"), ("bottom-center", "↓"), ("bottom-right", "↘"),
    ]

    def __init__(self, current_width: int, current_height: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Resize Canvas")
        self.setFixedSize(320, 320)

        self.current_width = current_width
        self.current_height = current_height

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        info_label = QLabel(f"Current Size: {current_width} × {current_height} px")
        info_label.setStyleSheet("color: #94A3B8; font-weight: bold;")
        layout.addWidget(info_label)

        form = QFormLayout()
        form.setSpacing(8)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 4096)
        self.width_spin.setValue(current_width)
        self.width_spin.setSuffix(" px")

        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 4096)
        self.height_spin.setValue(current_height)
        self.height_spin.setSuffix(" px")

        form.addRow("New Width:", self.width_spin)
        form.addRow("New Height:", self.height_spin)
        layout.addLayout(form)

        # Anchor positioning group box
        anchor_group = QGroupBox("Anchor Position")
        anchor_grid = QGridLayout(anchor_group)
        anchor_grid.setSpacing(4)

        self.button_group = QButtonGroup(self)
        self.selected_anchor = "top-left"

        for idx, (anchor_key, symbol) in enumerate(self.ANCHORS):
            row, col = divmod(idx, 3)
            btn = QPushButton(symbol)
            btn.setCheckable(True)
            btn.setFixedSize(36, 36)
            btn.setToolTip(anchor_key.replace("-", " ").title())
            if anchor_key == "top-left":
                btn.setChecked(True)

            self.button_group.addButton(btn, idx)
            anchor_grid.addWidget(btn, row, col, Qt.AlignCenter)

        self.button_group.idClicked.connect(self._on_anchor_clicked)
        layout.addWidget(anchor_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_anchor_clicked(self, btn_id: int) -> None:
        if 0 <= btn_id < len(self.ANCHORS):
            self.selected_anchor = self.ANCHORS[btn_id][0]

    def get_values(self) -> Tuple[int, int, str]:
        """Returns (new_width, new_height, anchor_position)."""
        return self.width_spin.value(), self.height_spin.value(), self.selected_anchor


class CropCanvasDialog(QDialog):
    """Modal dialog for cropping canvas region."""

    def __init__(
        self,
        current_width: int,
        current_height: int,
        selection_bbox: Optional[Tuple[int, int, int, int]] = None,
        content_bbox: Optional[Tuple[int, int, int, int]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Crop Canvas")
        self.setFixedSize(320, 310)

        self.current_width = current_width
        self.current_height = current_height
        self.selection_bbox = selection_bbox
        self.content_bbox = content_bbox

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        info_label = QLabel(f"Current Canvas: {current_width} × {current_height} px")
        info_label.setStyleSheet("color: #94A3B8; font-weight: bold;")
        layout.addWidget(info_label)

        form = QFormLayout()
        form.setSpacing(8)

        self.x_spin = QSpinBox()
        self.x_spin.setRange(-2048, 4096)
        self.x_spin.setValue(0)
        self.x_spin.setSuffix(" px")

        self.y_spin = QSpinBox()
        self.y_spin.setRange(-2048, 4096)
        self.y_spin.setValue(0)
        self.y_spin.setSuffix(" px")

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 4096)
        self.width_spin.setValue(current_width)
        self.width_spin.setSuffix(" px")

        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 4096)
        self.height_spin.setValue(current_height)
        self.height_spin.setSuffix(" px")

        form.addRow("X Offset:", self.x_spin)
        form.addRow("Y Offset:", self.y_spin)
        form.addRow("Crop Width:", self.width_spin)
        form.addRow("Crop Height:", self.height_spin)
        layout.addLayout(form)

        # Quick preset buttons: Fit to Selection / Fit to Content
        btn_layout = QHBoxLayout()
        self.btn_fit_sel = QPushButton("Fit Selection")
        self.btn_fit_sel.setToolTip("Crop canvas to bounding box of active selection")
        self.btn_fit_sel.setEnabled(selection_bbox is not None)
        self.btn_fit_sel.clicked.connect(self._apply_selection_bbox)

        self.btn_fit_content = QPushButton("Fit Content")
        self.btn_fit_content.setToolTip("Crop canvas to non-transparent pixel content bounds")
        self.btn_fit_content.setEnabled(content_bbox is not None)
        self.btn_fit_content.clicked.connect(self._apply_content_bbox)

        btn_layout.addWidget(self.btn_fit_sel)
        btn_layout.addWidget(self.btn_fit_content)
        layout.addLayout(btn_layout)

        # If selection bbox exists, default to selection bounds
        if selection_bbox is not None:
            self._apply_selection_bbox()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply_selection_bbox(self) -> None:
        if self.selection_bbox:
            x, y, w, h = self.selection_bbox
            self.x_spin.setValue(x)
            self.y_spin.setValue(y)
            self.width_spin.setValue(w)
            self.height_spin.setValue(h)

    def _apply_content_bbox(self) -> None:
        if self.content_bbox:
            x, y, w, h = self.content_bbox
            self.x_spin.setValue(x)
            self.y_spin.setValue(y)
            self.width_spin.setValue(w)
            self.height_spin.setValue(h)

    def get_values(self) -> Tuple[int, int, int, int]:
        """Returns (x, y, crop_width, crop_height)."""
        return self.x_spin.value(), self.y_spin.value(), self.width_spin.value(), self.height_spin.value()


class AboutDialog(QDialog):
    """About Coopixel information dialog."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("About Coopixel")
        self.setFixedSize(360, 240)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title_lbl = QLabel("🎨 Coopixel")
        title_lbl.setStyleSheet("font-size: 22px; font-weight: bold; color: #F97316;")
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


class ImportImageDialog(QDialog):
    """Modal popup dialog for setting options when importing an image as a layer."""

    def __init__(
        self,
        filepath: str,
        img_width: int,
        img_height: int,
        canvas_width: int,
        canvas_height: int,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Import Image Options")
        self.setFixedSize(380, 310)

        self.filepath = filepath
        self.img_width = img_width
        self.img_height = img_height
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        filename = os.path.basename(filepath)
        info_lbl = QLabel(
            f"<b>File:</b> {filename}<br>"
            f"<b>Image Dimensions:</b> {img_width} × {img_height} px<br>"
            f"<b>Current Canvas Size:</b> {canvas_width} × {canvas_height} px"
        )
        info_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; background: #1E293B; padding: 10px; border-radius: 4px;")
        layout.addWidget(info_lbl)

        form = QFormLayout()
        form.setSpacing(10)

        default_name = os.path.splitext(filename)[0]
        self.name_edit = QLineEdit(default_name)
        form.addRow("Layer Name:", self.name_edit)

        layout.addLayout(form)

        # Behavior options
        options_group = QGroupBox("Canvas & Sizing Options")
        opt_layout = QVBoxLayout(options_group)
        opt_layout.setSpacing(6)

        self.resize_cb = QCheckBox(f"Resize canvas to fit imported image ({img_width} × {img_height} px)")
        self.resize_cb.setToolTip("Resizes document canvas dimensions to match the imported image size")
        if img_width != canvas_width or img_height != canvas_height:
            self.resize_cb.setChecked(True)

        self.scale_cb = QCheckBox("Scale image to fit current canvas size")
        self.scale_cb.setToolTip("Scales the imported image to fit inside current canvas bounds")

        self.resize_cb.toggled.connect(self._on_resize_toggled)
        self.scale_cb.toggled.connect(self._on_scale_toggled)

        opt_layout.addWidget(self.resize_cb)
        opt_layout.addWidget(self.scale_cb)
        layout.addWidget(options_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_resize_toggled(self, checked: bool) -> None:
        if checked:
            self.scale_cb.setChecked(False)

    def _on_scale_toggled(self, checked: bool) -> None:
        if checked:
            self.resize_cb.setChecked(False)

    def get_values(self) -> Tuple[str, bool, bool]:
        """Returns (layer_name, resize_canvas, scale_to_canvas)."""
        name = self.name_edit.text().strip() or "Imported Layer"
        return name, self.resize_cb.isChecked(), self.scale_cb.isChecked()
