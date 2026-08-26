"""
Spritesheet Import Dialog for Coopixel.
Features:
  - Global Frame Dimensions setting (Width x Height) for all animations.
  - LHS Animation Manager (Multi-selection enabled, Hotkey 'N' to add animation, inherits layer name, tag, speed, and pivot point from previously selected animation).
  - RHS Top 70%: Spritesheet Viewer with multi-animation highlights, cell-based grid selection, frame pivot point crosshair rendering in every frame box, overlay buttons 🌐 & 🎯.
  - RHS Bottom 30%: Selected Animation Properties with Multi-Selection Bulk Editing (Bulk editable: Layer Name, Layer Tag, Pivot X/Y, Speed FPS; Greyed out during multi-selection: Animation Name, Position X/Y, Num Frames).
  - Clean removal of default 'Background' layers on import.
  - Confirmation prompt ("Are you sure?") before completing import.
"""

import os
from typing import List, Optional, Set, Tuple

from PySide6.QtCore import QPoint, QPointF, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QCursor,
    QFont,
    QImage,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from coopixel.models.document import PixelDocument
from coopixel.models.spritesheet_config import (
    DEFAULT_CONFIG_DIR,
    SpritesheetAnimationConfig,
    add_spritesheet_layers_to_document,
    build_document_from_spritesheet,
    load_spritesheet_configs,
    save_spritesheet_configs,
)


