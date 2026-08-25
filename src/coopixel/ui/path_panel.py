"""
Paths Panel Dock Widget for Coopixel.
Manages vector Bezier paths, layer associations, path selection, and stroke/fill operations.
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDockWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from coopixel.models.document import PixelDocument
from coopixel.models.path import VectorPath


class PathPanel(QDockWidget):
    """Dock panel for managing vector paths and performing stroke/fill operations."""

    path_changed = Signal()
    path_selected = Signal(int)

    def __init__(self, doc: Optional[PixelDocument] = None, parent: Optional[QWidget] = None):
        super().__init__("Paths", parent)
        self.doc: PixelDocument = doc if doc is not None else PixelDocument()
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # ---- Header & Action Toolbar ----
        lbl = QLabel("Vector Paths Management")
        lbl.setStyleSheet("font-weight: 600; color: #94A3B8; font-size: 11px;")
        main_layout.addWidget(lbl)

        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(4)

        self.add_btn = QPushButton("+ New")
        self.add_btn.setToolTip("Create new vector path")
        self.add_btn.setObjectName("secondaryButton")
        self.add_btn.clicked.connect(self.on_add_path)

        self.stroke_btn = QPushButton("🖌️ Stroke")
        self.stroke_btn.setToolTip("Rasterize path outline onto active layer")
        self.stroke_btn.setObjectName("secondaryButton")
        self.stroke_btn.clicked.connect(self.on_stroke_path)

        self.fill_btn = QPushButton("🎨 Fill")
        self.fill_btn.setToolTip("Rasterize filled path interior onto active layer")
        self.fill_btn.setObjectName("secondaryButton")
        self.fill_btn.clicked.connect(self.on_fill_path)

        self.del_btn = QPushButton("🗑️")
        self.del_btn.setToolTip("Delete selected path")
        self.del_btn.setFixedWidth(28)
        self.del_btn.setObjectName("secondaryButton")
        self.del_btn.clicked.connect(self.on_delete_path)

        btn_bar.addWidget(self.add_btn)
        btn_bar.addWidget(self.stroke_btn)
        btn_bar.addWidget(self.fill_btn)
        btn_bar.addWidget(self.del_btn)
        main_layout.addLayout(btn_bar)

        # ---- Paths List Widget ----
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "QListWidget { background-color: #0F172A; border: 1px solid #334155; border-radius: 4px; }"
            "QListWidget::item { padding: 6px; border-bottom: 1px solid #1E293B; color: #F1F5F9; }"
            "QListWidget::item:selected { background-color: #C25E00; color: #FFFFFF; font-weight: bold; }"
        )
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        main_layout.addWidget(self.list_widget, stretch=1)

        self.setWidget(main_widget)
        self.refresh_panel()

    def set_document(self, doc: PixelDocument) -> None:
        self.doc = doc
        self.refresh_panel()

    def refresh_panel(self) -> None:
        """Rebuilds the paths list from document.paths."""
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        for idx, path in enumerate(self.doc.paths):
            count = len(path.anchors)
            layer_info = f" [{path.layer_id}]" if path.layer_id else ""
            status = " [Closed]" if path.closed else ""
            text = f"🖋️ {path.name}{layer_info} ({count} pts){status}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, idx)
            self.list_widget.addItem(item)

        if self.doc.active_path_index is not None and 0 <= self.doc.active_path_index < self.list_widget.count():
            self.list_widget.setCurrentRow(self.doc.active_path_index)
            self.stroke_btn.setEnabled(True)
            self.fill_btn.setEnabled(True)
            self.del_btn.setEnabled(True)
        else:
            self.stroke_btn.setEnabled(False)
            self.fill_btn.setEnabled(False)
            self.del_btn.setEnabled(False)

        self.list_widget.blockSignals(False)

    def _on_row_changed(self, row: int) -> None:
        if 0 <= row < len(self.doc.paths):
            self.doc.active_path_index = row
            path = self.doc.paths[row]

            # Automatically select the layer associated with this path if it exists
            if path.layer_id:
                for idx, layer in enumerate(self.doc.layers):
                    if layer.name == path.layer_id:
                        self.doc.active_layer_index = idx
                        break

            self.stroke_btn.setEnabled(True)
            self.fill_btn.setEnabled(True)
            self.del_btn.setEnabled(True)
            self.path_selected.emit(row)

    def on_add_path(self) -> None:
        self.doc.add_path()
        self.refresh_panel()
        self.path_changed.emit()

    def on_delete_path(self) -> None:
        if self.doc.active_path_index is not None:
            self.doc.remove_path(self.doc.active_path_index)
            self.refresh_panel()
            self.path_changed.emit()

    def on_stroke_path(self) -> None:
        path = self.doc.active_path
        if path:
            # Uses primary color from parent or window if available
            parent_window = self.window()
            pri_color = getattr(parent_window, "primary_color", "#FF004DFF")
            brush_size = getattr(parent_window, "brush_size", 1)
            self.doc.stroke_path(path, pri_color, brush_size)
            self.path_changed.emit()

    def on_fill_path(self) -> None:
        path = self.doc.active_path
        if path:
            parent_window = self.window()
            pri_color = getattr(parent_window, "primary_color", "#FF004DFF")
            self.doc.fill_path(path, pri_color)
            self.path_changed.emit()
