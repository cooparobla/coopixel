"""
Main Window for Coopixel Pixel Art Editor.
Integrates dark theme, standard photo editor menu bar, tool toolbar, canvas viewport, dock panels, and layer effects.
"""

import copy
import os
from typing import Optional, Tuple
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QImage, QKeySequence, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
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
from coopixel.ui.actions_panel import ActionRecord, ActionsPanel
from coopixel.ui.align_panel import AlignPanel
from coopixel.ui.animation_panel import AnimationPanel
from coopixel.ui.appearance_panel import AppearancePanel
from coopixel.ui.canvas import CanvasWidget
from coopixel.ui.color_panel import ColorPanel
from coopixel.ui.dialogs import AboutDialog, CanvasSizeDialog, CropCanvasDialog, ImportImageDialog, NewCanvasDialog
from coopixel.ui.layer_panel import LayerPanel
from coopixel.ui.path_panel import PathPanel
from coopixel.ui.shortcuts_dialog import ShortcutsDialog, load_shortcuts
from coopixel.ui.spritesheet_import_dialog import SpritesheetImportDialog
from coopixel.ui.tag_panel import TagPanel
from coopixel.ui.tool_panel import ToolPanel



class MainWindow(QMainWindow):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("COOPIXEL")
        self.resize(1280, 820)
        self.actions_by_id: dict = {}

        # Set window icon
        pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(pkg_dir, "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # ---- Document & History ----
        self.doc: PixelDocument = PixelDocument(32, 32)
        self.history: HistoryStack = HistoryStack(max_depth=50)
        self._clean_state_snapshot: Optional[dict] = copy.deepcopy(self.doc.to_dict())

        # ---- Canvas (Central Widget) ----
        self.canvas = CanvasWidget(self.doc)
        self.canvas.cursor_moved.connect(self.update_status_bar)
        # stroke_committed = full stroke done → push history snapshot
        self.canvas.stroke_committed.connect(self.on_stroke_committed)
        # canvas_updated = live repaint during stroke (no history)
        self.canvas.canvas_updated.connect(self.canvas.update)

        # ---- Tool Options Bar (top toolbar) ----
        self.tool_panel = ToolPanel(self)
        tb = self._wrap_in_toolbar("Tool Options", self.tool_panel)
        self.addToolBar(Qt.TopToolBarArea, tb)

        self.tool_panel.tool_selected.connect(self.on_tool_selected)
        self.tool_panel.brush_size_changed.connect(self.on_brush_size_changed)
        self.tool_panel.shape_filled_changed.connect(self.on_shape_filled_changed)
        self.tool_panel.crop_commit_requested.connect(self.on_crop_tool_commit_requested)
        self.tool_panel.crop_cancel_requested.connect(self.on_crop_tool_cancel_requested)
        self.tool_panel.crop_fit_sel_requested.connect(self.on_crop_tool_fit_sel_requested)
        self.tool_panel.crop_fit_content_requested.connect(self.on_crop_tool_fit_content_requested)
        self.tool_panel.crop_wh_changed.connect(self.on_crop_wh_changed)
        self.tool_panel.selection_cleared.connect(self.on_selection_committed)
        self.tool_panel.move_nudge_requested.connect(self.on_move_nudge_requested)
        self.tool_panel.pivot_changed.connect(self.on_pivot_changed)

        self.canvas.crop_committed.connect(self.on_crop_committed)
        self.canvas.crop_box_changed.connect(self.tool_panel.update_crop_box_ui)
        self.canvas.selection_committed.connect(self.on_selection_committed)
        self.canvas.pivot_modified.connect(self.tool_panel.update_pivot_spins)
        self.canvas.color_picked.connect(lambda hex_col: self.color_panel.set_primary_color(hex_col))

        # Set default tool to Selection Tool
        self.tool_panel.select_tool_by_key("selection")

        # Wire Color Picker callback
        self.tool_panel.tools["picker"].on_color_picked = self.on_color_picked_from_canvas

        # Link shared SelectionModel between canvas and tool panel
        self.tool_panel.set_canvas_selection(self.canvas.selection)

        # ---- Left-side Dock Panels ----
        # Layer panel first (top of left side)
        self.layer_panel = LayerPanel(self.doc, self)
        self.layer_panel.layer_structure_changed.connect(self.on_layer_structure_changed)
        self.layer_panel.layer_visual_changed.connect(self.on_layer_visual_changed)
        self.layer_panel.crop_layer_requested.connect(self.on_crop_layer_requested)
        self.layer_panel.select_layer_content_requested.connect(self.on_select_layer_content)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.layer_panel)

        # Color panel below layers
        self.color_panel = ColorPanel(self)
        self.color_panel.primary_color_changed.connect(self.on_primary_color_changed)
        self.color_panel.secondary_color_changed.connect(self.on_secondary_color_changed)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.color_panel)

        # Stack them vertically (layer panel above color panel)
        self.splitDockWidget(self.layer_panel, self.color_panel, Qt.Vertical)

        # ---- Right-side Dock Panels ----
        self.align_panel = AlignPanel(self.doc, self)
        self.align_panel.align_committed.connect(self.on_layer_aligned)
        self.addDockWidget(Qt.RightDockWidgetArea, self.align_panel)
        self.align_panel.hide()

        self.appearance_panel = AppearancePanel(self.doc, self)
        self.appearance_panel.effect_changed.connect(self.on_layer_structure_changed)
        self.addDockWidget(Qt.RightDockWidgetArea, self.appearance_panel)
        self.appearance_panel.hide()

        self.tag_panel = TagPanel(self.doc, self)
        self.tag_panel.tag_visibility_changed.connect(self.on_tag_visibility_changed)
        self.addDockWidget(Qt.RightDockWidgetArea, self.tag_panel)
        self.tag_panel.hide()

        self.actions_panel = ActionsPanel(self)
        self.actions_panel.run_action_requested.connect(self.on_run_action)
        self.addDockWidget(Qt.RightDockWidgetArea, self.actions_panel)
        self.actions_panel.hide()

        self.path_panel = PathPanel(self.doc, self)
        self.path_panel.path_changed.connect(self.on_path_changed)
        self.path_panel.path_selected.connect(self.on_path_selected)
        self.canvas.path_modified.connect(self.path_panel.refresh_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.path_panel)
        self.path_panel.hide()



        # Connect tool panel pen action signals to path panel
        self.tool_panel.pen_stroke_requested.connect(self.path_panel.on_stroke_path)
        self.tool_panel.pen_fill_requested.connect(self.path_panel.on_fill_path)
        self.tool_panel.pen_new_path_requested.connect(self.path_panel.on_add_path)

        # ---- Bottom Dock Panels ----
        self.animation_panel = AnimationPanel(self.doc, self)
        self.animation_panel.animation_structure_changed.connect(self.on_frame_structure_changed)
        self.animation_panel.frame_structure_changed.connect(self.on_frame_structure_changed)
        self.animation_panel.active_frame_changed.connect(self.on_active_frame_changed)
        self.animation_panel.animation_visual_changed.connect(self.canvas.update)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.animation_panel)
        self.animation_panel.hide()

        # Tabify right dock panels so they share the right dock space cleanly when opened
        self.tabifyDockWidget(self.path_panel, self.appearance_panel)
        self.tabifyDockWidget(self.appearance_panel, self.align_panel)
        self.tabifyDockWidget(self.align_panel, self.tag_panel)
        self.tabifyDockWidget(self.tag_panel, self.actions_panel)


        # Build Main View Layout
        drawing_area = QWidget()
        drawing_layout = QHBoxLayout(drawing_area)
        drawing_layout.setContentsMargins(0, 0, 0, 0)
        drawing_layout.setSpacing(0)
        drawing_layout.addWidget(self.canvas, stretch=1)
        self.setCentralWidget(drawing_area)

        # Sync initial colors
        self.canvas.primary_color = self.color_panel.primary_color
        self.canvas.secondary_color = self.color_panel.secondary_color
        self.doc.primary_color = self.color_panel.primary_color


        # ---- Right-hand Vertical Icon Toolbar ----
        self._build_right_sidebar_toolbar()

        # ---- Status Bar ----
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._build_status_bar_view_options()

        # ---- Menu Bar ----
        self._build_menu_bar()
        self.update_status_bar(0, 0)
        self._push_history()
        self.update_window_title()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _wrap_in_toolbar(self, name: str, widget: QWidget) -> QToolBar:
        tb = QToolBar(name, self)
        tb.setMovable(False)
        tb.addWidget(widget)
        return tb

    def _build_right_sidebar_toolbar(self) -> None:
        """Icon-only vertical toolbar on the right side of drawing area for panel toggles."""
        right_tb = QToolBar("Sidebar", self)
        right_tb.setMovable(False)
        right_tb.setOrientation(Qt.Vertical)
        right_tb.setStyleSheet(
            "QToolBar { background-color: #202020; border-left: 1px solid #333333; spacing: 4px; padding: 4px; }"
            "QToolButton { background: #282828; border: 1px solid #333333; border-radius: 4px; padding: 4px 7px; font-size: 13px; color: #F1F5F9; }"
            "QToolButton:hover { background: #332B25; border-color: #F97316; }"
            "QToolButton:checked { background: #2E2620; border-color: #F97316; color: #F97316; }"
        )

        path_act = QAction("🖋️", self)
        path_act.setToolTip("Vector Paths Panel")
        path_act.setCheckable(True)
        path_act.setChecked(self.path_panel.isVisible())
        path_act.toggled.connect(self.path_panel.setVisible)
        self.path_panel.visibilityChanged.connect(path_act.setChecked)

        align_act = QAction("📐", self)
        align_act.setToolTip("Align Layer to Canvas")
        align_act.setCheckable(True)
        align_act.setChecked(self.align_panel.isVisible())
        align_act.toggled.connect(self.align_panel.setVisible)
        self.align_panel.visibilityChanged.connect(align_act.setChecked)

        app_act = QAction("✨", self)
        app_act.setToolTip("Appearance & Layer Effects")
        app_act.setCheckable(True)
        app_act.setChecked(self.appearance_panel.isVisible())
        app_act.toggled.connect(self.appearance_panel.setVisible)
        self.appearance_panel.visibilityChanged.connect(app_act.setChecked)

        tag_act = QAction("🏷️", self)
        tag_act.setToolTip("Tag Manager")
        tag_act.setCheckable(True)
        tag_act.setChecked(self.tag_panel.isVisible())
        tag_act.toggled.connect(self.tag_panel.setVisible)
        self.tag_panel.visibilityChanged.connect(tag_act.setChecked)

        actions_act = QAction("⚡", self)
        actions_act.setToolTip("Actions History")
        actions_act.setCheckable(True)
        actions_act.setChecked(self.actions_panel.isVisible())
        actions_act.toggled.connect(self.actions_panel.setVisible)
        self.actions_panel.visibilityChanged.connect(actions_act.setChecked)

        anim_act = QAction("🎬", self)
        anim_act.setToolTip("Animation Timeline")
        anim_act.setCheckable(True)
        anim_act.setChecked(self.animation_panel.isVisible())
        anim_act.toggled.connect(self.animation_panel.setVisible)
        self.animation_panel.visibilityChanged.connect(anim_act.setChecked)

        right_tb.addAction(path_act)
        right_tb.addAction(align_act)
        right_tb.addAction(app_act)
        right_tb.addAction(tag_act)
        right_tb.addAction(actions_act)
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

        import_sheet_act = QAction("Import &Spritesheet...", self)
        import_sheet_act.triggered.connect(self.on_file_import_spritesheet)
        file_menu.addAction(import_sheet_act)

        import_pal_act = QAction("Import &Palette PNG...", self)
        import_pal_act.setShortcut(QKeySequence("Ctrl+Shift+P"))
        import_pal_act.triggered.connect(self.color_panel.on_load_palette_png)
        file_menu.addAction(import_pal_act)

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

        sel_layer_act = QAction("Select Layer &Content", self)
        sel_layer_act.triggered.connect(lambda: self.on_select_layer_content())
        edit_menu.addAction(sel_layer_act)

        edit_menu.addSeparator()

        shortcuts_act = QAction("Keyboard &Shortcuts...", self)
        shortcuts_act.triggered.connect(self.on_open_shortcuts_dialog)
        edit_menu.addAction(shortcuts_act)

        # ---- IMAGE ----
        image_menu = menu_bar.addMenu("&Image")

        crop_dialog_act = QAction("&Crop Canvas...", self)
        crop_dialog_act.setShortcut(QKeySequence("Ctrl+Shift+X"))
        crop_dialog_act.triggered.connect(self.on_crop_canvas_dialog)
        image_menu.addAction(crop_dialog_act)

        crop_sel_act = QAction("Crop Canvas to &Selection", self)
        crop_sel_act.triggered.connect(self.on_crop_to_selection)
        image_menu.addAction(crop_sel_act)

        crop_content_act = QAction("&Trim Canvas to Content", self)
        crop_content_act.triggered.connect(self.on_crop_to_content)
        image_menu.addAction(crop_content_act)

        image_menu.addSeparator()

        img_canvas_size_act = QAction("Canvas Size...", self)
        img_canvas_size_act.triggered.connect(self.on_change_canvas_size)
        image_menu.addAction(img_canvas_size_act)

        crop_tool_act = QAction("Crop Tool", self)
        crop_tool_act.setShortcut(QKeySequence("K"))
        crop_tool_act.triggered.connect(lambda: self.tool_panel.select_tool_by_key("crop"))
        self.addAction(crop_tool_act)

        move_tool_act = QAction("Move Tool", self)
        move_tool_act.setShortcut(QKeySequence("V"))
        move_tool_act.triggered.connect(lambda: self.tool_panel.select_tool_by_key("move"))
        self.addAction(move_tool_act)

        sel_tool_act = QAction("Selection Tool", self)
        sel_tool_act.setShortcut(QKeySequence("S"))
        sel_tool_act.triggered.connect(lambda: self.tool_panel.select_tool_by_key("selection"))
        self.addAction(sel_tool_act)

        pencil_tool_act = QAction("Draw Tool", self)
        pencil_tool_act.setShortcut(QKeySequence("D"))
        pencil_tool_act.triggered.connect(lambda: self.tool_panel.select_tool_by_key("pencil"))
        self.addAction(pencil_tool_act)

        pen_tool_act = QAction("Pen Tool", self)
        pen_tool_act.setShortcut(QKeySequence("P"))
        pen_tool_act.triggered.connect(lambda: self.tool_panel.select_tool_by_key("pen"))
        self.addAction(pen_tool_act)

        pivot_tool_act = QAction("Pivot Tool", self)
        pivot_tool_act.setShortcut(QKeySequence("Shift+P"))
        pivot_tool_act.triggered.connect(lambda: self.tool_panel.select_tool_by_key("pivot"))
        self.addAction(pivot_tool_act)


        eraser_tool_act = QAction("Eraser Tool", self)
        eraser_tool_act.setShortcut(QKeySequence("E"))
        eraser_tool_act.triggered.connect(lambda: self.tool_panel.select_tool_by_key("eraser"))
        self.addAction(eraser_tool_act)

        picker_tool_act = QAction("Color Picker", self)
        picker_tool_act.setShortcut(QKeySequence("I"))
        picker_tool_act.triggered.connect(lambda: self.tool_panel.select_tool_by_key("picker"))
        self.addAction(picker_tool_act)

        fill_tool_act = QAction("Bucket Fill Tool", self)
        fill_tool_act.setShortcut(QKeySequence("F"))
        fill_tool_act.triggered.connect(lambda: self.tool_panel.select_tool_by_key("fill"))
        self.addAction(fill_tool_act)

        line_tool_act = QAction("Line Tool", self)
        line_tool_act.setShortcut(QKeySequence("L"))
        line_tool_act.triggered.connect(lambda: self.tool_panel.select_tool_by_key("line"))
        self.addAction(line_tool_act)

        rect_tool_act = QAction("Rectangle Tool", self)
        rect_tool_act.setShortcut(QKeySequence("R"))
        rect_tool_act.triggered.connect(lambda: self.tool_panel.select_tool_by_key("rectangle"))
        self.addAction(rect_tool_act)

        circle_tool_act = QAction("Circle Tool", self)
        circle_tool_act.setShortcut(QKeySequence("C"))
        circle_tool_act.triggered.connect(lambda: self.tool_panel.select_tool_by_key("circle"))
        self.addAction(circle_tool_act)

        decrease_size_act = QAction("Decrease Tool Size", self)
        decrease_size_act.setShortcut(QKeySequence("["))
        decrease_size_act.triggered.connect(self._decrease_brush_size)
        self.addAction(decrease_size_act)

        increase_size_act = QAction("Increase Tool Size", self)
        increase_size_act.setShortcut(QKeySequence("]"))
        increase_size_act.triggered.connect(self._increase_brush_size)
        self.addAction(increase_size_act)

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

        center_canvas_act = QAction("Center &Canvas", self)
        center_canvas_act.setShortcut(QKeySequence("A"))
        center_canvas_act.triggered.connect(self._center_canvas)
        view_menu.addAction(center_canvas_act)
        self.addAction(center_canvas_act)

        view_menu.addSeparator()

        self.grid_act = QAction("Toggle &Grid", self)
        self.grid_act.setCheckable(True)
        self.grid_act.setChecked(True)
        self.grid_act.setShortcut(QKeySequence("Ctrl+G"))
        self.grid_act.triggered.connect(self._on_toggle_grid_clicked)
        view_menu.addAction(self.grid_act)

        self.border_act = QAction("Toggle Canvas &Border Outline", self)
        self.border_act.setCheckable(True)
        self.border_act.setChecked(True)
        self.border_act.triggered.connect(self._on_toggle_border_clicked)
        view_menu.addAction(self.border_act)

        view_menu.addSeparator()

        toggle_layers_act = self.layer_panel.toggleViewAction()
        toggle_layers_act.setText("Layers Panel")
        view_menu.addAction(toggle_layers_act)

        toggle_paths_act = self.path_panel.toggleViewAction()
        toggle_paths_act.setText("Paths Panel")
        view_menu.addAction(toggle_paths_act)

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
        del_l_act.setShortcut(QKeySequence.Delete)
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

        layer_menu.addSeparator()

        crop_l_act = QAction("Crop Layer to &Canvas", self)
        crop_l_act.setToolTip("Removes any pixel data in the active layer outside current canvas dimensions")
        crop_l_act.triggered.connect(self.layer_panel.on_crop_layer_to_canvas)
        layer_menu.addAction(crop_l_act)

        # ---- ANIMATION ----
        anim_menu = menu_bar.addMenu("&Animation")

        play_act = QAction("&Play / Pause Animation", self)
        play_act.setShortcut(QKeySequence(Qt.Key_Space))
        play_act.triggered.connect(self.animation_panel.toggle_play)
        anim_menu.addAction(play_act)

        anim_menu.addSeparator()

        add_frame_act = QAction("&Add New Frame", self)
        add_frame_act.triggered.connect(self.animation_panel.on_add_frame)
        anim_menu.addAction(add_frame_act)

        dup_frame_act = QAction("&Duplicate Active Frame", self)
        dup_frame_act.triggered.connect(self.animation_panel.on_duplicate_frame)
        anim_menu.addAction(dup_frame_act)

        del_frame_act = QAction("&Delete Active Frame", self)
        del_frame_act.triggered.connect(self.animation_panel.on_delete_frame)
        anim_menu.addAction(del_frame_act)

        # ---- TOOLS ----
        tools_menu = menu_bar.addMenu("&Tools")
        tools_menu.addAction("Selection Tool (S)", lambda: self.tool_panel.select_tool_by_key("selection"))
        tools_menu.addAction("Draw Tool (D)", lambda: self.tool_panel.select_tool_by_key("pencil"))
        tools_menu.addAction("Pen Tool (P)", lambda: self.tool_panel.select_tool_by_key("pen"))
        tools_menu.addAction("Eraser Tool (E)", lambda: self.tool_panel.select_tool_by_key("eraser"))
        tools_menu.addAction("Color Picker (I)", lambda: self.tool_panel.select_tool_by_key("picker"))
        tools_menu.addAction("Bucket Fill (F)", lambda: self.tool_panel.select_tool_by_key("fill"))
        tools_menu.addAction("Line Tool (L)", lambda: self.tool_panel.select_tool_by_key("line"))
        tools_menu.addAction("Rectangle Tool (R)", lambda: self.tool_panel.select_tool_by_key("rectangle"))
        tools_menu.addAction("Circle Tool (C)", lambda: self.tool_panel.select_tool_by_key("circle"))


        # ---- WINDOW ----
        window_menu = menu_bar.addMenu("&Window")
        self.show_bounds_act = QAction("Show &Active Layer Content Bounds", self)
        self.show_bounds_act.setCheckable(True)
        self.show_bounds_act.setChecked(True)
        self.show_bounds_act.setShortcut(QKeySequence("Ctrl+Shift+B"))
        self.show_bounds_act.triggered.connect(self._on_toggle_bounds_clicked)
        window_menu.addAction(self.show_bounds_act)

        # Register actions map for shortcuts config
        self.actions_by_id = {
            "file_new": new_act,
            "file_open": open_act,
            "file_save": save_act,
            "file_save_as": save_as_act,
            "file_import_layer": import_act,
            "file_import_palette": import_pal_act,
            "file_export": export_act,
            "file_exit": exit_act,
            "edit_undo": self.undo_act,
            "edit_redo": self.redo_act,
            "edit_cut": cut_act,
            "edit_copy": copy_act,
            "edit_paste": paste_act,
            "edit_select_all": sel_all_act,
            "edit_deselect": desel_act,
            "edit_invert_selection": invert_sel_act,
            "edit_select_layer_content": sel_layer_act,
            "crop_canvas_dialog": crop_dialog_act,
            "tool_crop": crop_tool_act,
            "tool_move": move_tool_act,
            "tool_selection": sel_tool_act,
            "tool_pencil": pencil_tool_act,
            "tool_pen": pen_tool_act,
            "tool_pivot": pivot_tool_act,
            "tool_eraser": eraser_tool_act,
            "tool_picker": picker_tool_act,
            "tool_fill": fill_tool_act,
            "tool_line": line_tool_act,
            "tool_rect": rect_tool_act,
            "tool_circle": circle_tool_act,
            "decrease_size": decrease_size_act,
            "increase_size": increase_size_act,
            "zoom_in": zoom_in_act,
            "zoom_out": zoom_out_act,
            "zoom_reset": reset_zoom_act,
            "center_canvas": center_canvas_act,
            "toggle_grid": self.grid_act,
            "toggle_bounds": self.show_bounds_act,
            "add_layer": add_l_act,
            "delete_layer": del_l_act,
            "copy_layer": copy_l_act,
            "paste_layer": paste_l_act,
            "play_animation": play_act,
        }
        self._apply_shortcuts()

        window_menu.addSeparator()

        w_layers_act = self.layer_panel.toggleViewAction()
        w_layers_act.setText("Layers Panel")
        window_menu.addAction(w_layers_act)

        w_colors_act = self.color_panel.toggleViewAction()
        w_colors_act.setText("Color Panel")
        window_menu.addAction(w_colors_act)

        w_app_act = self.appearance_panel.toggleViewAction()
        w_app_act.setText("Appearance & Layer Effects Panel")
        window_menu.addAction(w_app_act)

        w_anim_act = self.animation_panel.toggleViewAction()
        w_anim_act.setText("Animation Timeline Panel")
        window_menu.addAction(w_anim_act)

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

    def _on_toggle_grid_clicked(self) -> None:
        self.canvas.toggle_grid()
        if hasattr(self, "view_btn_grid"):
            self.view_btn_grid.setChecked(self.canvas.show_grid)
        if hasattr(self, "grid_act"):
            self.grid_act.setChecked(self.canvas.show_grid)

    def _on_toggle_border_clicked(self) -> None:
        self.canvas.toggle_canvas_border()
        if hasattr(self, "view_btn_border"):
            self.view_btn_border.setChecked(self.canvas.show_canvas_border)
        if hasattr(self, "border_act"):
            self.border_act.setChecked(self.canvas.show_canvas_border)

    def _on_toggle_bounds_clicked(self) -> None:
        self.canvas.toggle_layer_bounds()
        if hasattr(self, "view_btn_bounds"):
            self.view_btn_bounds.setChecked(self.canvas.show_layer_bounds)
        if hasattr(self, "show_bounds_act"):
            self.show_bounds_act.setChecked(self.canvas.show_layer_bounds)

    def _build_status_bar_view_options(self) -> None:
        """Adds 2D viewer option buttons (Grid, Canvas Border, Layer Bounds, Reset View) to the bottom-right of the status bar."""
        options_widget = QWidget()
        layout = QHBoxLayout(options_widget)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(4)

        btn_style = (
            "QToolButton { background: #242424; border: 1px solid #383838; border-radius: 4px; padding: 2px 6px; font-size: 13px; color: #E2E8F0; }"
            "QToolButton:hover { background: #332B25; border-color: #F97316; color: #FFFFFF; }"
            "QToolButton:checked { background: #2E2620; border-color: #F97316; color: #F97316; font-weight: bold; }"
        )

        self.view_btn_grid = QToolButton()
        self.view_btn_grid.setText("🌐")
        self.view_btn_grid.setToolTip("Toggle Pixel Grid (Ctrl+G)")
        self.view_btn_grid.setCheckable(True)
        self.view_btn_grid.setChecked(self.canvas.show_grid)
        self.view_btn_grid.setStyleSheet(btn_style)
        self.view_btn_grid.clicked.connect(self._on_toggle_grid_clicked)

        self.view_btn_border = QToolButton()
        self.view_btn_border.setText("🖼️")
        self.view_btn_border.setToolTip("Toggle Canvas Border Outline")
        self.view_btn_border.setCheckable(True)
        self.view_btn_border.setChecked(self.canvas.show_canvas_border)
        self.view_btn_border.setStyleSheet(btn_style)
        self.view_btn_border.clicked.connect(self._on_toggle_border_clicked)

        self.view_btn_bounds = QToolButton()
        self.view_btn_bounds.setText("📐")
        self.view_btn_bounds.setToolTip("Toggle Active Layer Content Bounds (Ctrl+Shift+B)")
        self.view_btn_bounds.setCheckable(True)
        self.view_btn_bounds.setChecked(self.canvas.show_layer_bounds)
        self.view_btn_bounds.setStyleSheet(btn_style)
        self.view_btn_bounds.clicked.connect(self._on_toggle_bounds_clicked)

        self.view_btn_reset = QToolButton()
        self.view_btn_reset.setText("🎯")
        self.view_btn_reset.setToolTip("Reset View (Zoom 16x & Center Canvas, Ctrl+0)")
        self.view_btn_reset.setStyleSheet(btn_style)
        self.view_btn_reset.clicked.connect(self._reset_view)

        layout.addWidget(self.view_btn_grid)
        layout.addWidget(self.view_btn_border)
        layout.addWidget(self.view_btn_bounds)
        layout.addWidget(self.view_btn_reset)

        self.status_bar.addPermanentWidget(options_widget)

    def is_dirty(self) -> bool:
        """Returns True if current document state differs from last saved or clean state."""
        if self._clean_state_snapshot is None:
            return False
        return self.doc.to_dict() != self._clean_state_snapshot

    def update_window_title(self) -> None:
        """Updates main window title bar with document file path and dirty indicator (*) if modified."""
        if self.doc.filepath:
            name = self.doc.filepath
        else:
            name = "Pixel Art Editor"

        dirty_star = "*" if self.is_dirty() else ""
        self.setWindowTitle(f"Coopixel - {name}{dirty_star}")

    def maybe_save_changes(self, action_desc: str = "closing") -> bool:
        """Prompts user to save changes if document is dirty.
        Returns True if safe to proceed (saved or discarded), False if user cancelled.
        """
        if not self.is_dirty():
            return True

        if self.doc.filepath:
            filename = os.path.basename(self.doc.filepath)
        else:
            filename = "Untitled.pix"

        res = QMessageBox.question(
            self,
            "Save Changes?",
            f"Do you want to save changes to '{filename}' before {action_desc}?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )

        if res == QMessageBox.Save:
            return self.on_file_save()
        elif res == QMessageBox.Discard:
            return True
        else:
            return False

    def closeEvent(self, event) -> None:
        """Intercepts window close event to prompt for unsaved changes."""
        if self.maybe_save_changes(action_desc="closing"):
            event.accept()
        else:
            event.ignore()

    def _push_history(self) -> None:
        """Push current document state and selection state to the history stack."""
        doc_dict = self.doc.to_dict()
        if hasattr(self, "canvas") and hasattr(self.canvas, "selection"):
            doc_dict["selection"] = [list(pt) for pt in self.canvas.selection.selected]
        else:
            doc_dict["selection"] = []
        self.history.push(doc_dict)
        self.update_window_title()

    def _restore_from_dict(self, state: dict) -> None:
        """Restore document and selection state from a state dict and update all UI, preserving current view."""
        filepath = self.doc.filepath
        # Save current view state before swapping the document
        saved_zoom = self.canvas.zoom_level
        saved_pan = self.canvas.pan_offset

        self.doc = PixelDocument.from_dict(state, filepath=filepath)
        # Update canvas doc reference without calling center_canvas()
        self.canvas.doc = self.doc
        self.canvas.zoom_level = saved_zoom
        self.canvas.pan_offset = saved_pan

        if "selection" in state and isinstance(state["selection"], list):
            sel_coords = state["selection"]
            self.canvas.selection.replace({(pt[0], pt[1]) for pt in sel_coords})
        else:
            self.canvas.selection.clear()

        self.canvas.invalidate_cache()
        self.canvas.update()
        self.layer_panel.set_document(self.doc)
        self.appearance_panel.set_document(self.doc)
        self.animation_panel.set_document(self.doc)
        self.tag_panel.set_document(self.doc)
        self.align_panel.set_document(self.doc)
        self.path_panel.set_document(self.doc)
        self.update_window_title()

    def on_path_changed(self) -> None:
        """Called when a path is added, modified, stroked, filled, or deleted."""
        self.canvas.invalidate_cache()
        self.canvas.update()
        self.path_panel.refresh_panel()
        self._push_history()

    def on_path_selected(self, path_idx: int) -> None:
        """Called when user selects a path in the Paths panel."""
        self.layer_panel.refresh_list()
        self.canvas.update()



    def on_layer_aligned(self, desc: str) -> None:
        """Called when active layer is aligned via AlignPanel."""
        self.canvas.invalidate_cache()
        self.canvas.update()
        self.status_bar.showMessage(desc, 1500)
        self._push_history()

    def on_selection_committed(self) -> None:
        """Called when a selection is created, modified, or cleared — pushes history state."""
        self._push_history()
        self.canvas.update()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def on_stroke_committed(self) -> None:
        """Called when a drawing stroke completes — pushes history and refreshes panels."""
        self._push_history()
        self.layer_panel.refresh_list()
        self.appearance_panel.refresh_panel()
        self.animation_panel.refresh_timeline()
        self.tag_panel.refresh_tags()
        self.canvas.invalidate_cache()
        self.canvas.update()

    def on_layer_structure_changed(self) -> None:
        """Called when layers/effects/tags are added/deleted/reordered/duplicated — push history."""
        self._push_history()
        self.appearance_panel.refresh_panel()
        self.animation_panel.refresh_timeline()
        self.tag_panel.refresh_tags()
        self.canvas.invalidate_cache()
        self.canvas.update()

    def on_layer_visual_changed(self) -> None:
        """Called when layer visibility/opacity/lock changes — repaint only, no history."""
        self.appearance_panel.refresh_panel()
        self.animation_panel.refresh_timeline()
        self.tag_panel.refresh_tags()
        self.canvas.invalidate_cache()
        self.canvas.update()

    def on_tag_visibility_changed(self) -> None:
        """Called when tag global visibility eye toggle is clicked."""
        self._push_history()
        self.canvas.invalidate_cache()
        self.layer_panel.refresh_list()
        self.appearance_panel.refresh_panel()
        self.animation_panel.refresh_timeline()
        self.canvas.update()

    def on_frame_structure_changed(self) -> None:
        """Called when frames are added/deleted/duplicated/reordered — push history."""
        self._push_history()
        self.canvas.invalidate_cache()
        self.layer_panel.refresh_list()
        self.appearance_panel.refresh_panel()
        self.canvas.update()

    def on_active_frame_changed(self) -> None:
        """Called when active frame is changed — updates layer panel, appearance panel, path panel & canvas."""
        self.canvas.invalidate_cache()
        self.layer_panel.refresh_list()
        self.appearance_panel.refresh_panel()
        self.tag_panel.refresh_tags()
        self.path_panel.refresh_panel()
        if self.doc and self.doc.active_animation:
            anim = self.doc.active_animation
            self.tool_panel.update_pivot_spins(anim.pivot_x, anim.pivot_y)
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
        if getattr(tool, "name", "") == "pen":
            if not self.path_panel.isVisible():
                self.path_panel.show()
        elif getattr(tool, "name", "") == "pivot":
            if self.doc and self.doc.active_animation:
                anim = self.doc.active_animation
                self.tool_panel.update_pivot_spins(anim.pivot_x, anim.pivot_y)
        self.canvas.update()

    def on_pivot_changed(self, x: int, y: int) -> None:
        if self.doc and self.doc.active_animation:
            anim = self.doc.active_animation
            if anim.pivot_x != x or anim.pivot_y != y:
                anim.pivot_x = x
                anim.pivot_y = y
                self._push_history()
                self.canvas.update()


    def on_brush_size_changed(self, size: int) -> None:
        self.canvas.brush_size = size
        self.canvas.update()

    def _decrease_brush_size(self) -> None:
        cur = self.tool_panel.size_spin.value()
        if cur > 1:
            new_size = cur - 1
            self.tool_panel.size_spin.setValue(new_size)
            self.canvas.update()
            self.status_bar.showMessage(f"Tool size: {new_size} px", 1000)

    def _increase_brush_size(self) -> None:
        cur = self.tool_panel.size_spin.value()
        if cur < 32:
            new_size = cur + 1
            self.tool_panel.size_spin.setValue(new_size)
            self.canvas.update()
            self.status_bar.showMessage(f"Tool size: {new_size} px", 1000)

    def _center_canvas(self) -> None:
        self.canvas.center_canvas()
        self.status_bar.showMessage("Centered canvas", 1000)

    def on_shape_filled_changed(self, filled: bool) -> None:
        self.canvas.shape_filled = filled

    def on_primary_color_changed(self, color_hex: str) -> None:
        self.canvas.primary_color = color_hex
        if hasattr(self, "doc") and self.doc:
            self.doc.primary_color = color_hex


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
            nw, nh, anchor = dlg.get_values()
            off_x, off_y = self._get_anchor_offset(nw, nh, anchor)
            self.doc.resize_canvas(nw, nh, anchor=anchor)

            if not self.canvas.selection.is_empty():
                new_sel = set()
                for sx, sy in self.canvas.selection.selected:
                    nx, ny = sx + off_x, sy + off_y
                    if 0 <= nx < nw and 0 <= ny < nh:
                        new_sel.add((nx, ny))
                self.canvas.selection.selected = new_sel

            self._push_history()
            self.canvas.center_canvas()
            self.canvas.update()
            self.status_bar.showMessage(f"Resized canvas to {nw}×{nh} px ({anchor})", 2000)

    def _get_anchor_offset(self, new_width: int, new_height: int, anchor: str) -> Tuple[int, int]:
        anchor = anchor.lower().strip()
        if anchor == "top-center":
            return (new_width - self.doc.width) // 2, 0
        elif anchor == "top-right":
            return new_width - self.doc.width, 0
        elif anchor == "middle-left":
            return 0, (new_height - self.doc.height) // 2
        elif anchor == "center":
            return (new_width - self.doc.width) // 2, (new_height - self.doc.height) // 2
        elif anchor == "middle-right":
            return new_width - self.doc.width, (new_height - self.doc.height) // 2
        elif anchor == "bottom-left":
            return 0, new_height - self.doc.height
        elif anchor == "bottom-center":
            return (new_width - self.doc.width) // 2, new_height - self.doc.height
        elif anchor == "bottom-right":
            return new_width - self.doc.width, new_height - self.doc.height
        else:
            return 0, 0

    def on_crop_canvas_dialog(self) -> None:
        sel_bbox = self.doc.get_selection_bbox(self.canvas.selection.selected)
        content_bbox = self.doc.get_content_bbox()
        dlg = CropCanvasDialog(self.doc.width, self.doc.height, selection_bbox=sel_bbox, content_bbox=content_bbox, parent=self)
        if dlg.exec() == QDialog.Accepted:
            x, y, w, h = dlg.get_values()
            self.on_crop_committed(x, y, w, h)

    def on_crop_to_selection(self) -> None:
        sel_bbox = self.doc.get_selection_bbox(self.canvas.selection.selected)
        if sel_bbox:
            x, y, w, h = sel_bbox
            self.on_crop_committed(x, y, w, h)
        else:
            self.status_bar.showMessage("No active selection to crop to", 2000)

    def on_crop_to_content(self) -> None:
        content_bbox = self.doc.get_content_bbox()
        if content_bbox:
            x, y, w, h = content_bbox
            self.on_crop_committed(x, y, w, h)
        else:
            self.status_bar.showMessage("No pixel content found to crop to", 2000)

    def on_crop_committed(self, x: int, y: int, w: int, h: int, record: bool = True) -> None:
        if w <= 0 or h <= 0:
            return

        self.doc.crop_canvas(x, y, w, h)
        if not self.canvas.selection.is_empty():
            new_sel = set()
            for sx, sy in self.canvas.selection.selected:
                nx, ny = sx - x, sy - y
                if 0 <= nx < w and 0 <= ny < h:
                    new_sel.add((nx, ny))
            self.canvas.selection.selected = new_sel

        crop_tool = getattr(self.tool_panel, "crop_tool", None)
        if crop_tool:
            crop_tool.clear_box()

        self._push_history()
        self.canvas.center_canvas()
        self.canvas.update()
        self.status_bar.showMessage(f"Cropped canvas to {w}×{h} px at ({x}, {y})", 2000)

        if record:
            # Record crop_canvas action
            self.actions_panel.record_action(
                action_type="crop_canvas",
                params={"x": x, "y": y, "width": w, "height": h},
                display_name="Crop Canvas",
                details=f"Bounds: {w}×{h} px at ({x}, {y})",
            )

    def on_crop_layer_requested(self) -> None:
        active_name = self.doc.active_layer.name if self.doc.active_layer else "Active Layer"
        self.actions_panel.record_action(
            action_type="crop_layer",
            params={},
            display_name="Crop Layer to Canvas",
            details=f"Layer: '{active_name}' to canvas ({self.doc.width}×{self.doc.height} px)",
        )

    def on_crop_tool_commit_requested(self) -> None:
        crop_tool = getattr(self.tool_panel, "crop_tool", None)
        if crop_tool and crop_tool.crop_box:
            x, y, w, h = crop_tool.crop_box
            self.on_crop_committed(x, y, w, h)
        else:
            content_bbox = self.doc.get_content_bbox()
            if content_bbox:
                x, y, w, h = content_bbox
                self.on_crop_committed(x, y, w, h)
            else:
                self.status_bar.showMessage("Draw a crop box on the canvas first", 2000)

    def on_crop_tool_cancel_requested(self) -> None:
        crop_tool = getattr(self.tool_panel, "crop_tool", None)
        if crop_tool:
            crop_tool.clear_box()
            self.canvas.update()
            self.status_bar.showMessage("Cleared crop box", 1500)

    def on_crop_tool_fit_sel_requested(self) -> None:
        crop_tool = getattr(self.tool_panel, "crop_tool", None)
        if crop_tool:
            sel_bbox = self.doc.get_selection_bbox(self.canvas.selection.selected)
            if sel_bbox:
                x, y, w, h = sel_bbox
                crop_tool.set_box(x, y, w, h)
                self.tool_panel.update_crop_box_ui(x, y, w, h)
                self.canvas.update()
                self.status_bar.showMessage(f"Set crop box to selection ({w}×{h} px)", 1500)
            else:
                self.status_bar.showMessage("No active selection", 1500)

    def on_crop_tool_fit_content_requested(self) -> None:
        crop_tool = getattr(self.tool_panel, "crop_tool", None)
        if crop_tool:
            content_bbox = self.doc.get_content_bbox()
            if content_bbox:
                x, y, w, h = content_bbox
                crop_tool.set_box(x, y, w, h)
                self.tool_panel.update_crop_box_ui(x, y, w, h)
                self.canvas.update()
                self.status_bar.showMessage(f"Set crop box to content ({w}×{h} px)", 1500)
            else:
                self.status_bar.showMessage("No content found", 1500)

    def on_crop_wh_changed(self, w: int, h: int) -> None:
        """User edited the W or H spinbox — apply to existing crop box origin."""
        crop_tool = getattr(self.tool_panel, "crop_tool", None)
        if crop_tool and crop_tool.crop_box:
            crop_tool.set_box_wh(w, h)
            self.canvas.update()
            x, y, _w, _h = crop_tool.crop_box
            self.status_bar.showMessage(f"Crop box resized to {w}×{h} px", 1000)

    def on_move_nudge_requested(self, dx: int, dy: int) -> None:
        move_tool = getattr(self.tool_panel, "move_tool", None)
        if move_tool:
            is_open = self.path_panel.isVisible() if hasattr(self, "path_panel") else False
            changed = move_tool.nudge(self.doc, dx, dy, selection=self.canvas.selection, path_panel_open=is_open)
            if changed:
                self._push_history()
                self.canvas.update()
                target_name = "path" if is_open and self.doc.active_path else "layer"
                self.status_bar.showMessage(f"Nudged {target_name} by ({dx}, {dy})", 1500)


    # ---- Selection & Clipboard Actions ----

    def on_select_all(self) -> None:
        self.canvas.selection.select_all(self.doc)
        self.on_selection_committed()
        self.status_bar.showMessage("Selected entire canvas", 1500)

    def on_deselect(self) -> None:
        self.canvas.selection.clear()
        self.on_selection_committed()

    def on_invert_selection(self) -> None:
        self.canvas.selection.invert(self.doc)
        self.on_selection_committed()

    def on_select_layer_content(self, layer_index: Optional[int] = None) -> None:
        if layer_index is None:
            layer_index = self.doc.active_layer_index
        if not self.doc or not (0 <= layer_index < len(self.doc.layers)):
            return
        self.doc.active_layer_index = layer_index
        layer = self.doc.layers[layer_index]
        self.canvas.selection.select_layer_pixels(layer, self.doc)
        self.on_selection_committed()
        self.status_bar.showMessage(f"Selected content pixels on layer '{layer.name}'", 1500)

    def _apply_shortcuts(self) -> None:
        shortcuts = load_shortcuts()
        for act_id, shortcut_str in shortcuts.items():
            if act_id in self.actions_by_id:
                self.actions_by_id[act_id].setShortcut(QKeySequence(shortcut_str))

    def on_open_shortcuts_dialog(self) -> None:
        dlg = ShortcutsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._apply_shortcuts()

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
        if not self.maybe_save_changes(action_desc="creating a new canvas"):
            return
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
            self.canvas.selection.clear()
            self._push_history()
            self.canvas.set_document(self.doc)
            self.layer_panel.set_document(self.doc)
            self.appearance_panel.set_document(self.doc)
            self.animation_panel.set_document(self.doc)
            self.tag_panel.set_document(self.doc)
            self.align_panel.set_document(self.doc)
            self.path_panel.set_document(self.doc)
            self.tool_panel.select_tool_by_key("selection")
            self._clean_state_snapshot = copy.deepcopy(self.doc.to_dict())
            self.update_window_title()


    def open_file(self, filepath: str) -> bool:
        """Opens a .pix / .caml file directly from the given file path."""
        if not os.path.exists(filepath):
            # If target file does not exist yet, set it as active filepath for saving
            self.doc.filepath = filepath
            self._clean_state_snapshot = copy.deepcopy(self.doc.to_dict())
            self.update_window_title()
            return True
        try:
            self.doc = PixelDocument.load_from_pix(filepath)
            self.history.clear()
            self.canvas.selection.clear()
            self._push_history()
            self.canvas.set_document(self.doc)
            self.layer_panel.set_document(self.doc)
            self.appearance_panel.set_document(self.doc)
            self.animation_panel.set_document(self.doc)
            self.tag_panel.set_document(self.doc)
            self.align_panel.set_document(self.doc)
            self.path_panel.set_document(self.doc)

            self._clean_state_snapshot = copy.deepcopy(self.doc.to_dict())
            self.update_window_title()
            self.status_bar.showMessage(f"Opened {filepath}", 3000)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error Opening File", f"Failed to load file:\n{e}")
            return False

    def on_file_open(self) -> None:
        if not self.maybe_save_changes(action_desc="opening another file"):
            return
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Coopixel File", "", "Coopixel / CAML Files (*.pix *.caml);;All Files (*)"
        )
        if filepath:
            self.open_file(filepath)

    def on_file_save(self) -> bool:
        if self.doc.filepath:
            try:
                self.doc.save_to_pix(self.doc.filepath)
                self._clean_state_snapshot = copy.deepcopy(self.doc.to_dict())
                self.update_window_title()
                self.status_bar.showMessage("File saved successfully.", 3000)
                return True
            except Exception as e:
                QMessageBox.critical(self, "Error Saving File", f"Failed to save file:\n{e}")
                return False
        else:
            return self.on_file_save_as()

    def on_file_save_as(self) -> bool:
        default_name = self.doc.filepath if self.doc.filepath else "untitled.pix"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Coopixel File", default_name, "Coopixel Image (*.pix);;CAML File (*.caml)"
        )
        if filepath:
            try:
                self.doc.save_to_pix(filepath)
                self.doc.filepath = filepath
                self._clean_state_snapshot = copy.deepcopy(self.doc.to_dict())
                self.update_window_title()
                self.status_bar.showMessage("File saved successfully.", 3000)
                return True
            except Exception as e:
                QMessageBox.critical(self, "Error Saving File", f"Failed to save file:\n{e}")
                return False
        return False

    def on_file_import_png(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Image as Layer", "", "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        if filepath:
            img = QImage(filepath)
            if img.isNull():
                QMessageBox.warning(self, "Import Failed", "Could not load image file.")
                return

            dlg = ImportImageDialog(
                filepath,
                img_width=img.width(),
                img_height=img.height(),
                canvas_width=self.doc.width,
                canvas_height=self.doc.height,
                parent=self,
            )
            if dlg.exec() == ImportImageDialog.Accepted:
                layer_name, resize_canvas, scale_to_canvas = dlg.get_values()
                try:
                    layer = self.doc.import_image_as_layer(
                        filepath,
                        name=layer_name,
                        resize_canvas=resize_canvas,
                        scale_to_canvas=scale_to_canvas,
                    )
                    if layer:
                        self._push_history()
                        self.canvas.invalidate_cache()
                        self.canvas.center_canvas()
                        self.canvas.update()
                        self.layer_panel.refresh_list()
                        self.appearance_panel.refresh_panel()
                        self.animation_panel.refresh_timeline()
                        self.status_bar.showMessage(f"Imported {os.path.basename(filepath)} as layer '{layer.name}'", 3000)

                        # Record import_layer action
                        ext = os.path.splitext(filepath)[1].lstrip(".").upper() or "IMAGE"
                        filename = os.path.basename(filepath)
                        self.actions_panel.record_action(
                            action_type="import_layer",
                            params={
                                "filepath": filepath,
                                "filetype": ext,
                                "layer_name": layer_name,
                                "resize_canvas": resize_canvas,
                                "scale_to_canvas": scale_to_canvas,
                            },
                            display_name=f"Import Image ({filename})",
                            details=f"Format: {ext} | Layer: '{layer_name}' | Resize Canvas: {'Yes' if resize_canvas else 'No'} | Scale: {'Yes' if scale_to_canvas else 'No'}",
                        )
                except Exception as e:
                    QMessageBox.critical(self, "Import Error", f"Failed to import image:\n{e}")

    def on_file_import_spritesheet(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Spritesheet PNG", "", "PNG Images (*.png);;All Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        if not filepath:
            return

        img = QImage(filepath)
        if img.isNull():
            QMessageBox.warning(self, "Import Failed", "Could not load image file.")
            return

        dlg = SpritesheetImportDialog(filepath, img, active_doc=self.doc, parent=self)
        if dlg.exec() == QDialog.Accepted and dlg.result_document:
            self.doc = dlg.result_document
            self._push_history()
            self.canvas.invalidate_cache()
            self.canvas.center_canvas()
            self.canvas.update()
            self.layer_panel.refresh_list()
            self.appearance_panel.refresh_panel()
            self.animation_panel.set_document(self.doc)
            self.status_bar.showMessage(f"Imported spritesheet {os.path.basename(filepath)} successfully", 3000)

    def on_run_action(self, action_record: ActionRecord) -> None:
        """Handler for re-running a recorded action from the Actions Panel."""
        atype = action_record.action_type
        params = action_record.params

        if atype == "import_layer":
            filepath = params.get("filepath", "")
            if not os.path.exists(filepath):
                QMessageBox.warning(self, "Run Action Failed", f"Image file no longer exists at path:\n{filepath}")
                return
            layer_name = params.get("layer_name", "Imported Layer")
            resize_canvas = params.get("resize_canvas", False)
            scale_to_canvas = params.get("scale_to_canvas", False)

            try:
                layer = self.doc.import_image_as_layer(
                    filepath,
                    name=layer_name,
                    resize_canvas=resize_canvas,
                    scale_to_canvas=scale_to_canvas,
                )
                if layer:
                    self._push_history()
                    self.canvas.invalidate_cache()
                    self.canvas.center_canvas()
                    self.canvas.update()
                    self.layer_panel.refresh_list()
                    self.appearance_panel.refresh_panel()
                    self.animation_panel.refresh_timeline()
                    filename = os.path.basename(filepath)
                    self.status_bar.showMessage(f"Re-run: Imported {filename} as layer '{layer.name}'", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Action Error", f"Failed to re-run image import:\n{e}")

        elif atype == "crop_canvas":
            x = params.get("x", 0)
            y = params.get("y", 0)
            w = params.get("width", self.doc.width)
            h = params.get("height", self.doc.height)
            self.on_crop_committed(x, y, w, h, record=False)

        elif atype == "crop_layer":
            self.doc.crop_active_layer_to_canvas()
            self._push_history()
            self.canvas.invalidate_cache()
            self.canvas.update()
            self.layer_panel.refresh_list()
            self.status_bar.showMessage("Re-run: Cropped active layer to canvas", 2000)

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
