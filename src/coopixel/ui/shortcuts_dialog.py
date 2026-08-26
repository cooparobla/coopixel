"""
Keyboard Shortcuts Configuration Dialog and Manager for Coopixel.
Allows viewing, searching, customizing, saving, and resetting keyboard shortcuts.
"""

import json
import os
from typing import Dict, Optional
from PySide6.QtCore import Qt, QKeyCombination
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QKeySequenceEdit,
)

CONFIG_DIR = os.path.expanduser("~/.config/coopixel")
SHORTCUTS_FILE = os.path.join(CONFIG_DIR, "shortcuts.json")

# Default shortcuts definition mapping action_id -> info
DEFAULT_SHORTCUTS: Dict[str, Dict[str, str]] = {
    # File Menu
    "file_new": {"name": "New Document", "category": "File", "default": "Ctrl+N"},
    "file_open": {"name": "Open Document", "category": "File", "default": "Ctrl+O"},
    "file_save": {"name": "Save Document", "category": "File", "default": "Ctrl+S"},
    "file_save_as": {"name": "Save As", "category": "File", "default": "Ctrl+Shift+S"},
    "file_import_layer": {"name": "Import Image as Layer", "category": "File", "default": "Ctrl+Shift+I"},
    "file_import_palette": {"name": "Import Palette PNG", "category": "File", "default": "Ctrl+Shift+P"},
    "file_export": {"name": "Export PNG", "category": "File", "default": "Ctrl+E"},
    "file_exit": {"name": "Exit Application", "category": "File", "default": "Ctrl+Q"},

    # Edit Menu
    "edit_undo": {"name": "Undo", "category": "Edit", "default": "Ctrl+Z"},
    "edit_redo": {"name": "Redo", "category": "Edit", "default": "Ctrl+Y"},
    "edit_cut": {"name": "Cut", "category": "Edit", "default": "Ctrl+X"},
    "edit_copy": {"name": "Copy", "category": "Edit", "default": "Ctrl+C"},
    "edit_paste": {"name": "Paste", "category": "Edit", "default": "Ctrl+V"},
    "edit_select_all": {"name": "Select All", "category": "Edit", "default": "Ctrl+A"},
    "edit_deselect": {"name": "Deselect", "category": "Edit", "default": "Escape"},
    "edit_invert_selection": {"name": "Invert Selection", "category": "Edit", "default": "Ctrl+I"},
    "edit_select_layer_content": {"name": "Select Layer Content", "category": "Edit", "default": "Ctrl+Shift+A"},

    # Tools
    "tool_pen": {"name": "Pen Tool", "category": "Tools", "default": "P"},
    "tool_selection": {"name": "Selection Tool", "category": "Tools", "default": "S"},
    "tool_pencil": {"name": "Draw Tool", "category": "Tools", "default": "D"},
    "tool_eraser": {"name": "Eraser Tool", "category": "Tools", "default": "E"},
    "tool_picker": {"name": "Color Picker Tool", "category": "Tools", "default": "I"},
    "tool_fill": {"name": "Bucket Fill Tool", "category": "Tools", "default": "F"},
    "tool_line": {"name": "Line Tool", "category": "Tools", "default": "L"},
    "tool_rect": {"name": "Rectangle Tool", "category": "Tools", "default": "R"},
    "tool_circle": {"name": "Circle Tool", "category": "Tools", "default": "C"},
    "tool_crop": {"name": "Crop Tool", "category": "Tools", "default": "K"},
    "tool_move": {"name": "Move Tool", "category": "Tools", "default": "V"},
    "tool_pivot": {"name": "Pivot Tool", "category": "Tools", "default": "Shift+P"},
    "decrease_size": {"name": "Decrease Tool Size", "category": "Tools", "default": "["},
    "increase_size": {"name": "Increase Tool Size", "category": "Tools", "default": "]"},

    # Image / View
    "crop_canvas_dialog": {"name": "Crop Canvas Dialog", "category": "Image", "default": "Ctrl+Shift+X"},
    "zoom_in": {"name": "Zoom In", "category": "View", "default": "Ctrl+="},
    "zoom_out": {"name": "Zoom Out", "category": "View", "default": "Ctrl+-"},
    "zoom_reset": {"name": "Reset Zoom", "category": "View", "default": "Ctrl+0"},
    "center_canvas": {"name": "Center Canvas", "category": "View", "default": "A"},
    "toggle_grid": {"name": "Toggle Grid", "category": "View", "default": "Ctrl+G"},
    "toggle_bounds": {"name": "Toggle Layer Bounds", "category": "View", "default": "Ctrl+Shift+B"},

    # Layers & Animation
    "add_layer": {"name": "Add New Layer", "category": "Layer", "default": "Ctrl+Shift+N"},
    "delete_layer": {"name": "Delete Layer", "category": "Layer", "default": "Delete"},
    "copy_layer": {"name": "Copy Layer", "category": "Layer", "default": "Ctrl+Shift+C"},
    "paste_layer": {"name": "Paste Layer", "category": "Layer", "default": "Ctrl+Shift+V"},
    "play_animation": {"name": "Play / Pause Animation", "category": "Animation", "default": "Space"},
}


