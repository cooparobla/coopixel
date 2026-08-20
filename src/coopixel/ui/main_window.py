"""
Main Window for Coopixel Pixel Art Editor.
Integrates dark theme, standard photo editor menu bar, tool toolbar, canvas viewport, dock panels, and layer effects.
"""

import os
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QImage, QKeySequence, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QStatusBar,
    QToolBar,
    QToolButton,
    QWidget,
)
from coopixel.models.document import PixelDocument, hex_to_qcolor
from coopixel.models.history import HistoryStack
from coopixel.ui.animation_panel import AnimationPanel
from coopixel.ui.appearance_panel import AppearancePanel
from coopixel.ui.canvas import CanvasWidget
from coopixel.ui.color_panel import ColorPanel
from coopixel.ui.dialogs import AboutDialog, CanvasSizeDialog, NewCanvasDialog
from coopixel.ui.layer_panel import LayerPanel
from coopixel.ui.tool_panel import ToolPanel


class MainWindow(QMainWindow):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Coopixel - Pixel Art Editor")
        self.resize(1280, 820)

        # ---- Document & History ----
        self.doc: PixelDocument = PixelDocument(32, 32)
        self.history: HistoryStack = HistoryStack(max_depth=50)
        self.history.push(self.doc.to_dict())   # Initial snapshot

        # ---- Canvas (Central Widget) ----
        self.canvas = CanvasWidget(self.doc)
        self.canvas.cursor_moved.connect(self.update_status_bar)
        # stroke_committed = full stroke done → push history snapshot
        self.canvas.stroke_committed.connect(self.on_stroke_committed)
        # canvas_updated = live repaint during stroke (no history)
        self.canvas.canvas_updated.connect(self.canvas.update)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #121417; }")
        scroll_area.setWidget(self.canvas)
        self.setCentralWidget(scroll_area)

        # ---- Tool Options Bar (top toolbar) ----
        self.tool_panel = ToolPanel(self)
        tb = self._wrap_in_toolbar("Tool Options", self.tool_panel)
        self.addToolBar(Qt.TopToolBarArea, tb)

        self.tool_panel.tool_selected.connect(self.on_tool_selected)
        self.tool_panel.brush_size_changed.connect(self.on_brush_size_changed)
        self.tool_panel.shape_filled_changed.connect(self.on_shape_filled_changed)

        # Set default tool to Pencil
        self.canvas.active_tool = self.tool_panel.tools["pencil"]

        # Wire Color Picker callback
        self.tool_panel.tools["picker"].on_color_picked = self.on_color_picked_from_canvas

        # Link shared SelectionModel between canvas and tool panel
        self.tool_panel.set_canvas_selection(self.canvas.selection)

        # ---- Left-side Dock Panels ----
        # Layer panel first (top of left side)
        self.layer_panel = LayerPanel(self.doc, self)
        self.layer_panel.layer_structure_changed.connect(self.on_layer_structure_changed)
        self.layer_panel.layer_visual_changed.connect(self.on_layer_visual_changed)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.layer_panel)

        # Color panel below layers
        self.color_panel = ColorPanel(self)
        self.color_panel.primary_color_changed.connect(self.on_primary_color_changed)
        self.color_panel.secondary_color_changed.connect(self.on_secondary_color_changed)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.color_panel)

        # Stack them vertically (layer panel above color panel)
        self.splitDockWidget(self.layer_panel, self.color_panel, Qt.Vertical)

        # ---- Right-side Dock Panels ----
        self.appearance_panel = AppearancePanel(self.doc, self)
        self.appearance_panel.effect_changed.connect(self.on_layer_structure_changed)
        self.addDockWidget(Qt.RightDockWidgetArea, self.appearance_panel)
        self.appearance_panel.hide()

        # ---- Bottom Dock Panels ----
        self.animation_panel = AnimationPanel(self.doc, self)
        self.animation_panel.animation_structure_changed.connect(self.on_frame_structure_changed)
        self.animation_panel.frame_structure_changed.connect(self.on_frame_structure_changed)
        self.animation_panel.active_frame_changed.connect(self.on_active_frame_changed)
        self.animation_panel.animation_visual_changed.connect(self.canvas.update)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.animation_panel)
        self.animation_panel.hide()

        # Sync initial colors
        self.canvas.primary_color = self.color_panel.primary_color
        self.canvas.secondary_color = self.color_panel.secondary_color

        # ---- Right-hand Vertical Icon Toolbar ----
        self._build_right_sidebar_toolbar()

        # ---- Status Bar ----
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # ---- Menu Bar ----
        self._build_menu_bar()
        self.update_status_bar(0, 0)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _wrap_in_toolbar(self, name: str, widget: QWidget) -> QToolBar:
        tb = QToolBar(name, self)
        tb.setMovable(False)
        tb.addWidget(widget)
        return tb

    def _build_right_sidebar_toolbar(self) -> None:
        """Icon-only vertical toolbar on the right side of drawing area for Appearance panel toggle."""
        right_tb = QToolBar("Sidebar", self)
        right_tb.setMovable(False)
        right_tb.setOrientation(Qt.Vertical)
        right_tb.setStyleSheet(
            "QToolBar { background-color: #1A1D24; border-left: 1px solid #2D3748; spacing: 4px; padding: 4px; }"
            "QToolButton { background: #1E2330; border: 1px solid #2D3748; border-radius: 4px; padding: 4px 7px; font-size: 14px; color: #F1F5F9; }"
            "QToolButton:hover { background: #263352; }"
            "QToolButton:checked { background: #2563EB; border-color: #3B82F6; color: #FFFFFF; }"
        )

        app_act = QAction("✨", self)
        app_act.setToolTip("Appearance & Layer Effects")
        app_act.setCheckable(True)
        app_act.setChecked(self.appearance_panel.isVisible())
        app_act.toggled.connect(self.appearance_panel.setVisible)
        self.appearance_panel.visibilityChanged.connect(app_act.setChecked)

        anim_act = QAction("🎬", self)
        anim_act.setToolTip("Animation Timeline")
        anim_act.setCheckable(True)
        anim_act.setChecked(self.animation_panel.isVisible())
        anim_act.toggled.connect(self.animation_panel.setVisible)
        self.animation_panel.visibilityChanged.connect(anim_act.setChecked)

        right_tb.addAction(app_act)
        right_tb.addAction(anim_act)
        self.addToolBar(Qt.RightToolBarArea, right_tb)





    def _build_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        # ---- FILE ----
        file_menu = menu_bar.addMenu("&File")

        new_act = QAction("&New...", self)
        new_act.setShortcut(QKeySequence.New)
        new_act.triggered.connect(self.on_file_new)
        file_menu.addAction(new_act)

        open_act = QAction("&Open (.pix / .caml)...", self)
        open_act.setShortcut(QKeySequence.Open)
        open_act.triggered.connect(self.on_file_open)
        file_menu.addAction(open_act)

        save_act = QAction("&Save (.pix)", self)
        save_act.setShortcut(QKeySequence.Save)
        save_act.triggered.connect(self.on_file_save)
        file_menu.addAction(save_act)

        save_as_act = QAction("Save &As...", self)
        save_as_act.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_act.triggered.connect(self.on_file_save_as)
        file_menu.addAction(save_as_act)

        file_menu.addSeparator()

        import_act = QAction("&Import Image as Layer...", self)
        import_act.setShortcut(QKeySequence("Ctrl+Shift+I"))
        import_act.triggered.connect(self.on_file_import_png)
        file_menu.addAction(import_act)

        export_act = QAction("&Export PNG...", self)
        export_act.setShortcut(QKeySequence("Ctrl+E"))
        export_act.triggered.connect(self.on_file_export_png)
        file_menu.addAction(export_act)

        file_menu.addSeparator()

        exit_act = QAction("E&xit", self)
        exit_act.setShortcut(QKeySequence.Quit)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        # ---- EDIT ----
        edit_menu = menu_bar.addMenu("&Edit")

        self.undo_act = QAction("&Undo", self)
        self.undo_act.setShortcut(QKeySequence.Undo)
        self.undo_act.triggered.connect(self.on_undo)
        edit_menu.addAction(self.undo_act)

        self.redo_act = QAction("&Redo", self)
        self.redo_act.setShortcut(QKeySequence.Redo)
        self.redo_act.triggered.connect(self.on_redo)
        edit_menu.addAction(self.redo_act)

        edit_menu.addSeparator()

        cut_act = QAction("Cu&t", self)
        cut_act.setShortcut(QKeySequence.Cut)
        cut_act.triggered.connect(self.on_cut)
        edit_menu.addAction(cut_act)

        copy_act = QAction("&Copy", self)
        copy_act.setShortcut(QKeySequence.Copy)
        copy_act.triggered.connect(self.on_copy)
        edit_menu.addAction(copy_act)

        paste_act = QAction("&Paste", self)
        paste_act.setShortcut(QKeySequence.Paste)
        paste_act.triggered.connect(self.on_paste)
        edit_menu.addAction(paste_act)

        edit_menu.addSeparator()

        clear_layer_act = QAction("Clear Active Layer", self)
        clear_layer_act.triggered.connect(self.on_clear_active_layer)
        edit_menu.addAction(clear_layer_act)

        canvas_size_act = QAction("Canvas Size...", self)
        canvas_size_act.triggered.connect(self.on_change_canvas_size)
        edit_menu.addAction(canvas_size_act)

        edit_menu.addSeparator()

        sel_all_act = QAction("Select &All", self)
        sel_all_act.setShortcut(QKeySequence("Ctrl+A"))
        sel_all_act.triggered.connect(self.on_select_all)
        edit_menu.addAction(sel_all_act)

        desel_act = QAction("&Deselect", self)
        desel_act.setShortcut(QKeySequence("Escape"))
        desel_act.triggered.connect(self.on_deselect)
        edit_menu.addAction(desel_act)

        invert_sel_act = QAction("&Invert Selection", self)
        invert_sel_act.setShortcut(QKeySequence("Ctrl+I"))
        invert_sel_act.triggered.connect(self.on_invert_selection)
        edit_menu.addAction(invert_sel_act)

        # ---- VIEW ----
        view_menu = menu_bar.addMenu("&View")

        zoom_in_act = QAction("Zoom &In", self)
        zoom_in_act.setShortcut(QKeySequence.ZoomIn)
        zoom_in_act.triggered.connect(self.canvas.zoom_in)
        view_menu.addAction(zoom_in_act)

        zoom_out_act = QAction("Zoom &Out", self)
        zoom_out_act.setShortcut(QKeySequence.ZoomOut)
        zoom_out_act.triggered.connect(self.canvas.zoom_out)
        view_menu.addAction(zoom_out_act)

        reset_zoom_act = QAction("&Reset View (Zoom + Center)", self)
        reset_zoom_act.setShortcut(QKeySequence("Ctrl+0"))
        reset_zoom_act.triggered.connect(self._reset_view)
        view_menu.addAction(reset_zoom_act)

        view_menu.addSeparator()

        grid_act = QAction("Toggle &Grid", self)
        grid_act.setCheckable(True)
        grid_act.setChecked(True)
        grid_act.setShortcut(QKeySequence("Ctrl+G"))
        grid_act.triggered.connect(self.canvas.toggle_grid)
        view_menu.addAction(grid_act)

        view_menu.addSeparator()

        toggle_layers_act = self.layer_panel.toggleViewAction()
        toggle_layers_act.setText("Layers Panel")
        view_menu.addAction(toggle_layers_act)

        toggle_colors_act = self.color_panel.toggleViewAction()
        toggle_colors_act.setText("Color Panel")
        view_menu.addAction(toggle_colors_act)

        toggle_app_act = self.appearance_panel.toggleViewAction()
        toggle_app_act.setText("Appearance & Layer Effects Panel")
        view_menu.addAction(toggle_app_act)

        toggle_anim_act = self.animation_panel.toggleViewAction()
        toggle_anim_act.setText("Animation Timeline Panel")
        view_menu.addAction(toggle_anim_act)

        # ---- LAYER ----
        layer_menu = menu_bar.addMenu("&Layer")

        add_l_act = QAction("&New Layer", self)
        add_l_act.setShortcut(QKeySequence("Ctrl+Shift+N"))
        add_l_act.triggered.connect(self.layer_panel.on_add_layer)
        layer_menu.addAction(add_l_act)

        dup_l_act = QAction("&Duplicate Layer", self)
        dup_l_act.triggered.connect(self.layer_panel.on_duplicate_layer)
        layer_menu.addAction(dup_l_act)

        del_l_act = QAction("&Delete Layer", self)
        del_l_act.triggered.connect(self.layer_panel.on_delete_layer)
        layer_menu.addAction(del_l_act)

        layer_menu.addSeparator()

        copy_l_act = QAction("Cop&y Layer", self)
        copy_l_act.setShortcut(QKeySequence("Ctrl+Shift+C"))
        copy_l_act.triggered.connect(self.layer_panel.on_copy_layer)
        layer_menu.addAction(copy_l_act)

        paste_l_act = QAction("Pas&te Layer", self)
        paste_l_act.setShortcut(QKeySequence("Ctrl+Shift+V"))
        paste_l_act.triggered.connect(self.layer_panel.on_paste_layer)
        layer_menu.addAction(paste_l_act)

        layer_menu.addSeparator()

        move_up_act = QAction("Move Layer &Up", self)
        move_up_act.triggered.connect(self.layer_panel.on_move_up)
        layer_menu.addAction(move_up_act)

        move_down_act = QAction("Move Layer &Down", self)
        move_down_act.triggered.connect(self.layer_panel.on_move_down)
        layer_menu.addAction(move_down_act)

        # ---- TOOLS ----
        tools_menu = menu_bar.addMenu("&Tools")
        tools_menu.addAction("Selection Tool (S)", lambda: self.tool_panel.select_tool_by_key("selection"))
        tools_menu.addAction("Pencil Tool (P)", lambda: self.tool_panel.select_tool_by_key("pencil"))
        tools_menu.addAction("Eraser Tool (E)", lambda: self.tool_panel.select_tool_by_key("eraser"))
        tools_menu.addAction("Color Picker (I)", lambda: self.tool_panel.select_tool_by_key("picker"))
        tools_menu.addAction("Bucket Fill (F)", lambda: self.tool_panel.select_tool_by_key("fill"))
        tools_menu.addAction("Line Tool (L)", lambda: self.tool_panel.select_tool_by_key("line"))
        tools_menu.addAction("Rectangle Tool (R)", lambda: self.tool_panel.select_tool_by_key("rectangle"))
        tools_menu.addAction("Circle Tool (C)", lambda: self.tool_panel.select_tool_by_key("circle"))

        # ---- HELP ----
        help_menu = menu_bar.addMenu("&Help")
        about_act = QAction("&About Coopixel", self)
        about_act.triggered.connect(self.on_about)
        help_menu.addAction(about_act)

    # ------------------------------------------------------------------
    # History helpers
    # ------------------------------------------------------------------

    def _reset_view(self) -> None:
        """Reset zoom to default (16x) and re-center the canvas. Bound to Ctrl+0."""
        self.canvas.zoom_level = 16.0
        self.canvas.center_canvas()
        self.canvas.update()

    def _push_history(self) -> None:
        """Push the current document state to the history stack (history.push deep-copies it)."""
        self.history.push(self.doc.to_dict())

    def _restore_from_dict(self, state: dict) -> None:
        """Restore document from a state dict and update all UI, preserving the current view."""
        filepath = self.doc.filepath
        # Save current view state before swapping the document
        saved_zoom = self.canvas.zoom_level
        saved_pan = self.canvas.pan_offset

        self.doc = PixelDocument.from_dict(state, filepath=filepath)
        # Update canvas doc reference without calling center_canvas()
        self.canvas.doc = self.doc
        self.canvas.zoom_level = saved_zoom
        self.canvas.pan_offset = saved_pan
        self.canvas.update()
        self.layer_panel.set_document(self.doc)
        self.appearance_panel.set_document(self.doc)
        self.animation_panel.set_document(self.doc)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def on_stroke_committed(self) -> None:
        """Called when a drawing stroke completes — pushes history and refreshes panels."""
        self._push_history()
        self.layer_panel.refresh_list()
        self.appearance_panel.refresh_panel()
        self.animation_panel.refresh_timeline()
        self.canvas.update()

    def on_layer_structure_changed(self) -> None:
        """Called when layers/effects are added/deleted/reordered/duplicated — push history."""
        self._push_history()
        self.appearance_panel.refresh_panel()
        self.animation_panel.refresh_timeline()
        self.canvas.update()

    def on_layer_visual_changed(self) -> None:
        """Called when layer visibility/opacity/lock changes — repaint only, no history."""
        self.appearance_panel.refresh_panel()
        self.animation_panel.refresh_timeline()
        self.canvas.update()

    def on_frame_structure_changed(self) -> None:
        """Called when frames are added/deleted/duplicated/reordered — push history."""
        self._push_history()
        self.layer_panel.refresh_list()
        self.appearance_panel.refresh_panel()
        self.canvas.update()

    def on_active_frame_changed(self) -> None:
        """Called when active frame is changed — updates layer panel, appearance panel & canvas."""
        self.layer_panel.refresh_list()
        self.appearance_panel.refresh_panel()
        self.canvas.update()

    def on_undo(self) -> None:
        prev_state = self.history.undo()
        if prev_state is not None:
            self._restore_from_dict(prev_state)
            self.status_bar.showMessage("Undo", 1500)

    def on_redo(self) -> None:
        next_state = self.history.redo()
        if next_state is not None:
            self._restore_from_dict(next_state)
            self.status_bar.showMessage("Redo", 1500)

    # ---- Tool & Color ----

    def on_tool_selected(self, tool) -> None:
        self.canvas.active_tool = tool

    def on_brush_size_changed(self, size: int) -> None:
        self.canvas.brush_size = size

    def on_shape_filled_changed(self, filled: bool) -> None:
        self.canvas.shape_filled = filled

    def on_primary_color_changed(self, color_hex: str) -> None:
        self.canvas.primary_color = color_hex

    def on_secondary_color_changed(self, color_hex: str) -> None:
        self.canvas.secondary_color = color_hex

    def on_color_picked_from_canvas(self, color_hex: str) -> None:
        self.color_panel.set_primary_color(color_hex)
        self.tool_panel.select_tool_by_key("pencil")

    def on_clear_active_layer(self) -> None:
        active = self.doc.active_layer
        if active and not active.locked and active.visible:
            active.clear_all()
            self._push_history()
            self.canvas.update()
            self.layer_panel.refresh_list()
            self.appearance_panel.refresh_panel()

    def on_change_canvas_size(self) -> None:
        dlg = CanvasSizeDialog(self.doc.width, self.doc.height, self)
        if dlg.exec() == CanvasSizeDialog.Accepted:
            nw, nh = dlg.get_values()
            self.doc.width = nw
            self.doc.height = nh
            self._push_history()
            self.canvas.center_canvas()
            self.canvas.update()

    # ---- Selection & Clipboard Actions ----

    def on_select_all(self) -> None:
        self.canvas.selection.select_all(self.doc)
        self.canvas.update()
        self.status_bar.showMessage("Selected entire canvas", 1500)

    def on_deselect(self) -> None:
        self.canvas.selection.clear()
        self.canvas.update()

    def on_invert_selection(self) -> None:
        self.canvas.selection.invert(self.doc)
        self.canvas.update()

    def on_copy(self) -> None:
        """Copies selected pixels (or active layer pixels) to clipboard."""
        active = self.doc.active_layer
        if not active:
            return

        selected_coords = self.canvas.selection.selected
        if not selected_coords:
            # If no selection, copy all pixels of active layer
            target_coords = set()
            for key in active.pixels.keys():
                parts = key.split(",")
                if len(parts) == 2:
                    target_coords.add((int(parts[0]), int(parts[1])))
        else:
            target_coords = set(selected_coords)

        if not target_coords:
            self.status_bar.showMessage("Nothing to copy on active layer", 1500)
            return

        min_x = min(x for x, y in target_coords)
        min_y = min(y for x, y in target_coords)

        clip_pixels = {}
        for x, y in target_coords:
            color = active.get_pixel(x, y)
            if color:
                clip_pixels[(x - min_x, y - min_y)] = color

        self.clipboard_data = {
            "min_x": min_x,
            "min_y": min_y,
            "pixels": clip_pixels,
        }

        # Sync with system clipboard QImage
        if clip_pixels:
            max_rel_x = max(rx for rx, ry in clip_pixels.keys())
            max_rel_y = max(ry for rx, ry in clip_pixels.keys())
            w = max_rel_x + 1
            h = max_rel_y + 1
            img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
            img.fill(QColor(0, 0, 0, 0))
            p = QPainter(img)
            for (rx, ry), hex_str in clip_pixels.items():
                p.setPen(hex_to_qcolor(hex_str))
                p.drawPoint(rx, ry)
            p.end()
            QApplication.clipboard().setImage(img)

        self.status_bar.showMessage(f"Copied {len(clip_pixels)} pixels to clipboard", 2000)

    def on_cut(self) -> None:
        """Cuts selected pixels (or active layer pixels) to clipboard."""
        active = self.doc.active_layer
        if not active or active.locked or not active.visible:
            return

        self.on_copy()
        selected_coords = self.canvas.selection.selected
        if not selected_coords:
            active.clear_all()
        else:
            for x, y in selected_coords:
                active.clear_pixel(x, y)

        self._push_history()
        self.canvas.update()
        self.layer_panel.refresh_list()
        self.appearance_panel.refresh_panel()
        self.animation_panel.refresh_timeline()
        self.status_bar.showMessage("Cut selection", 2000)

    def on_paste(self) -> None:
        """Pastes clipboard pixels onto the current active layer."""
        active = self.doc.active_layer
        if not active or active.locked or not active.visible:
            self.status_bar.showMessage("Cannot paste on locked/hidden layer", 2000)
            return

        pasted_coords = []

        # Check internal clipboard first
        if hasattr(self, "clipboard_data") and self.clipboard_data and "pixels" in self.clipboard_data:
            min_x = self.clipboard_data.get("min_x", 0)
            min_y = self.clipboard_data.get("min_y", 0)
            clip_pixels = self.clipboard_data.get("pixels", {})

            for (rx, ry), hex_color in clip_pixels.items():
                tx = min_x + rx
                ty = min_y + ry
                if self.doc.is_valid_coord(tx, ty):
                    active.set_pixel(tx, ty, hex_color)
                    pasted_coords.append((tx, ty))
        else:
            # Check system clipboard QImage
            sys_img = QApplication.clipboard().image()
            if not sys_img.isNull():
                w = min(sys_img.width(), self.doc.width)
                h = min(sys_img.height(), self.doc.height)
                for x in range(w):
                    for y in range(h):
                        qcol = sys_img.pixelColor(x, y)
                        if qcol.alpha() > 0:
                            hex_str = f"#{qcol.red():02X}{qcol.green():02X}{qcol.blue():02X}{qcol.alpha():02X}"
                            active.set_pixel(x, y, hex_str)
                            pasted_coords.append((x, y))

        if pasted_coords:
            self.canvas.selection.replace(pasted_coords)
            self._push_history()
            self.canvas.update()
            self.layer_panel.refresh_list()
            self.appearance_panel.refresh_panel()
            self.animation_panel.refresh_timeline()
            self.status_bar.showMessage(f"Pasted {len(pasted_coords)} pixels", 2000)
        else:
            self.status_bar.showMessage("Clipboard is empty", 2000)

    # ---- File Actions ----

    def on_file_new(self) -> None:
        dlg = NewCanvasDialog(self)
        if dlg.exec() == NewCanvasDialog.Accepted:
            w, h, bg = dlg.get_values()
            self.doc = PixelDocument(w, h)
            if bg == "White":
                bg_layer = self.doc.active_layer
                if bg_layer:
                    for x in range(w):
                        for y in range(h):
                            bg_layer.set_pixel(x, y, "#FFFFFFFF")
            elif bg == "Black":
                bg_layer = self.doc.active_layer
                if bg_layer:
                    for x in range(w):
                        for y in range(h):
                            bg_layer.set_pixel(x, y, "#000000FF")

            self.history.clear()
            self.history.push(self.doc.to_dict())
            self.canvas.set_document(self.doc)
            self.layer_panel.set_document(self.doc)
            self.appearance_panel.set_document(self.doc)
            self.animation_panel.set_document(self.doc)
            self.setWindowTitle("Coopixel - Pixel Art Editor")

    def open_file(self, filepath: str) -> bool:
        """Opens a .pix / .caml file directly from the given file path."""
        if not os.path.exists(filepath):
            # If target file does not exist yet, set it as active filepath for saving
            self.doc.filepath = filepath
            self.setWindowTitle(f"Coopixel - {filepath}")
            return True
        try:
            self.doc = PixelDocument.load_from_pix(filepath)
            self.history.clear()
            self.history.push(self.doc.to_dict())
            self.canvas.set_document(self.doc)
            self.layer_panel.set_document(self.doc)
            self.appearance_panel.set_document(self.doc)
            self.animation_panel.set_document(self.doc)
            self.setWindowTitle(f"Coopixel - {filepath}")
            self.status_bar.showMessage(f"Opened {filepath}", 3000)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error Opening File", f"Failed to load file:\n{e}")
            return False

    def on_file_open(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Coopixel File", "", "Coopixel / CAML Files (*.pix *.caml);;All Files (*)"
        )
        if filepath:
            self.open_file(filepath)


    def on_file_save(self) -> None:
        if self.doc.filepath:
            try:
                self.doc.save_to_pix(self.doc.filepath)
                self.setWindowTitle(f"Coopixel - {self.doc.filepath}")
                self.status_bar.showMessage("File saved successfully.", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error Saving File", f"Failed to save file:\n{e}")
        else:
            self.on_file_save_as()

    def on_file_save_as(self) -> None:
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Coopixel File", "untitled.pix", "Coopixel Image (*.pix);;CAML File (*.caml)"
        )
        if filepath:
            try:
                self.doc.save_to_pix(filepath)
                self.setWindowTitle(f"Coopixel - {filepath}")
                self.status_bar.showMessage("File saved successfully.", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error Saving File", f"Failed to save file:\n{e}")

    def on_file_import_png(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Image as Layer", "", "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        if filepath:
            try:
                layer = self.doc.import_image_as_layer(filepath)
                if layer:
                    self._push_history()
                    self.canvas.update()
                    self.layer_panel.refresh_list()
                    self.appearance_panel.refresh_panel()
                    self.animation_panel.refresh_timeline()
                    self.status_bar.showMessage(f"Imported {os.path.basename(filepath)} as layer '{layer.name}'", 3000)
                else:
                    QMessageBox.warning(self, "Import Failed", "Could not load image file.")
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import image:\n{e}")

    def on_file_export_png(self) -> None:
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export PNG Image", "export.png", "PNG Image (*.png)"
        )
        if filepath:
            try:
                if self.doc.export_png(filepath):
                    self.status_bar.showMessage("PNG exported successfully.", 3000)
                else:
                    QMessageBox.warning(self, "Export Failed", "Could not export PNG image.")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export PNG:\n{e}")

    def on_about(self) -> None:
        dlg = AboutDialog(self)
        dlg.exec()

    def update_status_bar(self, x: int, y: int) -> None:
        active_name = self.doc.active_layer.name if self.doc.active_layer else "None"
        zoom_pct = int(self.canvas.zoom_level * 100 / 16)
        msg = (
            f"Pos: ({x}, {y})  |  Canvas: {self.doc.width}×{self.doc.height}  |  "
            f"Zoom: {zoom_pct}%  |  Layer: {active_name}"
        )
        self.status_bar.showMessage(msg)