class SpritesheetViewer(QWidget):
    """Interactive canvas widget displaying the PNG spritesheet, cell-based selection, overlay buttons, animation bounds, frame split lines, and frame pivot point icons."""

    bounds_changed = Signal(int, int, int, int)  # Emitted when user drags/clicks cells (start_x, start_y, num_frames, 0)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self._image: Optional[QImage] = None
        self._pixmap: Optional[QPixmap] = None

        self._configs: List[SpritesheetAnimationConfig] = []
        self._selected_indices: Set[int] = set()
        self._global_fw: int = 32
        self._global_fh: int = 32
        self._show_grid: bool = True

        # Viewport zoom & pan transform
        self._zoom: float = 1.0
        self._pan_offset: QPoint = QPoint(0, 0)
        self._is_panning: bool = False
        self._pan_start: QPoint = QPoint(0, 0)
        self._initial_centered: bool = False

        # Cell hover & drag selection
        self._hover_cell: Optional[Tuple[int, int]] = None
        self._is_drawing: bool = False
        self._draw_start_cell: Tuple[int, int] = (0, 0)
        self._draw_current_cell: Tuple[int, int] = (0, 0)

        # Overlay buttons at bottom-right corner of viewer
        btn_style = (
            "QToolButton { background: #242424; border: 1px solid #383838; border-radius: 4px; padding: 2px 4px; font-size: 13px; color: #E2E8F0; }"
            "QToolButton:hover { background: #332B25; border-color: #F97316; color: #FFFFFF; }"
            "QToolButton:checked { background: #2E2620; border-color: #F97316; color: #F97316; font-weight: bold; }"
        )

        self.btn_grid = QToolButton(self)
        self.btn_grid.setText("🌐")
        self.btn_grid.setToolTip("Toggle Pixel and Frame Grid Overlay (Hotkey: G)")
        self.btn_grid.setCheckable(True)
        self.btn_grid.setChecked(True)
        self.btn_grid.setStyleSheet(btn_style)
        self.btn_grid.toggled.connect(self.set_show_grid)

        self.btn_reset = QToolButton(self)
        self.btn_reset.setText("🎯")
        self.btn_reset.setToolTip("Center / Reset View (Hotkey: A)")
        self.btn_reset.setStyleSheet(btn_style)
        self.btn_reset.clicked.connect(self.center_in_view)

    def set_image(self, image: QImage) -> None:
        self._image = image
        self._pixmap = QPixmap.fromImage(image) if image and not image.isNull() else None
        self._initial_centered = False
        self.center_in_view()
        self.update()

    def set_configs(
        self,
        configs: List[SpritesheetAnimationConfig],
        selected_indices: List[int],
        global_fw: int = 32,
        global_fh: int = 32,
    ) -> None:
        self._configs = configs
        if isinstance(selected_indices, int):
            self._selected_indices = {selected_indices}
        elif selected_indices is not None:
            self._selected_indices = set(selected_indices)
        else:
            self._selected_indices = set()
        self._global_fw = max(1, global_fw)
        self._global_fh = max(1, global_fh)
        self.update()

    def set_show_grid(self, show: bool) -> None:
        self._show_grid = show
        self.btn_grid.blockSignals(True)
        self.btn_grid.setChecked(show)
        self.btn_grid.blockSignals(False)
        self.update()

    def toggle_grid(self) -> None:
        self.set_show_grid(not self._show_grid)

    def fit_in_view(self) -> None:
        self.center_in_view()

    def center_in_view(self) -> None:
        """Centers and fits the image in the viewer, matching main canvas behavior (Hotkey: 'A')."""
        if not self._image or self._image.isNull():
            return
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        scale_w = (w - 40) / self._image.width()
        scale_h = (h - 40) / self._image.height()
        self._zoom = max(0.1, min(scale_w, scale_h, 16.0))
        img_center_x = (self._image.width() * self._zoom) / 2.0
        img_center_y = (self._image.height() * self._zoom) / 2.0
        self._pan_offset = QPoint(int(w / 2.0 - img_center_x), int(h / 2.0 - img_center_y))
        self.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self._auto_center)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reposition_overlay_buttons()
        if not self._initial_centered and self.width() > 0 and self.height() > 0:
            self.center_in_view()
            if self.width() > 300 and self.height() > 200:
                self._initial_centered = True

    def _reposition_overlay_buttons(self) -> None:
        if hasattr(self, "btn_grid") and hasattr(self, "btn_reset"):
            bw, bh = 30, 26
            pad = 10
            y = self.height() - bh - pad
            x_reset = self.width() - bw - pad
            x_grid = x_reset - bw - 4
            self.btn_grid.setGeometry(x_grid, y, bw, bh)
            self.btn_reset.setGeometry(x_reset, y, bw, bh)
            self.btn_grid.raise_()
            self.btn_reset.raise_()

    def _auto_center(self) -> None:
        if not self._initial_centered and self.width() > 0 and self.height() > 0:
            self.center_in_view()
            if self.width() > 300 and self.height() > 200:
                self._initial_centered = True

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_A:
            self.center_in_view()
            return
        elif event.key() == Qt.Key_G:
            self.toggle_grid()
            return
        super().keyPressEvent(event)

    def _widget_to_cell_coords(self, pt: QPoint) -> Tuple[int, int]:
        """Converts widget coordinates to grid cell column and row indices."""
        if self._zoom <= 0 or not self._image:
            return (0, 0)
        raw_x = (pt.x() - self._pan_offset.x()) / self._zoom
        raw_y = (pt.y() - self._pan_offset.y()) / self._zoom

        fw = max(1, self._global_fw)
        fh = max(1, self._global_fh)

        col = int(raw_x // fw)
        row = int(raw_y // fh)

        max_cols = max(1, (self._image.width() + fw - 1) // fw)
        max_rows = max(1, (self._image.height() + fh - 1) // fh)

        col = max(0, min(max_cols - 1, col))
        row = max(0, min(max_rows - 1, row))

        return (col, row)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not self._image:
            return
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1.0 / 1.15
        new_zoom = max(0.1, min(self._zoom * factor, 32.0))

        cursor_pos = event.position().toPoint()
        cell_col, cell_row = self._widget_to_cell_coords(cursor_pos)

        self._zoom = new_zoom
        self._pan_offset = QPoint(
            int(cursor_pos.x() - (cell_col * self._global_fw) * self._zoom),
            int(cursor_pos.y() - (cell_row * self._global_fh) * self._zoom),
        )
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._image:
            return
        # Panning on MiddleButton, RightButton, or Alt+LeftButton
        if event.button() in (Qt.MiddleButton, Qt.RightButton) or (
            event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier
        ):
            self._is_panning = True
            self._pan_start = event.pos()
            self.setCursor(QCursor(Qt.ClosedHandCursor))
        elif event.button() == Qt.LeftButton:
            cell_col, cell_row = self._widget_to_cell_coords(event.pos())
            fw = max(1, self._global_fw)
            fh = max(1, self._global_fh)
            img_w = self._image.width() if self._image else 8192

            cell_x = cell_col * fw
            cell_y = cell_row * fh

            # Get primary selected index if any
            primary_idx = next(iter(self._selected_indices)) if self._selected_indices else -1

            if 0 <= primary_idx < len(self._configs):
                curr_cfg = self._configs[primary_idx]

                if event.modifiers() & Qt.ControlModifier:
                    # Ctrl + Click: Append non-contiguous clicked cell to frame_cells sequence in order!
                    if not curr_cfg.frame_cells:
                        curr_cfg.frame_cells = curr_cfg.get_frame_positions(fw, fh, img_w=img_w)
                    curr_cfg.frame_cells.append((cell_x, cell_y))
                    curr_cfg.num_frames = len(curr_cfg.frame_cells)
                    curr_cfg.start_x = curr_cfg.frame_cells[0][0]
                    curr_cfg.start_y = curr_cfg.frame_cells[0][1]
                    self.bounds_changed.emit(curr_cfg.start_x, curr_cfg.start_y, curr_cfg.num_frames, 0)

                elif event.modifiers() & Qt.ShiftModifier:
                    # Shift + Click: Add contiguous cell range from animation start cell
                    sc = curr_cfg.start_x // fw
                    sr = curr_cfg.start_y // fh
                    cols_count = max(1, img_w // fw)

                    curr_cfg.frame_cells = None  # Reset to contiguous range
                    if cell_row == sr:
                        min_c, max_c = min(sc, cell_col), max(sc, cell_col)
                        start_x = min_c * fw
                        start_y = sr * fh
                        num_frames = max_c - min_c + 1
                    else:
                        min_c, max_c = min(sc, cell_col), max(sc, cell_col)
                        min_r, max_r = min(sr, cell_row), max(sr, cell_row)
                        start_x = min_c * fw
                        start_y = min_r * fh
                        num_frames = max(1, (max_c - min_c + 1) + (max_r - min_r) * cols_count)

                    self.bounds_changed.emit(start_x, start_y, num_frames, 0)

                else:
                    # Normal Click / Drag Start: Reset to single cell selection
                    curr_cfg.frame_cells = [(cell_x, cell_y)]
                    self._is_drawing = True
                    self._draw_start_cell = (cell_col, cell_row)
                    self._draw_current_cell = (cell_col, cell_row)
                    self.bounds_changed.emit(cell_x, cell_y, 1, 0)

            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._hover_cell = self._widget_to_cell_coords(event.pos())

        if self._is_panning:
            diff = event.pos() - self._pan_start
            self._pan_offset += diff
            self._pan_start = event.pos()
            self.update()
        elif self._is_drawing:
            cell_col, cell_row = self._widget_to_cell_coords(event.pos())
            self._draw_current_cell = (cell_col, cell_row)
            sc, sr = self._draw_start_cell
            fw = max(1, self._global_fw)
            fh = max(1, self._global_fh)
            img_w = self._image.width() if self._image else 8192

            cols_count = max(1, img_w // fw)
            primary_idx = next(iter(self._selected_indices)) if self._selected_indices else -1

            if 0 <= primary_idx < len(self._configs):
                curr_cfg = self._configs[primary_idx]
                curr_cfg.frame_cells = None  # Reset to contiguous range during drag

            if cell_row == sr:
                min_c, max_c = min(sc, cell_col), max(sc, cell_col)
                start_x = min_c * fw
                start_y = sr * fh
                num_frames = max_c - min_c + 1
            else:
                min_c, max_c = min(sc, cell_col), max(sc, cell_col)
                min_r, max_r = min(sr, cell_row), max(sr, cell_row)
                start_x = min_c * fw
                start_y = min_r * fh
                num_frames = max(1, (max_c - min_c + 1) + (max_r - min_r) * cols_count)

            self.bounds_changed.emit(start_x, start_y, num_frames, 0)
            self.update()
        else:
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() in (Qt.MiddleButton, Qt.RightButton) or self._is_panning:
            self._is_panning = False
            self.setCursor(QCursor(Qt.ArrowCursor))
        elif event.button() == Qt.LeftButton and self._is_drawing:
            self._is_drawing = False
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#0F172A"))  # Dark background

        if not self._image or not self._pixmap:
            painter.setPen(QColor("#64748B"))
            painter.drawText(self.rect(), Qt.AlignCenter, "No Spritesheet Image Loaded")
            return

        # 1. Draw Checkerboard background for image
        img_rect_screen = QRect(
            self._pan_offset.x(),
            self._pan_offset.y(),
            int(self._image.width() * self._zoom),
            int(self._image.height() * self._zoom),
        )

        painter.save()
        painter.setClipRect(img_rect_screen)

        tile_size = max(4, int(8 * self._zoom))
        for y in range(0, img_rect_screen.height(), tile_size):
            for x in range(0, img_rect_screen.width(), tile_size):
                col = QColor("#1E293B") if ((x // tile_size) + (y // tile_size)) % 2 == 0 else QColor("#334155")
                painter.fillRect(
                    img_rect_screen.x() + x,
                    img_rect_screen.y() + y,
                    min(tile_size, img_rect_screen.width() - x),
                    min(tile_size, img_rect_screen.height() - y),
                    col,
                )

        # 2. Draw Pixmap
        painter.drawPixmap(img_rect_screen, self._pixmap)

        # 3. Draw Grid Overlay if enabled
        if self._show_grid:
            img_w = self._image.width()
            img_h = self._image.height()
            fw = max(1, self._global_fw)
            fh = max(1, self._global_fh)

            # Fine pixel grid (when zoomed in)
            if self._zoom >= 4.0:
                painter.setPen(QPen(QColor(255, 255, 255, 25), 1))
                for px in range(1, img_w):
                    x_sc = int(self._pan_offset.x() + px * self._zoom)
                    painter.drawLine(x_sc, img_rect_screen.top(), x_sc, img_rect_screen.bottom())
                for py in range(1, img_h):
                    y_sc = int(self._pan_offset.y() + py * self._zoom)
                    painter.drawLine(img_rect_screen.left(), y_sc, img_rect_screen.right(), y_sc)

            # Global Cell Grid Lines
            painter.setPen(QPen(QColor(56, 189, 248, 100), 1, Qt.DashLine))
            for fx in range(fw, img_w, fw):
                x_sc = int(self._pan_offset.x() + fx * self._zoom)
                painter.drawLine(x_sc, img_rect_screen.top(), x_sc, img_rect_screen.bottom())

            for fy in range(fh, img_h, fh):
                y_sc = int(self._pan_offset.y() + fy * self._zoom)
                painter.drawLine(img_rect_screen.left(), y_sc, img_rect_screen.right(), y_sc)

        painter.restore()

        # Image border
        painter.setPen(QPen(QColor("#475569"), 1))
        painter.drawRect(img_rect_screen)

        fw = self._global_fw
        fh = self._global_fh
        img_w = self._image.width()

        # 4. Draw Hovered Cell Highlight
        if self._hover_cell and not self._is_panning:
            hc, hr = self._hover_cell
            rx = int(self._pan_offset.x() + hc * fw * self._zoom)
            ry = int(self._pan_offset.y() + hr * fh * self._zoom)
            rw = int(fw * self._zoom)
            rh = int(fh * self._zoom)
            hover_rect = QRect(rx, ry, rw, rh)
            painter.setPen(QPen(QColor("#38BDF8"), 1))
            painter.fillRect(hover_rect, QColor(56, 189, 248, 35))
            painter.drawRect(hover_rect)

        # 5. Draw Animation Bounding Boxes, Frame Cells, and Pivot Crosshairs
        font = QFont("sans-serif", max(8, int(10 * min(1.5, self._zoom))))
        painter.setFont(font)

        for idx, cfg in enumerate(self._configs):
            is_selected = idx in self._selected_indices
            frame_positions = cfg.get_frame_positions(fw, fh, img_w=img_w)
            pivot_x, pivot_y = cfg.get_pivot(fw, fh)

            if is_selected:
                # Active/Selected Animations: Draw each cell with highlight, frame index number, and pivot crosshair
                for f_idx, (fx, fy) in enumerate(frame_positions):
                    rx = int(self._pan_offset.x() + fx * self._zoom)
                    ry = int(self._pan_offset.y() + fy * self._zoom)
                    rw = int(fw * self._zoom)
                    rh = int(fh * self._zoom)

                    cell_rect = QRect(rx, ry, rw, rh)
                    painter.setPen(QPen(QColor("#F97316"), 2))
                    painter.drawRect(cell_rect)
                    painter.fillRect(cell_rect, QColor(249, 115, 22, 35))

                    lbl_rect = QRect(rx, ry, rw, min(20, rh))
                    painter.setPen(QColor("#38BDF8"))
                    painter.setFont(QFont("sans-serif", max(8, int(10 * min(1.5, self._zoom))), QFont.Bold))
                    painter.drawText(lbl_rect, Qt.AlignCenter, str(f_idx + 1))

                    # Always-visible Pivot Icon inside frame cell
                    p_cx = int(self._pan_offset.x() + (fx + pivot_x + 0.5) * self._zoom)
                    p_cy = int(self._pan_offset.y() + (fy + pivot_y + 0.5) * self._zoom)

                    painter.save()
                    painter.setRenderHint(QPainter.Antialiasing, True)
                    r_pin = max(4.0, min(12.0, self._zoom * 0.4))
                    painter.setPen(QPen(QColor(0, 0, 0, 180), 2))
                    painter.setBrush(QColor(249, 115, 22, 120))
                    painter.drawEllipse(QPointF(p_cx, p_cy), r_pin, r_pin)

                    painter.setPen(QPen(QColor("#F97316"), 1.5))
                    painter.drawEllipse(QPointF(p_cx, p_cy), r_pin, r_pin)

                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor("#38BDF8"))
                    painter.drawEllipse(QPointF(p_cx, p_cy), 2.5, 2.5)

                    painter.setPen(QPen(QColor("#F97316"), 1.5))
                    painter.drawLine(QPointF(p_cx - r_pin - 2, p_cy), QPointF(p_cx + r_pin + 2, p_cy))
                    painter.drawLine(QPointF(p_cx, p_cy - r_pin - 2), QPointF(p_cx, p_cy + r_pin + 2))
                    painter.restore()

                # Name Tag Label above first cell
                if frame_positions:
                    first_x, first_y = frame_positions[0]
                    rx = int(self._pan_offset.x() + first_x * self._zoom)
                    ry = int(self._pan_offset.y() + first_y * self._zoom)
                    tag_rect = QRect(rx, max(0, ry - 20), max(80, int(fw * self._zoom)), 20)
                    painter.fillRect(tag_rect, QColor("#F97316"))
                    painter.setPen(QColor("#FFFFFF"))
                    painter.setFont(QFont("sans-serif", 9, QFont.Bold))
                    painter.drawText(tag_rect, Qt.AlignCenter, f"{cfg.name} ({len(frame_positions)}f)")

            else:
                # Inactive Animation: Draw subtle boxes around cells & pivot pins
                for f_idx, (fx, fy) in enumerate(frame_positions):
                    rx = int(self._pan_offset.x() + fx * self._zoom)
                    ry = int(self._pan_offset.y() + fy * self._zoom)
                    rw = int(fw * self._zoom)
                    rh = int(fh * self._zoom)

                    cell_rect = QRect(rx, ry, rw, rh)
                    painter.setPen(QPen(QColor("#64748B"), 1, Qt.DashLine))
                    painter.drawRect(cell_rect)

                    # Pivot Pin for inactive animation
                    p_cx = int(self._pan_offset.x() + (fx + pivot_x + 0.5) * self._zoom)
                    p_cy = int(self._pan_offset.y() + (fy + pivot_y + 0.5) * self._zoom)

                    painter.save()
                    painter.setRenderHint(QPainter.Antialiasing, True)
                    r_pin = max(3.5, min(9.0, self._zoom * 0.35))
                    painter.setPen(QPen(QColor("#64748B"), 1))
                    painter.setBrush(QColor(100, 116, 139, 60))
                    painter.drawEllipse(QPointF(p_cx, p_cy), r_pin, r_pin)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor("#94A3B8"))
                    painter.drawEllipse(QPointF(p_cx, p_cy), 2.0, 2.0)
                    painter.restore()

                if frame_positions:
                    first_x, first_y = frame_positions[0]
                    rx = int(self._pan_offset.x() + first_x * self._zoom)
                    ry = int(self._pan_offset.y() + first_y * self._zoom)
                    tag_rect = QRect(rx, max(0, ry - 18), max(60, int(fw * self._zoom)), 18)
                    painter.fillRect(tag_rect, QColor(30, 41, 59, 200))
                    painter.setPen(QColor("#94A3B8"))
                    painter.setFont(QFont("sans-serif", 8))
                    painter.drawText(tag_rect, Qt.AlignCenter, cfg.name)

        # 6. Draw Cell Drag Selection Box
        if self._is_drawing:
            sc, sr = self._draw_start_cell
            ec, er = self._draw_current_cell

            cols_count = max(1, img_w // max(1, fw))
            if er == sr:
                min_c, max_c = min(sc, ec), max(sc, ec)
                rx = int(self._pan_offset.x() + min_c * fw * self._zoom)
                ry = int(self._pan_offset.y() + sr * fh * self._zoom)
                rw = int((max_c - min_c + 1) * fw * self._zoom)
                rh = int(fh * self._zoom)
            else:
                min_c, max_c = min(sc, ec), max(sc, ec)
                min_r, max_r = min(sr, er), max(sr, er)
                rx = int(self._pan_offset.x() + min_c * fw * self._zoom)
                ry = int(self._pan_offset.y() + min_r * fh * self._zoom)
                n_cells = (max_c - min_c + 1) + (max_r - min_r) * cols_count
                rw = int(n_cells * fw * self._zoom)
                rh = int(fh * self._zoom)

            drag_rect = QRect(rx, ry, rw, rh)
            painter.setPen(QPen(QColor("#22C55E"), 2, Qt.DashLine))
            painter.drawRect(drag_rect)
            painter.fillRect(drag_rect, QColor(34, 197, 94, 40))


class AnimationOptionsWidget(QGroupBox):
    """Panel displaying and editing properties of single or multiple selected animations (bulk editing)."""

    options_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Selected Animation Properties", parent)
        self._selected_configs: List[SpritesheetAnimationConfig] = []
        self._global_fw: int = 32
        self._global_fh: int = 32
        self._updating: bool = False

        self.setStyleSheet(
            "QGroupBox { font-weight: bold; color: #E2E8F0; }"
            "QLabel { color: #E2E8F0; }"
            "QLabel:disabled { color: #64748B; }"
            "QLineEdit { background: #1E293B; color: #F8FAFC; border: 1px solid #475569; border-radius: 4px; padding: 3px; }"
            "QLineEdit:disabled { background: #0F172A; color: #64748B; border-color: #334155; }"
            "QSpinBox { background: #1E293B; color: #F8FAFC; border: 1px solid #475569; border-radius: 4px; padding: 3px; }"
            "QSpinBox:disabled { background: #0F172A; color: #64748B; border-color: #334155; }"
        )

        layout = QFormLayout(self)
        layout.setSpacing(8)

        self.lbl_name = QLabel("Animation Name:")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("animation_name")

        self.lbl_layer_name = QLabel("Imported Layer Name:")
        self.layer_name_edit = QLineEdit()
        self.layer_name_edit.setPlaceholderText("Layer 1")

        self.lbl_tag = QLabel("Imported Layer Tag:")
        self.tag_edit = QLineEdit()
        self.tag_edit.setPlaceholderText("default")

        self.lbl_pos_x = QLabel("First Frame X:")
        self.start_x_spin = QSpinBox()
        self.start_x_spin.setRange(0, 8192)

        self.lbl_pos_y = QLabel("First Frame Y:")
        self.start_y_spin = QSpinBox()
        self.start_y_spin.setRange(0, 8192)

        self.lbl_pivot_x = QLabel("Pivot X:")
        self.pivot_x_spin = QSpinBox()
        self.pivot_x_spin.setRange(-8192, 8192)
        self.pivot_x_spin.setSuffix(" px")

        self.lbl_pivot_y = QLabel("Pivot Y:")
        self.pivot_y_spin = QSpinBox()
        self.pivot_y_spin.setRange(-8192, 8192)
        self.pivot_y_spin.setSuffix(" px")

        self.lbl_num_frames = QLabel("Num Frames:")
        self.num_frames_spin = QSpinBox()
        self.num_frames_spin.setRange(1, 256)
        self.num_frames_spin.setValue(1)

        self.lbl_speed = QLabel("Speed:")
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(10)
        self.fps_spin.setSuffix(" fps")

        self.size_info_label = QLabel("Frame Size: 32 × 32 px | Total Region: 32 × 32 px")
        self.size_info_label.setStyleSheet("color: #38BDF8; font-weight: bold;")

        self.lbl_pos = QLabel("Position:")
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(self.lbl_pos_x)
        pos_layout.addWidget(self.start_x_spin)
        pos_layout.addWidget(self.lbl_pos_y)
        pos_layout.addWidget(self.start_y_spin)

        self.lbl_pivot = QLabel("Pivot Point:")
        pivot_layout = QHBoxLayout()
        pivot_layout.addWidget(self.lbl_pivot_x)
        pivot_layout.addWidget(self.pivot_x_spin)
        pivot_layout.addWidget(self.lbl_pivot_y)
        pivot_layout.addWidget(self.pivot_y_spin)

        layout.addRow(self.lbl_name, self.name_edit)
        layout.addRow(self.lbl_layer_name, self.layer_name_edit)
        layout.addRow(self.lbl_tag, self.tag_edit)
        layout.addRow(self.lbl_pos, pos_layout)
        layout.addRow(self.lbl_pivot, pivot_layout)
        layout.addRow(self.lbl_num_frames, self.num_frames_spin)
        layout.addRow(self.lbl_speed, self.fps_spin)
        layout.addRow("Dimensions:", self.size_info_label)

        # Connect signals
        self.name_edit.textChanged.connect(self._on_field_changed)
        self.layer_name_edit.textChanged.connect(self._on_field_changed)
        self.tag_edit.textChanged.connect(self._on_field_changed)
        self.start_x_spin.valueChanged.connect(self._on_field_changed)
        self.start_y_spin.valueChanged.connect(self._on_field_changed)
        self.pivot_x_spin.valueChanged.connect(self._on_field_changed)
        self.pivot_y_spin.valueChanged.connect(self._on_field_changed)
        self.num_frames_spin.valueChanged.connect(self._on_field_changed)
        self.fps_spin.valueChanged.connect(self._on_field_changed)

    def set_configs(
        self,
        configs: List[SpritesheetAnimationConfig],
        global_fw: int = 32,
        global_fh: int = 32,
        max_img_w: int = 8192,
        max_img_h: int = 8192,
        default_layer_name: str = "Layer 1",
    ) -> None:
        self._selected_configs = configs
        self._global_fw = max(1, global_fw)
        self._global_fh = max(1, global_fh)
        self._updating = True

        self.start_x_spin.setMaximum(max_img_w)
        self.start_y_spin.setMaximum(max_img_h)

        if not configs:
            self.setEnabled(False)
            self.name_edit.setText("")
            self.layer_name_edit.setText("")
            self.tag_edit.setText("default")
            self.start_x_spin.setValue(0)
            self.start_y_spin.setValue(0)
            self.pivot_x_spin.setValue(self._global_fw // 2)
            self.pivot_y_spin.setValue(self._global_fh // 2)
            self.num_frames_spin.setValue(1)
            self.fps_spin.setValue(10)
            self.size_info_label.setText("Frame Size: N/A")

        elif len(configs) == 1:
            # Single-selection mode: All fields ENABLED
            config = configs[0]
            self.setEnabled(True)

            self.lbl_name.setEnabled(True)
            self.name_edit.setEnabled(True)

            self.lbl_pos.setEnabled(True)
            self.lbl_pos_x.setEnabled(True)
            self.start_x_spin.setEnabled(True)
            self.lbl_pos_y.setEnabled(True)
            self.start_y_spin.setEnabled(True)

            self.lbl_num_frames.setEnabled(True)
            self.num_frames_spin.setEnabled(True)

            self.lbl_layer_name.setEnabled(True)
            self.layer_name_edit.setEnabled(True)

            self.lbl_tag.setEnabled(True)
            self.tag_edit.setEnabled(True)

            self.lbl_pivot.setEnabled(True)
            self.lbl_pivot_x.setEnabled(True)
            self.pivot_x_spin.setEnabled(True)
            self.lbl_pivot_y.setEnabled(True)
            self.pivot_y_spin.setEnabled(True)

            self.lbl_speed.setEnabled(True)
            self.fps_spin.setEnabled(True)

            self.name_edit.setText(config.name)
            self.layer_name_edit.setText(config.layer_name or default_layer_name)
            self.tag_edit.setText(config.tag or "default")
            self.start_x_spin.setValue(config.start_x)
            self.start_y_spin.setValue(config.start_y)
            px, py = config.get_pivot(self._global_fw, self._global_fh)
            self.pivot_x_spin.setValue(px)
            self.pivot_y_spin.setValue(py)
            self.num_frames_spin.setValue(config.num_frames)
            self.fps_spin.setValue(config.fps)
            self._update_info_label()

        else:
            # Multi-selection bulk editing mode!
            # Enable ONLY bulk editable fields & labels: layer_name_edit, tag_edit, pivot_x_spin, pivot_y_spin, fps_spin.
            # Grey out non-bulk fields & labels: name_edit, pos labels/spins, num_frames label/spin.
            self.setEnabled(True)

            self.lbl_name.setEnabled(False)
            self.name_edit.setEnabled(False)
            self.name_edit.setText("[Multiple Animations Selected]")

            self.lbl_pos.setEnabled(False)
            self.lbl_pos_x.setEnabled(False)
            self.start_x_spin.setEnabled(False)
            self.lbl_pos_y.setEnabled(False)
            self.start_y_spin.setEnabled(False)

            self.lbl_num_frames.setEnabled(False)
            self.num_frames_spin.setEnabled(False)

            self.lbl_layer_name.setEnabled(True)
            self.layer_name_edit.setEnabled(True)

            self.lbl_tag.setEnabled(True)
            self.tag_edit.setEnabled(True)

            self.lbl_pivot.setEnabled(True)
            self.lbl_pivot_x.setEnabled(True)
            self.pivot_x_spin.setEnabled(True)
            self.lbl_pivot_y.setEnabled(True)
            self.pivot_y_spin.setEnabled(True)

            self.lbl_speed.setEnabled(True)
            self.fps_spin.setEnabled(True)

            layer_names = {c.layer_name for c in configs}
            if len(layer_names) == 1:
                self.layer_name_edit.setText(next(iter(layer_names)))
            else:
                self.layer_name_edit.setText("")
                self.layer_name_edit.setPlaceholderText("Multiple Values")

            tags = {c.tag for c in configs}
            if len(tags) == 1:
                self.tag_edit.setText(next(iter(tags)))
            else:
                self.tag_edit.setText("")
                self.tag_edit.setPlaceholderText("Multiple Values")

            pivots = {c.get_pivot(self._global_fw, self._global_fh) for c in configs}
            first_px, first_py = configs[0].get_pivot(self._global_fw, self._global_fh)
            self.pivot_x_spin.setValue(first_px)
            self.pivot_y_spin.setValue(first_py)

            fps_vals = {c.fps for c in configs}
            self.fps_spin.setValue(configs[0].fps if len(fps_vals) == 1 else 10)

            self.size_info_label.setText(
                f"Selected Animations: {len(configs)}  |  Bulk Editing Layer Name, Tag, Pivot & Speed"
            )

        self._updating = False

    def focus_layer_name(self) -> None:
        """Focuses and highlights the Imported Layer Name text edit box."""
        if self.layer_name_edit.isEnabled():
            self.layer_name_edit.setFocus()
            self.layer_name_edit.selectAll()

    def update_start_pos(self, start_x: int, start_y: int, num_frames: int) -> None:
        if len(self._selected_configs) == 1:
            self._updating = True
            self.start_x_spin.setValue(start_x)
            self.start_y_spin.setValue(start_y)
            if num_frames > 0:
                self.num_frames_spin.setValue(num_frames)
            self._updating = False
            self._on_field_changed()

    def _update_info_label(self) -> None:
        if len(self._selected_configs) == 1:
            cfg = self._selected_configs[0]
            total_w = cfg.num_frames * self._global_fw
            self.size_info_label.setText(
                f"Frame Size: {self._global_fw} × {self._global_fh} px  |  Total Region: {total_w} × {self._global_fh} px"
            )

    def sync_current_options(self) -> None:
        """Flushes widget input values directly to selected config objects."""
        if not self._selected_configs or self._updating:
            return

        if len(self._selected_configs) == 1:
            cfg = self._selected_configs[0]
            name_val = self.name_edit.text().strip()
            if name_val and name_val != "[Multiple Animations Selected]":
                cfg.name = name_val
            layer_val = self.layer_name_edit.text().strip()
            if layer_val:
                cfg.layer_name = layer_val
            tag_val = self.tag_edit.text().strip() or "default"
            cfg.tag = tag_val
            cfg.start_x = self.start_x_spin.value()
            cfg.start_y = self.start_y_spin.value()
            cfg.pivot_x = self.pivot_x_spin.value()
            cfg.pivot_y = self.pivot_y_spin.value()
            cfg.num_frames = self.num_frames_spin.value()
            cfg.fps = self.fps_spin.value()

        elif len(self._selected_configs) > 1:
            # Bulk editing mode!
            layer_val = self.layer_name_edit.text().strip()
            tag_val = self.tag_edit.text().strip() or "default"
            px_val = self.pivot_x_spin.value()
            py_val = self.pivot_y_spin.value()
            fps_val = self.fps_spin.value()

            for cfg in self._selected_configs:
                if layer_val:
                    cfg.layer_name = layer_val
                cfg.tag = tag_val
                cfg.pivot_x = px_val
                cfg.pivot_y = py_val
                cfg.fps = fps_val

    def _on_field_changed(self) -> None:
        if self._updating or not self._selected_configs:
            return

        self.sync_current_options()
        self._update_info_label()
        self.options_changed.emit()


class AnimationManagerWidget(QWidget):
    """LHS panel for managing list of animations, global frame size, and .pixpref configs."""

    selection_changed = Signal(list)  # Emits list of selected indices [int]
    configs_updated = Signal()
    global_size_changed = Signal(int, int)

    def __init__(self, default_layer_name: str = "Layer 1", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.configs: List[SpritesheetAnimationConfig] = []
        self.default_layer_name = default_layer_name

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Spritesheet Animations")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #F1F5F9;")
        layout.addWidget(title)

        # Global Frame Dimensions Section
        global_group = QGroupBox("Global Animation Frame Size")
        global_layout = QHBoxLayout(global_group)

        self.global_w_spin = QSpinBox()
        self.global_w_spin.setRange(1, 4096)
        self.global_w_spin.setValue(32)
        self.global_w_spin.setSuffix(" px")

        self.global_h_spin = QSpinBox()
        self.global_h_spin.setRange(1, 4096)
        self.global_h_spin.setValue(32)
        self.global_h_spin.setSuffix(" px")

        global_layout.addWidget(QLabel("Width:"))
        global_layout.addWidget(self.global_w_spin)
        global_layout.addWidget(QLabel("Height:"))
        global_layout.addWidget(self.global_h_spin)

        self.global_w_spin.valueChanged.connect(self._on_global_size_changed)
        self.global_h_spin.valueChanged.connect(self._on_global_size_changed)
        layout.addWidget(global_group)

        # Animation List (Extended Multi-Selection)
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget)

        # Buttons row
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("+ Add (N)")
        self.add_btn.setToolTip("Add new animation inheriting current layer name, tag & pivot point (Hotkey: N)")
        self.add_btn.clicked.connect(self.on_add_anim)

        self.del_btn = QPushButton("- Delete")
        self.del_btn.clicked.connect(self.on_delete_anim)

        self.dup_btn = QPushButton("Duplicate")
        self.dup_btn.clicked.connect(self.on_duplicate_anim)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.del_btn)
        btn_layout.addWidget(self.dup_btn)
        layout.addLayout(btn_layout)

        # Config File Group
        cfg_group = QGroupBox("Configuration (.pixpref)")
        cfg_layout = QHBoxLayout(cfg_group)
        self.save_cfg_btn = QPushButton("Save Config...")
        self.save_cfg_btn.clicked.connect(self.on_save_config)
        self.load_cfg_btn = QPushButton("Load Config...")
        self.load_cfg_btn.clicked.connect(self.on_load_config)

        cfg_layout.addWidget(self.save_cfg_btn)
        cfg_layout.addWidget(self.load_cfg_btn)
        layout.addWidget(cfg_group)

        # Import Settings Group
        settings_group = QGroupBox("Import Options")
        settings_form = QFormLayout(settings_group)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Add Layer to Active Document / Animations", "Create New Document"])

        settings_form.addRow("Target Mode:", self.mode_combo)
        layout.addWidget(settings_group)

        # Initialize with default animation
        self.configs.append(
            SpritesheetAnimationConfig(name="idle", layer_name=default_layer_name, tag="default", start_x=0, start_y=0, num_frames=4, fps=10)
        )
        self.refresh_list()

    @property
    def global_fw(self) -> int:
        return self.global_w_spin.value()

    @property
    def global_fh(self) -> int:
        return self.global_h_spin.value()

    def set_global_size(self, fw: int, fh: int) -> None:
        self.global_w_spin.blockSignals(True)
        self.global_h_spin.blockSignals(True)
        self.global_w_spin.setValue(max(1, fw))
        self.global_h_spin.setValue(max(1, fh))
        self.global_w_spin.blockSignals(False)
        self.global_h_spin.blockSignals(False)
        self._on_global_size_changed()

    def _on_global_size_changed(self) -> None:
        self.update_item_labels()
        self.global_size_changed.emit(self.global_fw, self.global_fh)

    def update_item_labels(self) -> None:
        """Updates list item labels in place without clear() or selection signal loops."""
        self.list_widget.blockSignals(True)
        for i, cfg in enumerate(self.configs):
            if i < self.list_widget.count():
                self.list_widget.item(i).setText(f"🎬 {cfg.name} [{cfg.layer_name}] (tag:{cfg.tag}) ({cfg.num_frames}f @ ({cfg.start_x},{cfg.start_y}))")
        self.list_widget.blockSignals(False)

    def refresh_list(self) -> None:
        curr_indices = self.get_selected_indices()
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        for cfg in self.configs:
            item = QListWidgetItem(f"🎬 {cfg.name} [{cfg.layer_name}] (tag:{cfg.tag}) ({cfg.num_frames}f @ ({cfg.start_x},{cfg.start_y}))")
            self.list_widget.addItem(item)

        self.list_widget.blockSignals(False)

        if self.configs:
            target_indices = [i for i in curr_indices if 0 <= i < len(self.configs)]
            if not target_indices:
                target_indices = [0]
            self.list_widget.blockSignals(True)
            self.list_widget.setCurrentRow(target_indices[0])
            for idx in target_indices:
                if idx < self.list_widget.count():
                    self.list_widget.item(idx).setSelected(True)
            self.list_widget.blockSignals(False)
        self._on_selection_changed()

    def _on_selection_changed(self) -> None:
        indices = self.get_selected_indices()
        self.del_btn.setEnabled(len(self.configs) > 1 and len(indices) > 0)
        self.selection_changed.emit(indices)

    def get_selected_indices(self) -> List[int]:
        return [item.row() for item in self.list_widget.selectedIndexes()]

    def get_selected_configs(self) -> List[SpritesheetAnimationConfig]:
        indices = self.get_selected_indices()
        return [self.configs[i] for i in indices if 0 <= i < len(self.configs)]

    def get_selected_config(self) -> Optional[SpritesheetAnimationConfig]:
        sel = self.get_selected_configs()
        return sel[0] if sel else (self.configs[0] if self.configs else None)

    def on_add_anim(self) -> None:
        """Adds a new animation, copying pivot point, layer name, tag, and speed from last selected animation."""
        new_name = f"anim_{len(self.configs) + 1}"

        sel_cfgs = self.get_selected_configs()
        last_cfg = sel_cfgs[-1] if sel_cfgs else (self.configs[-1] if self.configs else None)

        layer_name = last_cfg.layer_name if last_cfg else self.default_layer_name
        tag_val = last_cfg.tag if last_cfg else "default"
        px, py = last_cfg.get_pivot(self.global_fw, self.global_fh) if last_cfg else (self.global_fw // 2, self.global_fh // 2)
        fps_val = last_cfg.fps if last_cfg else 10

        new_cfg = SpritesheetAnimationConfig(
            name=new_name,
            layer_name=layer_name,
            tag=tag_val,
            start_x=0,
            start_y=0,
            num_frames=1,
            fps=fps_val,
            pivot_x=px,
            pivot_y=py,
        )
        self.configs.append(new_cfg)
        self.refresh_list()
        new_idx = len(self.configs) - 1
        self.list_widget.blockSignals(True)
        self.list_widget.clearSelection()
        self.list_widget.setCurrentRow(new_idx)
        if new_idx < self.list_widget.count():
            self.list_widget.item(new_idx).setSelected(True)
        self.list_widget.blockSignals(False)
        self._on_selection_changed()
        self.configs_updated.emit()

    def on_delete_anim(self) -> None:
        indices = sorted(self.get_selected_indices(), reverse=True)
        if len(self.configs) > len(indices) and len(indices) > 0:
            for idx in indices:
                if 0 <= idx < len(self.configs):
                    del self.configs[idx]
            self.refresh_list()
            self.configs_updated.emit()

    def on_duplicate_anim(self) -> None:
        indices = sorted(self.get_selected_indices())
        if indices:
            insert_pos = indices[-1] + 1
            for idx in indices:
                if 0 <= idx < len(self.configs):
                    src = self.configs[idx]
                    dup = SpritesheetAnimationConfig(
                        name=f"{src.name}_copy",
                        layer_name=src.layer_name,
                        tag=src.tag,
                        start_x=src.start_x,
                        start_y=src.start_y,
                        num_frames=src.num_frames,
                        fps=src.fps,
                        pivot_x=src.pivot_x,
                        pivot_y=src.pivot_y,
                        frame_cells=list(src.frame_cells) if src.frame_cells else None,
                    )
                    self.configs.insert(insert_pos, dup)
                    insert_pos += 1
            self.refresh_list()
            self.configs_updated.emit()

    def on_save_config(self) -> None:
        os.makedirs(DEFAULT_CONFIG_DIR, exist_ok=True)
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Animation Config (.pixpref)",
            os.path.join(DEFAULT_CONFIG_DIR, "spritesheet.pixpref"),
            "Coopixel Prefs (*.pixpref);;YAML Files (*.yaml *.yml);;All Files (*)",
        )
        if filepath:
            if not filepath.endswith(".pixpref") and not filepath.endswith(".yaml") and not filepath.endswith(".yml"):
                filepath += ".pixpref"
            try:
                save_spritesheet_configs(filepath, self.configs, global_frame_width=self.global_fw, global_frame_height=self.global_fh)
                QMessageBox.information(self, "Config Saved", f"Saved configuration to:\n{filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save config file:\n{e}")

    def on_load_config(self) -> None:
        os.makedirs(DEFAULT_CONFIG_DIR, exist_ok=True)
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Load Animation Config (.pixpref)",
            DEFAULT_CONFIG_DIR,
            "Coopixel Prefs (*.pixpref);;YAML Files (*.yaml *.yml);;All Files (*)",
        )
        if filepath:
            try:
                loaded, fw, fh = load_spritesheet_configs(filepath)
                if loaded:
                    self.configs = loaded
                    self.set_global_size(fw, fh)
                    self.refresh_list()
                    self.configs_updated.emit()
                    QMessageBox.information(self, "Config Loaded", f"Loaded {len(loaded)} animation configs from:\n{filepath}")
                else:
                    QMessageBox.warning(self, "Empty Config", "No valid animation configurations found in file.")
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Failed to load config file:\n{e}")


class SpritesheetImportDialog(QDialog):
    """Main Spritesheet Import Window / Dialog."""

    def __init__(self, filepath: str, image: QImage, active_doc: Optional[PixelDocument] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle(f"Import Spritesheet - {os.path.basename(filepath)}")
        self.resize(1080, 720)

        self.filepath = filepath
        self.image = image
        self.active_doc = active_doc
        self.result_document: Optional[PixelDocument] = None

        default_layer_name = os.path.splitext(os.path.basename(filepath))[0] or "Layer 1"

        main_layout = QVBoxLayout(self)

        main_splitter = QSplitter(Qt.Horizontal)

        # LHS Animation Manager
        self.manager_widget = AnimationManagerWidget(default_layer_name=default_layer_name, parent=self)
        self.manager_widget.setMinimumWidth(340)
        main_splitter.addWidget(self.manager_widget)

        # RHS Splitter (Top 70% Viewer Widget, Bottom 30% Options)
        self.rhs_splitter = QSplitter(Qt.Vertical)

        self.viewer_widget = SpritesheetViewer(parent=self)
        self.viewer_widget.set_image(image)

        self.options_widget = AnimationOptionsWidget(parent=self)

        self.rhs_splitter.addWidget(self.viewer_widget)
        self.rhs_splitter.addWidget(self.options_widget)
        self.rhs_splitter.setStretchFactor(0, 7)  # 70%
        self.rhs_splitter.setStretchFactor(1, 3)  # 30%

        main_splitter.addWidget(self.rhs_splitter)
        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 7)

        main_layout.addWidget(main_splitter)

        # Bottom Actions
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Import Spritesheet")
        buttons.accepted.connect(self.on_accept_import)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        # Shortcut 'N' for New Animation
        self.add_anim_act = QAction("New Animation", self)
        self.add_anim_act.setShortcut(QKeySequence("N"))
        self.add_anim_act.setShortcutContext(Qt.WindowShortcut)
        self.add_anim_act.triggered.connect(self._on_shortcut_new_anim)
        self.addAction(self.add_anim_act)

        # Wire Signals
        self.manager_widget.selection_changed.connect(self._on_selection_changed)
        self.manager_widget.configs_updated.connect(self._on_configs_updated)
        self.manager_widget.global_size_changed.connect(self._on_global_size_changed)
        self.options_widget.options_changed.connect(self._on_options_changed)
        self.viewer_widget.bounds_changed.connect(self._on_viewer_bounds_changed)

        # Sync initial state
        self._on_selection_changed(self.manager_widget.get_selected_indices())

    def _on_shortcut_new_anim(self) -> None:
        # Only trigger new animation if user is not currently typing in a line edit
        focused = self.focusWidget()
        if focused and isinstance(focused, QLineEdit):
            return
        self.manager_widget.on_add_anim()
        self.options_widget.focus_layer_name()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        total_h = self.rhs_splitter.height()
        if total_h > 0:
            self.rhs_splitter.setSizes([int(total_h * 0.70), int(total_h * 0.30)])

    def _on_selection_changed(self, indices: List[int]) -> None:
        configs = [self.manager_widget.configs[i] for i in indices if 0 <= i < len(self.manager_widget.configs)]
        img_w = self.image.width() if self.image else 8192
        img_h = self.image.height() if self.image else 8192
        fw = self.manager_widget.global_fw
        fh = self.manager_widget.global_fh
        self.options_widget.set_configs(
            configs,
            global_fw=fw,
            global_fh=fh,
            max_img_w=img_w,
            max_img_h=img_h,
            default_layer_name=self.manager_widget.default_layer_name,
        )
        self.viewer_widget.set_configs(self.manager_widget.configs, selected_indices=indices, global_fw=fw, global_fh=fh)

    def _on_global_size_changed(self, fw: int, fh: int) -> None:
        indices = self.manager_widget.get_selected_indices()
        configs = [self.manager_widget.configs[i] for i in indices if 0 <= i < len(self.manager_widget.configs)]
        img_w = self.image.width() if self.image else 8192
        img_h = self.image.height() if self.image else 8192
        self.options_widget.set_configs(
            configs,
            global_fw=fw,
            global_fh=fh,
            max_img_w=img_w,
            max_img_h=img_h,
            default_layer_name=self.manager_widget.default_layer_name,
        )
        self.viewer_widget.set_configs(self.manager_widget.configs, selected_indices=indices, global_fw=fw, global_fh=fh)

    def _on_configs_updated(self) -> None:
        indices = self.manager_widget.get_selected_indices()
        fw = self.manager_widget.global_fw
        fh = self.manager_widget.global_fh
        self.viewer_widget.set_configs(self.manager_widget.configs, selected_indices=indices, global_fw=fw, global_fh=fh)

    def _on_options_changed(self) -> None:
        self.manager_widget.update_item_labels()
        indices = self.manager_widget.get_selected_indices()
        fw = self.manager_widget.global_fw
        fh = self.manager_widget.global_fh
        self.viewer_widget.set_configs(self.manager_widget.configs, selected_indices=indices, global_fw=fw, global_fh=fh)

    def _on_viewer_bounds_changed(self, start_x: int, start_y: int, num_frames: int, _) -> None:
        self.options_widget.update_start_pos(start_x, start_y, num_frames)

    def on_accept_import(self) -> None:
        self.options_widget.sync_current_options()

        configs = self.manager_widget.configs
        if not configs:
            QMessageBox.warning(self, "No Animations", "Please define at least one animation configuration.")
            return

        # Confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirm Import",
            "Are you sure you want to import these spritesheet animations?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return

        target_mode = self.manager_widget.mode_combo.currentText()
        fw = self.manager_widget.global_fw
        fh = self.manager_widget.global_fh

        try:
            if target_mode.startswith("Add Layer") and self.active_doc is not None:
                self.result_document = add_spritesheet_layers_to_document(
                    doc=self.active_doc,
                    img=self.image,
                    configs=configs,
                    global_frame_width=fw,
                    global_frame_height=fh,
                )
            else:
                self.result_document = build_document_from_spritesheet(
                    img=self.image,
                    configs=configs,
                    global_frame_width=fw,
                    global_frame_height=fh,
                )

            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"An error occurred while importing spritesheet:\n{e}")
