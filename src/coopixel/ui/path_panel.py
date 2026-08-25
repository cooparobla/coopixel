"""
Paths Panel Dock Widget for Coopixel.
Manages vector Bezier paths, layer associations, path selection, dynamic stroke/fill toggles, and stroke/fill rasterization operations.
"""

from typing import Optional
from PySide6.QtCore import QSize, Qt, Signal
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


class PathItemWidget(QFrame):
    """Row widget representing a single vector path with dynamic stroke & fill icon toggles."""

    stroke_toggled = Signal(int, bool)
    fill_toggled = Signal(int, bool)
    delete_clicked = Signal(int)

    def __init__(self, path: VectorPath, path_index: int, is_active: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.path = path
        self.path_index = path_index

        self.setFrameShape(QFrame.StyledPanel)
        active_border = "border-left: 3px solid #F97316; background-color: #2E2620;" if is_active else "background-color: #242424;"
        self.setStyleSheet(
            f"PathItemWidget {{ {active_border} border-bottom: 1px solid #333333; border-radius: 4px; padding: 2px; }}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        count = len(path.anchors)
        status = " [Closed]" if path.closed else ""
        self.name_label = QLabel(f"🖋️ {path.name} ({count} pts){status}")
        self.name_label.setStyleSheet("font-weight: 600; color: #F1F5F9; font-size: 11px;")

        # Dynamic Stroke Toggle Button
        self.stroke_btn = QPushButton("Stroke")
        self.stroke_btn.setToolTip("Toggle dynamic stroke outline rendering on canvas")
        self.stroke_btn.setCheckable(True)
        self.stroke_btn.setChecked(path.stroked)
        self.stroke_btn.setMinimumHeight(24)
        self.stroke_btn.setStyleSheet(
            "QPushButton { background: #282828; border: 1px solid #333333; border-radius: 4px; font-size: 10px; color: #94A3B8; padding: 3px 6px; }"
            "QPushButton:checked { background: #2E2620; border-color: #F97316; color: #F97316; font-weight: bold; }"
            "QPushButton:hover { border-color: #F97316; }"
        )
        self.stroke_btn.toggled.connect(self._on_stroke_toggled)

        # Dynamic Fill Toggle Button
        self.fill_btn = QPushButton("Fill")
        self.fill_btn.setToolTip("Toggle dynamic fill interior rendering on canvas")
        self.fill_btn.setCheckable(True)
        self.fill_btn.setChecked(path.filled)
        self.fill_btn.setMinimumHeight(24)
        self.fill_btn.setStyleSheet(
            "QPushButton { background: #282828; border: 1px solid #333333; border-radius: 4px; font-size: 10px; color: #94A3B8; padding: 3px 6px; }"
            "QPushButton:checked { background: #2E2620; border-color: #F97316; color: #F97316; font-weight: bold; }"
            "QPushButton:hover { border-color: #F97316; }"
        )
        self.fill_btn.toggled.connect(self._on_fill_toggled)

        # Delete Button
        self.del_btn = QPushButton("✕")
        self.del_btn.setToolTip("Delete vector path")
        self.del_btn.setMinimumHeight(24)
        self.del_btn.setStyleSheet(
            "QPushButton { background: #282828; border: 1px solid #333333; border-radius: 4px; font-size: 11px; color: #E2E8F0; padding: 3px 6px; }"
            "QPushButton:hover { background: #7F1D1D; border-color: #EF4444; color: #FFFFFF; }"
        )
        self.del_btn.clicked.connect(lambda: self.delete_clicked.emit(self.path_index))

        layout.addWidget(self.name_label, stretch=1)
        layout.addWidget(self.stroke_btn)
        layout.addWidget(self.fill_btn)
        layout.addWidget(self.del_btn)


    def _on_stroke_toggled(self, checked: bool) -> None:
        self.path.stroked = checked
        self.stroke_toggled.emit(self.path_index, checked)

    def _on_fill_toggled(self, checked: bool) -> None:
        self.path.filled = checked
        self.fill_toggled.emit(self.path_index, checked)


class PathPanel(QDockWidget):
    """Dock panel for managing vector paths and performing dynamic & rasterized stroke/fill operations."""

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

        self.stroke_btn = QPushButton("🖌️ Bake Stroke")
        self.stroke_btn.setToolTip("Permanently rasterize path outline onto active layer")
        self.stroke_btn.setObjectName("secondaryButton")
        self.stroke_btn.clicked.connect(self.on_stroke_path)

        self.fill_btn = QPushButton("🎨 Bake Fill")
        self.fill_btn.setToolTip("Permanently rasterize filled path interior onto active layer")
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
            "QListWidget { background-color: #202020; border: 1px solid #333333; border-radius: 6px; color: #E2E8F0; padding: 4px; font-size: 11px; }"
            "QListWidget::item { padding: 2px; border-radius: 4px; margin-bottom: 2px; color: #E2E8F0; }"
            "QListWidget::item:hover { background-color: #2A2A2A; }"
            "QListWidget::item:selected { background-color: #2E2620; border-left: 3px solid #F97316; color: #F8FAFC; font-weight: bold; }"
        )
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        main_layout.addWidget(self.list_widget, stretch=1)

        self.setWidget(main_widget)
        self.refresh_panel()

    def set_document(self, doc: PixelDocument) -> None:
        self.doc = doc
        self.refresh_panel()

    def refresh_panel(self) -> None:
        """Rebuilds the paths list from document.paths for current layer and current frame."""
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        active_layer_name = self.doc.active_layer.name if self.doc.active_layer else ""
        active_frame_idx = getattr(self.doc, "active_frame_index", 0)

        current_selected_row = -1
        row_counter = 0

        for idx, path in enumerate(self.doc.paths):
            if path.layer_id and path.layer_id != active_layer_name:
                continue
            if path.frame_index is not None and path.frame_index != active_frame_idx:
                continue

            is_active = (idx == self.doc.active_path_index)

            item = QListWidgetItem()
            widget = PathItemWidget(path, idx, is_active=is_active)
            widget.stroke_toggled.connect(lambda _i, _c: self.path_changed.emit())
            widget.fill_toggled.connect(lambda _i, _c: self.path_changed.emit())
            widget.delete_clicked.connect(self._on_widget_delete_requested)

            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.UserRole, idx)

            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

            if is_active:
                current_selected_row = row_counter

            row_counter += 1

        if current_selected_row >= 0:
            self.list_widget.setCurrentRow(current_selected_row)
            self.stroke_btn.setEnabled(True)
            self.fill_btn.setEnabled(True)
            self.del_btn.setEnabled(True)
        elif self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
            self.stroke_btn.setEnabled(True)
            self.fill_btn.setEnabled(True)
            self.del_btn.setEnabled(True)
        else:
            self.stroke_btn.setEnabled(False)
            self.fill_btn.setEnabled(False)
            self.del_btn.setEnabled(False)

        self.list_widget.blockSignals(False)

    def _on_widget_delete_requested(self, orig_idx: int) -> None:
        self.doc.remove_path(orig_idx)
        self.refresh_panel()
        self.path_changed.emit()

    def _on_row_changed(self, row: int) -> None:
        if 0 <= row < self.list_widget.count():
            item = self.list_widget.item(row)
            orig_idx = item.data(Qt.UserRole)
            if orig_idx is not None and 0 <= orig_idx < len(self.doc.paths):
                self.doc.active_path_index = orig_idx
                path = self.doc.paths[orig_idx]

                if path.layer_id:
                    for idx, layer in enumerate(self.doc.layers):
                        if layer.name == path.layer_id:
                            self.doc.active_layer_index = idx
                            break

                self.stroke_btn.setEnabled(True)
                self.fill_btn.setEnabled(True)
                self.del_btn.setEnabled(True)
                self.path_selected.emit(orig_idx)

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
