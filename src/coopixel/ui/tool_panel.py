"""
Tool selection toolbar for Coopixel.
Shows icon-only tool buttons and context-sensitive mode options with informative tooltips.
"""

from typing import Dict, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QToolButton,
    QWidget,
)
from coopixel.tools.base import Tool
from coopixel.tools.drawing import BucketFillTool, EraserTool, PencilTool
from coopixel.tools.picker import ColorPickerTool
from coopixel.tools.selection import SelectionTool
from coopixel.tools.shapes import CircleTool, LineTool, RectangleTool


def _vline() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.VLine)
    sep.setStyleSheet("color: #2D3748;")
    return sep


def _tool_btn(icon_label: str, tooltip: str) -> QToolButton:
    btn = QToolButton()
    btn.setText(icon_label)
    btn.setToolTip(tooltip)
    btn.setCheckable(True)
    btn.setStyleSheet(
        "QToolButton { background: #1E2330; border: 1px solid #2D3748; border-radius: 4px; padding: 4px 7px; font-size: 14px; color: #F1F5F9; }"
        "QToolButton:checked { background: #2563EB; border-color: #3B82F6; color: #FFFFFF; }"
        "QToolButton:hover { background: #263352; }"
    )
    return btn


class ToolPanel(QFrame):
    tool_selected = Signal(Tool)
    brush_size_changed = Signal(int)
    shape_filled_changed = Signal(bool)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #1A1D24; border-bottom: 1px solid #2D3748;")

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 4)
        main_layout.setSpacing(8)

        # ---- Tool Buttons ----
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        tools_layout = QHBoxLayout()
        tools_layout.setSpacing(4)

        self.selection_tool = SelectionTool()
        self.fill_tool = BucketFillTool()

        self.tools: Dict[str, Tool] = {
            "selection": self.selection_tool,
            "pencil": PencilTool(),
            "eraser": EraserTool(),
            "picker": ColorPickerTool(),
            "fill": self.fill_tool,
            "line": LineTool(),
            "rectangle": RectangleTool(),
            "circle": CircleTool(),
        }

        tool_defs = [
            ("selection", "🔲", "Selection Tool (S)"),
            ("pencil",    "✏️", "Pencil Tool (P)"),
            ("eraser",    "🧹", "Eraser Tool (E)"),
            ("picker",    "🧪", "Color Picker (I)"),
            ("fill",      "🪣", "Bucket Fill Tool (F)"),
            ("line",      "📏", "Line Tool (L)"),
            ("rectangle", "⬜", "Rectangle Tool (R)"),
            ("circle",    "⭕", "Circle Tool (C)"),
        ]
        self._tool_order = [k for k, _, _ in tool_defs]

        for tool_key, icon, tip in tool_defs:
            tool_obj = self.tools[tool_key]
            btn = _tool_btn(icon, tip)
            if tool_key == "pencil":
                btn.setChecked(True)
            self.btn_group.addButton(btn)
            tools_layout.addWidget(btn)
            btn.clicked.connect(lambda _checked, t=tool_obj, k=tool_key: self._on_tool_clicked(t, k))

        main_layout.addLayout(tools_layout)
        main_layout.addWidget(_vline())

        # ---- Brush Size ----
        size_lbl = QLabel("Size:")
        size_lbl.setStyleSheet("color: #94A3B8; font-weight: 500;")
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 32)
        self.size_spin.setValue(1)
        self.size_spin.setSuffix(" px")
        self.size_spin.valueChanged.connect(self.brush_size_changed.emit)
        main_layout.addWidget(size_lbl)
        main_layout.addWidget(self.size_spin)

        # ---- Filled Shape Toggle ----
        self.fill_cb = QCheckBox("Filled")
        self.fill_cb.setStyleSheet("color: #94A3B8;")
        self.fill_cb.toggled.connect(self.shape_filled_changed.emit)
        main_layout.addWidget(self.fill_cb)

        main_layout.addWidget(_vline())

        # ---- Context Options Stacked Widget ----
        self.ctx_stack = QStackedWidget()

        # Page 0 — Empty (Pencil / Eraser / Picker)
        self.ctx_stack.addWidget(QWidget())

        # Page 1 — Selection Modes
        sel_widget = QWidget()
        sel_layout = QHBoxLayout(sel_widget)
        sel_layout.setContentsMargins(0, 0, 0, 0)
        sel_layout.setSpacing(4)
        sel_lbl = QLabel("Selection:")
        sel_lbl.setStyleSheet("color: #94A3B8; font-weight: 500;")
        sel_layout.addWidget(sel_lbl)

        self.sel_mode_group = QButtonGroup(self)
        self.sel_mode_group.setExclusive(True)
        sel_modes = [
            (SelectionTool.DRAW,        "✏️", "Draw Selection: Paint pixels in/out of selection"),
            (SelectionTool.BOX,         "⬜", "Box Selection: Drag to select a rectangle"),
            (SelectionTool.CIRCLE,      "⭕", "Circle Selection: Drag to select an ellipse"),
            (SelectionTool.FILL_CONTIG, "🪣", "Contiguous Selection: Select connected same-color region"),
            (SelectionTool.FILL_GLOBAL, "🌐", "Global Selection: Select all matching color pixels"),
        ]
        for mode_key, icon, tip in sel_modes:
            b = _tool_btn(icon, tip)
            if mode_key == SelectionTool.DRAW:
                b.setChecked(True)
            self.sel_mode_group.addButton(b)
            sel_layout.addWidget(b)
            b.clicked.connect(lambda _chk, mk=mode_key: self._on_sel_mode(mk))

        sel_layout.addWidget(_vline())
        clear_sel_btn = QToolButton()
        clear_sel_btn.setText("✕")
        clear_sel_btn.setToolTip("Clear Selection / Deselect all (Escape)")
        clear_sel_btn.setStyleSheet(
            "QToolButton { background: #1E2330; border: 1px solid #2D3748; border-radius: 4px; padding: 4px 7px; font-size: 14px; color: #EF4444; }"
            "QToolButton:hover { background: #3B1D24; color: #FCA5A5; }"
        )
        clear_sel_btn.clicked.connect(self._on_clear_selection)
        self.clear_sel_btn = clear_sel_btn
        sel_layout.addWidget(clear_sel_btn)
        sel_layout.addStretch(1)
        self.ctx_stack.addWidget(sel_widget)

        # Page 2 — Fill Modes
        fill_widget = QWidget()
        fill_layout = QHBoxLayout(fill_widget)
        fill_layout.setContentsMargins(0, 0, 0, 0)
        fill_layout.setSpacing(4)
        fill_lbl = QLabel("Fill:")
        fill_lbl.setStyleSheet("color: #94A3B8; font-weight: 500;")
        fill_layout.addWidget(fill_lbl)

        self.fill_mode_group = QButtonGroup(self)
        self.fill_mode_group.setExclusive(True)
        fill_modes = [
            (BucketFillTool.CONTIGUOUS, "🪣", "Contiguous Fill: Flood fill connected same-color pixels"),
            (BucketFillTool.GLOBAL,     "🌐", "Global Fill: Fill all matching color pixels across layer"),
        ]
        for mode_key, icon, tip in fill_modes:
            b = _tool_btn(icon, tip)
            if mode_key == BucketFillTool.CONTIGUOUS:
                b.setChecked(True)
            self.fill_mode_group.addButton(b)
            fill_layout.addWidget(b)
            b.clicked.connect(lambda _chk, mk=mode_key: self._on_fill_mode(mk))

        fill_layout.addStretch(1)
        self.ctx_stack.addWidget(fill_widget)

        main_layout.addWidget(self.ctx_stack)
        main_layout.addStretch(1)

        # Shared reference to the canvas selection (set later by MainWindow)
        self._canvas_selection = None

        # Start on pencil context
        self.ctx_stack.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_canvas_selection(self, sel):
        """Link the shared SelectionModel from the canvas."""
        self._canvas_selection = sel
        self.selection_tool.selection = sel

    def select_tool_by_key(self, tool_key: str) -> None:
        if tool_key not in self.tools:
            return
        tool = self.tools[tool_key]
        idx = self._tool_order.index(tool_key) if tool_key in self._tool_order else -1
        if idx >= 0:
            btns = self.btn_group.buttons()
            if 0 <= idx < len(btns):
                btns[idx].setChecked(True)
        self._on_tool_clicked(tool, tool_key)

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_tool_clicked(self, tool: Tool, key: str) -> None:
        if key == "selection":
            self.ctx_stack.setCurrentIndex(1)
        elif key == "fill":
            self.ctx_stack.setCurrentIndex(2)
        else:
            self.ctx_stack.setCurrentIndex(0)
        self.tool_selected.emit(tool)

    def _on_sel_mode(self, mode: str) -> None:
        self.selection_tool.mode = mode

    def _on_fill_mode(self, mode: str) -> None:
        self.fill_tool.fill_mode = mode

    def _on_clear_selection(self) -> None:
        if self._canvas_selection is not None:
            self._canvas_selection.clear()
        if self.parent():
            canvas = getattr(self.parent(), "canvas", None)
            if canvas:
                canvas.update()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape and self._canvas_selection:
            self._canvas_selection.clear()
            if self.parent():
                canvas = getattr(self.parent(), "canvas", None)
                if canvas:
                    canvas.update()
        super().keyPressEvent(event)