def load_shortcuts() -> Dict[str, str]:
    """Loads shortcuts mapping action_id -> shortcut_string. Falls back to defaults."""
    shortcuts = {act_id: info["default"] for act_id, info in DEFAULT_SHORTCUTS.items()}
    if os.path.exists(SHORTCUTS_FILE):
        try:
            with open(SHORTCUTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    for act_id, val in data.items():
                        if act_id in shortcuts and isinstance(val, str):
                            shortcuts[act_id] = val
        except Exception:
            pass
    return shortcuts


def save_shortcuts(shortcuts: Dict[str, str]) -> bool:
    """Saves shortcuts mapping action_id -> shortcut_string to user config."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(SHORTCUTS_FILE, "w", encoding="utf-8") as f:
            json.dump(shortcuts, f, indent=2)
        return True
    except Exception:
        return False


class ShortcutsDialog(QDialog):
    """Dialog for customizing keyboard shortcuts."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.resize(560, 480)

        self.current_shortcuts = load_shortcuts()
        self.edits: Dict[str, QKeySequenceEdit] = {}

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Search Bar
        search_layout = QHBoxLayout()
        search_lbl = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter shortcuts by name or category...")
        self.search_input.textChanged.connect(self._filter_table)
        search_layout.addWidget(search_lbl)
        search_layout.addWidget(self.search_input, stretch=1)
        layout.addLayout(search_layout)

        # Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Action", "Category", "Shortcut Key"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table, stretch=1)

        self._populate_table()

        # Bottom Buttons
        btn_layout = QHBoxLayout()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setToolTip("Restore all shortcuts to their default values")
        reset_btn.clicked.connect(self._reset_to_defaults)
        btn_layout.addWidget(reset_btn)

        btn_layout.addStretch(1)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        btn_layout.addWidget(button_box)

        layout.addLayout(btn_layout)

    def _populate_table(self) -> None:
        self.table.setRowCount(0)
        self.edits.clear()

        row = 0
        for act_id, info in DEFAULT_SHORTCUTS.items():
            self.table.insertRow(row)

            # Name Item
            name_item = QTableWidgetItem(info["name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, name_item)

            # Category Item
            cat_item = QTableWidgetItem(info["category"])
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, cat_item)

            # KeySequenceEdit
            cur_seq = self.current_shortcuts.get(act_id, info["default"])
            seq_edit = QKeySequenceEdit(QKeySequence(cur_seq))
            seq_edit.setToolTip("Click and press desired shortcut key combination")
            self.edits[act_id] = seq_edit
            self.table.setCellWidget(row, 2, seq_edit)

            row += 1

    def _filter_table(self, query: str) -> None:
        query = query.strip().lower()
        for row in range(self.table.rowCount()):
            name_text = self.table.item(row, 0).text().lower()
            cat_text = self.table.item(row, 1).text().lower()
            match = (not query) or (query in name_text) or (query in cat_text)
            self.table.setRowHidden(row, not match)

    def _reset_to_defaults(self) -> None:
        for act_id, info in DEFAULT_SHORTCUTS.items():
            if act_id in self.edits:
                self.edits[act_id].setKeySequence(QKeySequence(info["default"]))

    def _on_accept(self) -> None:
        result = {}
        for act_id, edit in self.edits.items():
            seq_str = edit.keySequence().toString()
            result[act_id] = seq_str
        save_shortcuts(result)
        self.accept()

    def get_shortcuts(self) -> Dict[str, str]:
        result = {}
        for act_id, edit in self.edits.items():
            seq_str = edit.keySequence().toString()
            result[act_id] = seq_str
        return result
