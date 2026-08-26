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
from coopixel.tools.crop import CropTool
from coopixel.tools.drawing import BucketFillTool, DrawTool, EraserTool, PencilTool
from coopixel.tools.move import MoveTool
from coopixel.tools.pen import PenTool
from coopixel.tools.picker import ColorPickerTool
from coopixel.tools.selection import SelectionTool
from coopixel.tools.shapes import CircleTool, LineTool, RectangleTool


def _vline() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.VLine)
    sep.setStyleSheet("color: #333333;")
    return sep


def _tool_btn(icon_label: str, tooltip: str) -> QToolButton:
    btn = QToolButton()
    btn.setText(icon_label)
    btn.setToolTip(tooltip)
    btn.setCheckable(True)
    btn.setStyleSheet(
        "QToolButton { background: #282828; border: 1px solid #333333; border-radius: 4px; padding: 4px 7px; font-size: 13px; color: #F1F5F9; }"
        "QToolButton:checked { background: #2E2620; border-color: #F97316; color: #F97316; }"
        "QToolButton:hover { background: #332B25; border-color: #F97316; }"
    )
    return btn


class ToolPanel(QFrame):
    tool_selected = Signal(Tool)
    brush_size_changed = Signal(int)
    shape_filled_changed = Signal(bool)
    crop_commit_requested = Signal()
    crop_cancel_requested = Signal()
    crop_fit_sel_requested = Signal()
    crop_fit_content_requested = Signal()
    # Emitted when user edits W or H spinboxes in the crop context panel
    crop_wh_changed = Signal(int, int)
    selection_cleared = Signal()
    move_nudge_requested = Signal(int, int)
    pen_stroke_requested = Signal()
    pen_fill_requested = Signal()
    pen_new_path_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #202020; border-bottom: 1px solid #333333;")

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
        self.crop_tool = CropTool()
        self.move_tool = MoveTool()
        self.draw_tool = DrawTool()
        self.pen_tool = PenTool()

        self.tools: Dict[str, Tool] = {
            "crop": self.crop_tool,
            "move": self.move_tool,
            "selection": self.selection_tool,
            "draw": self.draw_tool,
            "pencil": self.draw_tool,
            "eraser": EraserTool(),
            "picker": ColorPickerTool(),
            "fill": self.fill_tool,
            "pen": self.pen_tool,
        }

        tool_defs = [
            ("move",      "🖐️", "Move Tool (V)"),
            ("selection", "🔲", "Selection Tool (S)"),
            ("draw",      "✏️", "Draw Tool (D)"),
            ("pen",       "🖋️", "Pen Tool (P): Vector paths & Bezier curves"),
            ("eraser",    "🧹", "Eraser Tool (E)"),
            ("picker",    "🧪", "Color Picker (I)"),
            ("fill",      "🪣", "Bucket Fill Tool (F)"),
            ("crop",      "✂️", "Crop Tool (K)"),
        ]


        self._tool_order = [k for k, _, _ in tool_defs]

        for tool_key, icon, tip in tool_defs:
            tool_obj = self.tools[tool_key]
            btn = _tool_btn(icon, tip)
            if tool_key == "selection":
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

        # Page 0 — Draw Modes (Pencil / Line / Rectangle / Circle)
        draw_widget = QWidget()
        draw_layout = QHBoxLayout(draw_widget)
        draw_layout.setContentsMargins(0, 0, 0, 0)
        draw_layout.setSpacing(4)
        draw_lbl = QLabel("Draw:")
        draw_lbl.setStyleSheet("color: #94A3B8; font-weight: 500;")
        draw_layout.addWidget(draw_lbl)

        self.draw_mode_group = QButtonGroup(self)
        self.draw_mode_group.setExclusive(True)
        draw_modes = [
            (DrawTool.PENCIL,    "✏️", "Pencil / Freehand Drawing"),
            (DrawTool.LINE,      "📏", "Line Tool: Drag to draw a straight line"),
            (DrawTool.RECTANGLE, "⬜", "Rectangle Tool: Drag to draw a box"),
            (DrawTool.CIRCLE,    "⭕", "Circle Tool: Drag to draw an ellipse"),
        ]
        self._draw_mode_btns = {}
        for mode_key, icon, tip in draw_modes:
            b = _tool_btn(icon, tip)
            if mode_key == DrawTool.PENCIL:
                b.setChecked(True)
            self.draw_mode_group.addButton(b)
            self._draw_mode_btns[mode_key] = b
            draw_layout.addWidget(b)
            b.clicked.connect(lambda _chk, mk=mode_key: self._on_draw_mode(mk))

        draw_layout.addStretch(1)
        self.ctx_stack.addWidget(draw_widget)

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
            (SelectionTool.BOX,         "⬜", "Box Selection: Drag to select a rectangle"),
            (SelectionTool.DRAW,        "✏️", "Draw Selection: Paint pixels in/out of selection"),
            (SelectionTool.CIRCLE,      "⭕", "Circle Selection: Drag to select an ellipse"),
            (SelectionTool.FILL_CONTIG, "🪣", "Contiguous Selection: Select connected same-color region"),
            (SelectionTool.FILL_GLOBAL, "🌐", "Global Selection: Select all matching color pixels"),
        ]
        for mode_key, icon, tip in sel_modes:
            b = _tool_btn(icon, tip)
            if mode_key == SelectionTool.BOX:
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

        # Page 3 — Crop Options
        crop_widget = QWidget()
        crop_layout = QHBoxLayout(crop_widget)
        crop_layout.setContentsMargins(0, 0, 0, 0)
        crop_layout.setSpacing(6)

        crop_lbl = QLabel("Crop:")
        crop_lbl.setStyleSheet("color: #F97316; font-weight: bold;")
        crop_layout.addWidget(crop_lbl)

        commit_btn = QPushButton("✔️ Commit Crop")
        commit_btn.setToolTip("Commit crop to current box (Enter)")
        commit_btn.setStyleSheet(
            "QPushButton { background: #166534; border: 1px solid #22C55E; color: #FFFFFF; font-weight: bold; padding: 4px 8px; border-radius: 4px; }"
            "QPushButton:hover { background: #15803D; }"
        )
        commit_btn.clicked.connect(self.crop_commit_requested.emit)
        crop_layout.addWidget(commit_btn)

        cancel_btn = QPushButton("✕ Reset Box")
        cancel_btn.setToolTip("Clear crop box (Esc)")
        cancel_btn.setStyleSheet(
            "QPushButton { background: #374151; border: 1px solid #4B5563; color: #F3F4F6; padding: 4px 8px; border-radius: 4px; }"
            "QPushButton:hover { background: #4B5563; }"
        )
        cancel_btn.clicked.connect(self.crop_cancel_requested.emit)
        crop_layout.addWidget(cancel_btn)

        fit_sel_btn = QPushButton("Fit Selection")
        fit_sel_btn.setToolTip("Set crop box to active selection bounds")
        fit_sel_btn.setStyleSheet(
            "QPushButton { background: #1E293B; border: 1px solid #334155; color: #94A3B8; padding: 4px 8px; border-radius: 4px; }"
            "QPushButton:hover { background: #334155; color: #F8FAFC; }"
        )
        fit_sel_btn.clicked.connect(self.crop_fit_sel_requested.emit)
        crop_layout.addWidget(fit_sel_btn)

        fit_content_btn = QPushButton("Fit Content")
        fit_content_btn.setToolTip("Set crop box to non-transparent pixel content bounds")
        fit_content_btn.setStyleSheet(
            "QPushButton { background: #1E293B; border: 1px solid #334155; color: #94A3B8; padding: 4px 8px; border-radius: 4px; }"
            "QPushButton:hover { background: #334155; color: #F8FAFC; }"
        )
        fit_content_btn.clicked.connect(self.crop_fit_content_requested.emit)
        crop_layout.addWidget(fit_content_btn)

        # W / H spinboxes for precise numeric editing
        crop_layout.addWidget(_vline())

        w_lbl = QLabel("W:")
        w_lbl.setStyleSheet("color: #94A3B8;")
        crop_layout.addWidget(w_lbl)
        self.crop_w_spin = QSpinBox()
        self.crop_w_spin.setRange(1, 32767)
        self.crop_w_spin.setValue(1)
        self.crop_w_spin.setSuffix(" px")
        self.crop_w_spin.setToolTip("Crop box width (edit to resize)")
        self.crop_w_spin.setStyleSheet(
            "QSpinBox { background: #1E293B; border: 1px solid #334155; color: #F8FAFC; "
            "padding: 2px 4px; border-radius: 3px; min-width: 68px; }"
        )
        crop_layout.addWidget(self.crop_w_spin)

        h_lbl = QLabel("H:")
        h_lbl.setStyleSheet("color: #94A3B8;")
        crop_layout.addWidget(h_lbl)
        self.crop_h_spin = QSpinBox()
        self.crop_h_spin.setRange(1, 32767)
        self.crop_h_spin.setValue(1)
        self.crop_h_spin.setSuffix(" px")
        self.crop_h_spin.setToolTip("Crop box height (edit to resize)")
        self.crop_h_spin.setStyleSheet(
            "QSpinBox { background: #1E293B; border: 1px solid #334155; color: #F8FAFC; "
            "padding: 2px 4px; border-radius: 3px; min-width: 68px; }"
        )
        crop_layout.addWidget(self.crop_h_spin)

        # Wire spinboxes — both emit crop_wh_changed together
        self.crop_w_spin.valueChanged.connect(self._on_crop_spin_changed)
        self.crop_h_spin.valueChanged.connect(self._on_crop_spin_changed)

        crop_layout.addStretch(1)
        self.ctx_stack.addWidget(crop_widget)


        # Page 4 — Move Tool Sub-toolbar (Nudge buttons: Left, Right, Up, Down)
        move_widget = QWidget()
        move_layout = QHBoxLayout(move_widget)
        move_layout.setContentsMargins(0, 0, 0, 0)
        move_layout.setSpacing(4)

        nudge_label = QLabel("Nudge:")
        nudge_label.setStyleSheet("color: #94A3B8; font-weight: 500; font-size: 10px;")
        move_layout.addWidget(nudge_label)

        nudge_btns = [
            ("←", -1, 0, "Nudge Left 1px"),
            ("→", 1, 0, "Nudge Right 1px"),
            ("↑", 0, -1, "Nudge Up 1px"),
            ("↓", 0, 1, "Nudge Down 1px"),
        ]
        for symbol, dx, dy, tip in nudge_btns:
            nb = QPushButton(symbol)
            nb.setToolTip(tip)
            nb.setFixedSize(24, 24)
            nb.setStyleSheet(
                "QPushButton { background: #1E293B; border: 1px solid #334155; color: #F8FAFC; font-weight: bold; border-radius: 4px; }"
                "QPushButton:hover { background: #334155; border-color: #38BDF8; color: #38BDF8; }"
            )
            nb.clicked.connect(lambda _chk, x=dx, y=dy: self.move_nudge_requested.emit(x, y))
            move_layout.addWidget(nb)

        move_layout.addStretch(1)
        self.ctx_stack.addWidget(move_widget)

        # Page 5 — Pen Tool Modes
        pen_widget = QWidget()
        pen_layout = QHBoxLayout(pen_widget)
        pen_layout.setContentsMargins(0, 0, 0, 0)
        pen_layout.setSpacing(4)
        pen_lbl = QLabel("Pen Tool:")
        pen_lbl.setStyleSheet("color: #94A3B8; font-weight: 500;")
        pen_layout.addWidget(pen_lbl)

        btn_new_p = QToolButton()
        btn_new_p.setText("+ New Path")
        btn_new_p.setToolTip("Create new vector path")
        btn_new_p.setStyleSheet("QToolButton { background: #282828; color: #F1F5F9; border: 1px solid #333333; border-radius: 4px; padding: 3px 8px; font-size: 11px; } QToolButton:hover { background: #C25E00; }")
        btn_new_p.clicked.connect(self.pen_new_path_requested.emit)

        btn_stroke_p = QToolButton()
        btn_stroke_p.setText("🖌️ Stroke Path")
        btn_stroke_p.setToolTip("Rasterize active path outline onto active layer")
        btn_stroke_p.setStyleSheet("QToolButton { background: #282828; color: #F1F5F9; border: 1px solid #333333; border-radius: 4px; padding: 3px 8px; font-size: 11px; } QToolButton:hover { background: #C25E00; }")
        btn_stroke_p.clicked.connect(self.pen_stroke_requested.emit)

        btn_fill_p = QToolButton()
        btn_fill_p.setText("🎨 Fill Path")
        btn_fill_p.setToolTip("Rasterize active path interior onto active layer")
        btn_fill_p.setStyleSheet("QToolButton { background: #282828; color: #F1F5F9; border: 1px solid #333333; border-radius: 4px; padding: 3px 8px; font-size: 11px; } QToolButton:hover { background: #C25E00; }")
        btn_fill_p.clicked.connect(self.pen_fill_requested.emit)

        pen_layout.addWidget(btn_new_p)
        pen_layout.addWidget(btn_stroke_p)
        pen_layout.addWidget(btn_fill_p)
        pen_layout.addStretch(1)
        self.ctx_stack.addWidget(pen_widget)

        # Page 6 — Empty spacer for tools with no extra context options
        self.ctx_stack.addWidget(QWidget())
        main_layout.addWidget(self.ctx_stack, stretch=1)

        # Shared reference to the canvas selection (set later by MainWindow)
        self._canvas_selection = None

        # Start on selection tool by default
        self.select_tool_by_key("selection")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_canvas_selection(self, sel):
        """Link the shared SelectionModel from the canvas."""
        self._canvas_selection = sel
        self.selection_tool.selection = sel

    def select_tool_by_key(self, tool_key: str) -> None:
        actual_key = tool_key
        if tool_key in ("draw", "pencil"):
            self.draw_tool.mode = DrawTool.PENCIL
            self._update_draw_mode_buttons()
            actual_key = "draw"
        elif tool_key == "line":
            self.draw_tool.mode = DrawTool.LINE
            self._update_draw_mode_buttons()
            actual_key = "draw"
        elif tool_key == "rectangle":
            self.draw_tool.mode = DrawTool.RECTANGLE
            self._update_draw_mode_buttons()
            actual_key = "draw"
        elif tool_key == "circle":
            self.draw_tool.mode = DrawTool.CIRCLE
            self._update_draw_mode_buttons()
            actual_key = "draw"

        if actual_key not in self.tools:
            return

        tool = self.tools[actual_key]
        idx = self._tool_order.index(actual_key) if actual_key in self._tool_order else -1
        if idx >= 0:
            btns = self.btn_group.buttons()
            if 0 <= idx < len(btns):
                btns[idx].setChecked(True)
        self._on_tool_clicked(tool, actual_key)


    def _on_tool_clicked(self, tool: Tool, key: str) -> None:
        if key in ("draw", "pencil"):
            self.ctx_stack.setCurrentIndex(0)
        elif key == "selection":
            self.ctx_stack.setCurrentIndex(1)
        elif key == "fill":
            self.ctx_stack.setCurrentIndex(2)
        elif key == "crop":
            self.ctx_stack.setCurrentIndex(3)
        elif key == "move":
            self.ctx_stack.setCurrentIndex(4)
        elif key == "pen":
            self.ctx_stack.setCurrentIndex(5)
        else:
            self.ctx_stack.setCurrentIndex(6)
        self.tool_selected.emit(tool)


    def _on_draw_mode(self, mode: str) -> None:
        self.draw_tool.mode = mode

    def _update_draw_mode_buttons(self) -> None:
        if hasattr(self, "_draw_mode_btns") and self.draw_tool.mode in self._draw_mode_btns:
            self._draw_mode_btns[self.draw_tool.mode].setChecked(True)

    def _on_sel_mode(self, mode: str) -> None:
        self.selection_tool.mode = mode

    def _on_fill_mode(self, mode: str) -> None:
        self.fill_tool.fill_mode = mode

    def _on_crop_spin_changed(self) -> None:
        """Emitted when the user edits W or H spinboxes directly."""
        self.crop_wh_changed.emit(self.crop_w_spin.value(), self.crop_h_spin.value())

    def update_crop_box_ui(self, x: int, y: int, w: int, h: int) -> None:
        """Called by MainWindow when the canvas crop box changes (drag or Fit buttons)."""
        # Block signals to avoid triggering crop_wh_changed during programmatic update
        self.crop_w_spin.blockSignals(True)
        self.crop_h_spin.blockSignals(True)
        self.crop_w_spin.setValue(w)
        self.crop_h_spin.setValue(h)
        self.crop_w_spin.blockSignals(False)
        self.crop_h_spin.blockSignals(False)

    def _on_clear_selection(self) -> None:
        if self._canvas_selection is not None:
            was_not_empty = not self._canvas_selection.is_empty()
            self._canvas_selection.clear()
            if was_not_empty:
                self.selection_cleared.emit()
        if self.parent():
            canvas = getattr(self.parent(), "canvas", None)
            if canvas:
                canvas.update()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape and self._canvas_selection:
            was_not_empty = not self._canvas_selection.is_empty()
            self._canvas_selection.clear()
            if was_not_empty:
                self.selection_cleared.emit()
            if self.parent():
                canvas = getattr(self.parent(), "canvas", None)
                if canvas:
                    canvas.update()
        super().keyPressEvent(event)
