"""
Layer Panel Widget for managing document layers in Coopixel.
"""

from typing import Optional
from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDockWidget,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from coopixel.models.document import Layer, PixelDocument


class LayerItemWidget(QWidget):
    """Row widget for a single layer entry in the list."""

    visibility_changed = Signal(int, bool)
    lock_changed = Signal(int, bool)

    def __init__(self, index: int, layer: Layer, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.index = index
        self.layer = layer

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        # Visibility Toggle (👁)
        self.vis_cb = QCheckBox("👁")
        self.vis_cb.setChecked(layer.visible)
        self.vis_cb.setToolTip("Toggle Layer Visibility")
        self.vis_cb.toggled.connect(lambda checked: self.visibility_changed.emit(self.index, checked))

        # Lock Toggle (🔒)
        self.lock_cb = QCheckBox("🔒")
        self.lock_cb.setChecked(layer.locked)
        self.lock_cb.setToolTip("Lock / Unlock Layer")
        self.lock_cb.toggled.connect(lambda checked: self.lock_changed.emit(self.index, checked))

        # Name & Tag label
        name_text = layer.name
        if layer.tag:
            name_text += f" [{layer.tag}]"
        self.name_label = QLabel(name_text)
        self.name_label.setStyleSheet("font-weight: 500; padding-left: 2px;")

        layout.addWidget(self.vis_cb)
        layout.addWidget(self.lock_cb)
        layout.addWidget(self.name_label, stretch=1)


class LayerPanel(QDockWidget):
    # Emitted when layer structure changes (add/delete/move/duplicate) → triggers history push
    layer_structure_changed = Signal()
    # Emitted when only visual attributes change (opacity/visibility/lock) → repaint only
    layer_visual_changed = Signal()

    def __init__(self, doc: Optional[PixelDocument] = None, parent: Optional[QWidget] = None):
        super().__init__("Layers", parent)
        self.doc: PixelDocument = doc if doc is not None else PixelDocument()
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 1. Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        self.add_btn = QPushButton("+ Layer")
        self.add_btn.setToolTip("Add New Layer")
        self.add_btn.clicked.connect(self.on_add_layer)

        self.dup_btn = QPushButton("Dup")
        self.dup_btn.setToolTip("Duplicate Active Layer")
        self.dup_btn.setObjectName("secondaryButton")
        self.dup_btn.clicked.connect(self.on_duplicate_layer)

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setToolTip("Copy Entire Active Layer")
        self.copy_btn.setObjectName("secondaryButton")
        self.copy_btn.clicked.connect(self.on_copy_layer)

        self.paste_btn = QPushButton("Paste")
        self.paste_btn.setToolTip("Paste Copied Layer")
        self.paste_btn.setObjectName("secondaryButton")
        self.paste_btn.clicked.connect(self.on_paste_layer)

        self.del_btn = QPushButton("Del")
        self.del_btn.setToolTip("Delete Active Layer")
        self.del_btn.setObjectName("secondaryButton")
        self.del_btn.clicked.connect(self.on_delete_layer)

        self.up_btn = QPushButton("▲")
        self.up_btn.setToolTip("Move Layer Up")
        self.up_btn.setObjectName("secondaryButton")
        self.up_btn.clicked.connect(self.on_move_up)

        self.down_btn = QPushButton("▼")
        self.down_btn.setToolTip("Move Layer Down")
        self.down_btn.setObjectName("secondaryButton")
        self.down_btn.clicked.connect(self.on_move_down)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.dup_btn)
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addWidget(self.paste_btn)
        btn_layout.addWidget(self.del_btn)
        btn_layout.addWidget(self.up_btn)
        btn_layout.addWidget(self.down_btn)
        layout.addLayout(btn_layout)

        # 2. Layer List
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.list_widget, stretch=1)

        # 3. Opacity Slider
        opacity_layout = QHBoxLayout()
        opacity_layout.setSpacing(8)
        opacity_lbl = QLabel("Opacity:")
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_val_label = QLabel("100%")
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)

        opacity_layout.addWidget(opacity_lbl)
        opacity_layout.addWidget(self.opacity_slider, stretch=1)
        opacity_layout.addWidget(self.opacity_val_label)
        layout.addLayout(opacity_layout)

        self.setWidget(main_widget)
        self.refresh_list()

    def set_document(self, doc: PixelDocument) -> None:
        self.doc = doc
        self.refresh_list()

    def refresh_list(self) -> None:
        """Rebuild the layer list from the current document state."""
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        # Display layers in descending index order (top layer first)
        for i in reversed(range(len(self.doc.layers))):
            layer = self.doc.layers[i]
            item = QListWidgetItem()
            item.setData(Qt.UserRole, i)

            widget = LayerItemWidget(i, layer)
            widget.visibility_changed.connect(self._on_visibility_changed)
            widget.lock_changed.connect(self._on_lock_changed)

            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

            if i == self.doc.active_layer_index:
                self.list_widget.setCurrentItem(item)

        self.list_widget.blockSignals(False)

        # Sync opacity slider to active layer
        active = self.doc.active_layer
        if active:
            val = int(active.opacity * 100)
            self.opacity_slider.blockSignals(True)
            self.opacity_slider.setValue(val)
            self.opacity_val_label.setText(f"{val}%")
            self.opacity_slider.blockSignals(False)

    # ------------------------------------------------------------------
    # Internal slots (not history-emitting selection change)
    # ------------------------------------------------------------------

    def _on_row_changed(self, row: int) -> None:
        """Switches active layer — does NOT push history."""
        if row < 0:
            return
        item = self.list_widget.item(row)
        if item:
            index = item.data(Qt.UserRole)
            self.doc.active_layer_index = index

            active = self.doc.active_layer
            if active:
                val = int(active.opacity * 100)
                self.opacity_slider.blockSignals(True)
                self.opacity_slider.setValue(val)
                self.opacity_val_label.setText(f"{val}%")
                self.opacity_slider.blockSignals(False)

    def _on_opacity_changed(self, val: int) -> None:
        """Opacity change — visual only (no history push)."""
        active = self.doc.active_layer
        if active:
            active.opacity = val / 100.0
            self.opacity_val_label.setText(f"{val}%")
            self.layer_visual_changed.emit()

    def _on_visibility_changed(self, index: int, visible: bool) -> None:
        if 0 <= index < len(self.doc.layers):
            self.doc.layers[index].visible = visible
            self.layer_visual_changed.emit()

    def _on_lock_changed(self, index: int, locked: bool) -> None:
        if 0 <= index < len(self.doc.layers):
            self.doc.layers[index].locked = locked
            self.layer_visual_changed.emit()

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        index = item.data(Qt.UserRole)
        if 0 <= index < len(self.doc.layers):
            layer = self.doc.layers[index]
            new_name, ok = QInputDialog.getText(self, "Rename Layer", "Layer Name:", text=layer.name)
            if ok and new_name.strip():
                layer.name = new_name.strip()
                self.refresh_list()
                # Renaming is a structure change (saved in document dict)
                self.layer_structure_changed.emit()

    # ------------------------------------------------------------------
    # Public layer action slots (called from buttons and menu)
    # ------------------------------------------------------------------

    def on_add_layer(self) -> None:
        self.doc.add_layer()
        self.refresh_list()
        self.layer_structure_changed.emit()

    def on_duplicate_layer(self) -> None:
        self.doc.duplicate_layer(self.doc.active_layer_index)
        self.refresh_list()
        self.layer_structure_changed.emit()

    def on_delete_layer(self) -> None:
        if self.doc.delete_layer(self.doc.active_layer_index):
            self.refresh_list()
            self.layer_structure_changed.emit()

    def on_move_up(self) -> None:
        if self.doc.move_layer_up(self.doc.active_layer_index):
            self.refresh_list()
            self.layer_structure_changed.emit()

    def on_move_down(self) -> None:
        if self.doc.move_layer_down(self.doc.active_layer_index):
            self.refresh_list()
            self.layer_structure_changed.emit()

    def _on_context_menu(self, pos: QPoint) -> None:
        item = self.list_widget.itemAt(pos)
        if item:
            index = item.data(Qt.UserRole)
            self.doc.active_layer_index = index

        menu = QMenu(self)
        copy_act = menu.addAction("📋 Copy Layer")
        paste_act = menu.addAction("📥 Paste Layer")
        paste_act.setEnabled(getattr(LayerPanel, "_shared_layer_clipboard", None) is not None)
        menu.addSeparator()
        tag_act = menu.addAction("🏷️ Set Tag...")
        dup_act = menu.addAction("📑 Duplicate Layer")
        rename_act = menu.addAction("✏️ Rename Layer")
        crop_act = menu.addAction("✂️ Crop Layer to Canvas")
        del_act = menu.addAction("🗑️ Delete Layer")

        action = menu.exec_(self.list_widget.mapToGlobal(pos)) if hasattr(menu, 'exec_') else menu.exec(self.list_widget.mapToGlobal(pos))
        if action == copy_act:
            self.on_copy_layer()
        elif action == paste_act:
            self.on_paste_layer()
        elif action == tag_act:
            self.on_set_layer_tag()
        elif action == dup_act:
            self.on_duplicate_layer()
        elif action == rename_act and item:
            self._on_item_double_clicked(item)
        elif action == crop_act:
            self.on_crop_layer_to_canvas()
        elif action == del_act:
            self.on_delete_layer()

    def on_copy_layer(self) -> None:
        active = self.doc.active_layer
        if active:
            LayerPanel._shared_layer_clipboard = active.clone(name=active.name)

    def on_paste_layer(self) -> None:
        clipboard = getattr(LayerPanel, "_shared_layer_clipboard", None)
        if clipboard:
            cloned = clipboard.clone()
            insert_idx = self.doc.active_layer_index + 1 if self.doc.layers else 0
            self.doc.layers.insert(insert_idx, cloned)
            self.doc.active_layer_index = insert_idx
            self.refresh_list()
            self.layer_structure_changed.emit()

    def on_crop_layer_to_canvas(self) -> None:
        self.doc.crop_active_layer_to_canvas()
        self.refresh_list()
        self.layer_structure_changed.emit()

    def on_set_layer_tag(self) -> None:
        active = self.doc.active_layer
        if active:
            new_tag, ok = QInputDialog.getText(
                self, "Set Layer Tag", "Tag Name (e.g. 'character', 'bg', 'shadow'):", text=active.tag
            )
            if ok:
                active.tag = new_tag.strip()
                self.refresh_list()
                self.layer_structure_changed.emit()

