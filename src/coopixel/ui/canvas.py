"""
Interactive Pixel Canvas Widget for Coopixel.
Handles zooming, panning, grid rendering, checkerboard background, tool interaction, and live preview.
"""

from typing import Dict, Optional, Set, Tuple
from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, Signal, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QImage,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QTransform,
    QWheelEvent,
)

from PySide6.QtWidgets import QWidget
from coopixel.models.document import PixelDocument, hex_to_qcolor, qcolor_to_hex
from coopixel.models.selection import SelectionModel
from coopixel.tools.base import Tool
from coopixel.tools.crop import CropTool
from coopixel.tools.move import MoveTool
from coopixel.tools.pen import PenTool
from coopixel.tools.pivot import PivotTool
from coopixel.tools.selection import SelectionTool



class CanvasWidget(QWidget):
    cursor_moved = Signal(int, int)
    # Emitted when a complete drawing stroke finishes (mouse_release) — triggers history push
    stroke_committed = Signal()
    # Emitted on live pixel changes during a stroke (mouse_move) — triggers repaint only, NO history
    canvas_updated = Signal()
    # Emitted when a crop box is committed via canvas interaction (Enter / double-click)
    crop_committed = Signal(int, int, int, int)
    # Emitted whenever the crop box changes (drag live update) — carries (x, y, w, h)
    crop_box_changed = Signal(int, int, int, int)
    # Emitted when a vector path is created or modified
    path_modified = Signal()
    # Emitted when a selection is created, modified, or cleared via canvas interaction
    selection_committed = Signal()
    # Emitted when the pivot point position is modified via PivotTool canvas drag
    pivot_modified = Signal(int, int)
    # Emitted when a color is picked via Alt+Click canvas interaction
    color_picked = Signal(str)

    def __init__(self, doc: Optional[PixelDocument] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.doc: PixelDocument = doc if doc is not None else PixelDocument(32, 32)
        self.active_tool: Optional[Tool] = None

        # Shared selection model — also given to SelectionTool instances
        self.selection: SelectionModel = SelectionModel()

        # Tool settings
        self.primary_color: str = "#FF0000FF"
        self.secondary_color: str = "#00000000"
        self.brush_size: int = 1
        self.shape_filled: bool = False

        # View settings
        self.zoom_level: float = 16.0  # 16x default pixel scale factor
        self.show_grid: bool = True
        self.show_canvas_border: bool = True
        self.show_layer_bounds: bool = True  # Faint outline around active layer content bounds
        self.show_pivot: bool = True  # Display pivot point on canvas
        self.pan_offset: QPointF = QPointF(40.0, 40.0)
        self._initial_centered: bool = False
        self.is_panning: bool = False
        self.last_pan_pos: QPoint = QPoint()

        # Track whether the current stroke has made any pixel changes
        self._stroke_dirty: bool = False

        # Composite rendering cache
        self._cached_composite_image: Optional[QImage] = None

        # Checkerboard tile cache — keyed by square_size (float)
        self._checker_pixmap: Optional[QPixmap] = None
        self._checker_square_size: float = -1.0

        # Canvas hover / cursor state
        self.hover_coord: Optional[Tuple[int, int]] = None

        # Enable mouse tracking for hover effects & coordinate updates
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(400, 300)

    def invalidate_cache(self) -> None:
        """Invalidate the cached composite QImage buffer."""
        self._cached_composite_image = None

    def get_composite_image(self) -> QImage:
        """Returns cached composite QImage or renders fresh if dirty."""
        if (
            self._cached_composite_image is None
            or self._cached_composite_image.width() != self.doc.width
            or self._cached_composite_image.height() != self.doc.height
        ):
            self._cached_composite_image = self.doc.render_composite_qimage()
        return self._cached_composite_image

    def set_document(self, doc: PixelDocument) -> None:
        self.doc = doc
        self.invalidate_cache()
        if self.isVisible():
            self.center_canvas()
        else:
            self._initial_centered = False
        self.update()

    def center_canvas(self) -> None:
        canvas_pixel_width = self.doc.width * self.zoom_level
        canvas_pixel_height = self.doc.height * self.zoom_level
        dx = (self.width() - canvas_pixel_width) / 2.0
        dy = (self.height() - canvas_pixel_height) / 2.0
        self.pan_offset = QPointF(dx, dy)
        self.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self._auto_center_canvas)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not self._initial_centered and event.size().width() > 0 and event.size().height() > 0:
            self.center_canvas()
            if event.size().width() > 400 and event.size().height() > 300:
                self._initial_centered = True

    def _auto_center_canvas(self) -> None:
        if not self._initial_centered and self.width() > 0 and self.height() > 0:
            self.center_canvas()
            if self.width() > 400 and self.height() > 300:
                self._initial_centered = True

    def set_zoom(self, zoom: float) -> None:
        self.zoom_level = max(1.0, min(128.0, zoom))
        self.update()

    def zoom_in(self) -> None:
        self.set_zoom(self.zoom_level * 1.25)

    def zoom_out(self) -> None:
        self.set_zoom(self.zoom_level / 1.25)

    def toggle_grid(self) -> None:
        self.show_grid = not self.show_grid
        self.update()

    def toggle_canvas_border(self) -> None:
        self.show_canvas_border = not self.show_canvas_border
        self.update()

    def toggle_layer_bounds(self) -> None:
        self.show_layer_bounds = not self.show_layer_bounds
        self.update()

    def window_to_canvas_coord(self, pos: QPointF) -> Tuple[int, int]:
        """Converts widget window pixel position to document pixel (x, y) coordinate."""
        rel_x = pos.x() - self.pan_offset.x()
        rel_y = pos.y() - self.pan_offset.y()
        px = int(rel_x // self.zoom_level)
        py = int(rel_y // self.zoom_level)
        return px, py

    def draw_checkerboard(self, painter: QPainter, rect: QRectF) -> None:
        """Draws a subtle dark checkerboard using a cached QPixmap tile for GPU-accelerated tiling."""
        square_size = max(4.0, self.zoom_level / 2.0)

        # Rebuild tile only when square_size changes
        if self._checker_pixmap is None or square_size != self._checker_square_size:
            tile_px = int(round(square_size * 2))  # tile = 2x2 checker squares
            tile_img = QImage(tile_px, tile_px, QImage.Format_RGB32)
            c1 = QColor("#222222")
            c2 = QColor("#1A1A1A")
            sq = int(round(square_size))
            tile_img.fill(c1)
            # Fill the two squares that differ from c1
            tile_painter = QPainter(tile_img)
            tile_painter.fillRect(0, sq, sq, sq, c2)
            tile_painter.fillRect(sq, 0, sq, sq, c2)
            tile_painter.end()
            self._checker_pixmap = QPixmap.fromImage(tile_img)
            self._checker_square_size = square_size

        painter.drawTiledPixmap(rect, self._checker_pixmap)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        # Background fill
        painter.fillRect(self.rect(), QColor("#141414"))

        # Calculate canvas rectangle in widget screen space
        cw = self.doc.width * self.zoom_level
        ch = self.doc.height * self.zoom_level
        canvas_rect = QRectF(self.pan_offset.x(), self.pan_offset.y(), cw, ch)

        # 1. Checkerboard background for transparency indication
        self.draw_checkerboard(painter, canvas_rect)

        # 2. Composite render of all layers (cached)
        comp_img = self.get_composite_image()
        painter.drawImage(canvas_rect, comp_img)

        # 3. Tool Preview Pixels (live shape preview while dragging)
        if self.active_tool and self.hover_coord:
            hx, hy = self.hover_coord
            preview = self.active_tool.get_preview_pixels(
                self.doc, hx, hy, self.primary_color, self.brush_size, self.shape_filled, self.selection
            )
            for (px, py), color_hex in preview.items():
                if self.doc.is_valid_coord(px, py):
                    px_rect = QRectF(
                        self.pan_offset.x() + px * self.zoom_level,
                        self.pan_offset.y() + py * self.zoom_level,
                        self.zoom_level,
                        self.zoom_level,
                    )
                    painter.fillRect(px_rect, hex_to_qcolor(color_hex))

        # 4. Pixel Grid Lines (Viewport Clipped for performance)
        if self.show_grid and self.zoom_level >= 6.0:
            z = self.zoom_level
            ox = self.pan_offset.x()
            oy = self.pan_offset.y()
            w_w = float(self.width())
            w_h = float(self.height())

            min_x = max(0, int((-ox) / z))
            max_x = min(self.doc.width, int((w_w - ox) / z) + 1)
            min_y = max(0, int((-oy) / z))
            max_y = min(self.doc.height, int((w_h - oy) / z) + 1)

            pen = QPen(QColor(255, 255, 255, 30), 1)
            painter.setPen(pen)
            top_y = max(canvas_rect.top(), 0.0)
            bot_y = min(canvas_rect.bottom(), w_h)
            left_x = max(canvas_rect.left(), 0.0)
            right_x = min(canvas_rect.right(), w_w)

            for x in range(min_x, max_x + 1):
                lx = ox + x * z
                if left_x <= lx <= right_x:
                    painter.drawLine(QPointF(lx, top_y), QPointF(lx, bot_y))

            for y in range(min_y, max_y + 1):
                ly = oy + y * z
                if top_y <= ly <= bot_y:
                    painter.drawLine(QPointF(left_x, ly), QPointF(right_x, ly))

        # 5. Canvas Border
        if self.show_canvas_border:
            border_pen = QPen(QColor("#F97316"), 1.5)
            painter.setPen(border_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(canvas_rect)

        # 5.5. Active Layer Content Bounds (faint dashed outline around active layer content)
        if self.show_layer_bounds:
            self._draw_active_layer_bounds(painter)

        # 6. Selection Overlay
        if not self.selection.is_empty():
            self._draw_selection(painter)

        # 7. Crop Box Overlay
        if isinstance(self.active_tool, CropTool):
            self._draw_crop_overlay(painter)

        # 7.5. Vector Bezier Path Overlay
        self._draw_vector_paths(painter)

        # 7.6. Pivot Point Overlay (Visible ONLY when Pivot Tool is selected and active)
        if isinstance(self.active_tool, PivotTool):
            self._draw_pivot_overlay(painter)

        # 8. Hover cursor indicator (scaled to match current tool brush size)

        if self.hover_coord and self.active_tool:
            if not isinstance(self.active_tool, (CropTool, MoveTool)):
                hx, hy = self.hover_coord
                if self.doc.is_valid_coord(hx, hy):
                    effective_size = 1 if getattr(self.active_tool, "name", "") == "picker" else max(1, self.brush_size)
                    half = effective_size // 2
                    start_x = hx - half
                    start_y = hy - half
                    z = self.zoom_level
                    ox = self.pan_offset.x()
                    oy = self.pan_offset.y()

                    cursor_rect = QRectF(
                        ox + start_x * z,
                        oy + start_y * z,
                        effective_size * z,
                        effective_size * z,
                    )

                    # Soft translucent blue fill + dashed blue border for high clarity
                    painter.fillRect(cursor_rect, QColor(96, 165, 250, 35))
                    c_pen = QPen(QColor("#60A5FA"), 1.5, Qt.DashLine)
                    painter.setPen(c_pen)
                    painter.setBrush(Qt.NoBrush)
                    painter.drawRect(cursor_rect)

    def _draw_active_layer_bounds(self, painter: QPainter) -> None:
        """Renders a faint outline around the bounding box of non-transparent content in the active layer."""
        if not self.show_layer_bounds:
            return
        active_layer = self.doc.active_layer
        if not active_layer or not active_layer.visible or not active_layer.pixels:
            return

        bbox = active_layer.get_content_bbox()
        if not bbox:
            return

        bx, by, bw, bh = bbox
        z = self.zoom_level
        ox = self.pan_offset.x()
        oy = self.pan_offset.y()

        bounds_rect = QRectF(ox + bx * z, oy + by * z, bw * z, bh * z)

        # Faint dashed cyan outline (opacity 140) with soft dash pattern
        pen = QPen(QColor(56, 189, 248, 140), 1.5, Qt.DashLine)
        pen.setDashPattern([4, 4])
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(bounds_rect)

        # Draw resize handle if Move tool is active
        if isinstance(self.active_tool, MoveTool) and not active_layer.locked:
            handle_size = 7.0
            br_x = ox + (bx + bw) * z
            br_y = oy + (by + bh) * z
            handle_rect = QRectF(br_x - handle_size / 2, br_y - handle_size / 2, handle_size, handle_size)
            painter.setPen(QPen(QColor("#0284C7"), 1.5))
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawRect(handle_rect)

    def _draw_crop_overlay(self, painter: QPainter) -> None:
        """Renders Photoshop-style crop overlay: dimmed dark outside area + dashed border + handle corners."""
        if not isinstance(self.active_tool, CropTool):
            return
        crop_box = self.active_tool.crop_box
        if not crop_box:
            return

        cx, cy, cw, ch = crop_box
        z = self.zoom_level
        ox = self.pan_offset.x()
        oy = self.pan_offset.y()

        crop_screen_rect = QRectF(ox + cx * z, oy + cy * z, cw * z, ch * z)
        canvas_screen_rect = QRectF(ox, oy, self.doc.width * z, self.doc.height * z)

        # Dim regions outside crop box
        dim_color = QColor(0, 0, 0, 160)

        # Top dim
        if crop_screen_rect.top() > canvas_screen_rect.top():
            painter.fillRect(
                QRectF(canvas_screen_rect.left(), canvas_screen_rect.top(), canvas_screen_rect.width(), crop_screen_rect.top() - canvas_screen_rect.top()),
                dim_color,
            )
        # Bottom dim
        if crop_screen_rect.bottom() < canvas_screen_rect.bottom():
            painter.fillRect(
                QRectF(canvas_screen_rect.left(), crop_screen_rect.bottom(), canvas_screen_rect.width(), canvas_screen_rect.bottom() - crop_screen_rect.bottom()),
                dim_color,
            )
        # Left dim
        painter.fillRect(
            QRectF(canvas_screen_rect.left(), crop_screen_rect.top(), max(0.0, crop_screen_rect.left() - canvas_screen_rect.left()), crop_screen_rect.height()),
            dim_color,
        )
        # Right dim
        painter.fillRect(
            QRectF(crop_screen_rect.right(), crop_screen_rect.top(), max(0.0, canvas_screen_rect.right() - crop_screen_rect.right()), crop_screen_rect.height()),
            dim_color,
        )

        # Crop Box Border
        border_pen = QPen(QColor("#F97316"), 2.0, Qt.DashLine)
        painter.setPen(border_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(crop_screen_rect)

        # Corner handle markers
        handle_size = 6.0
        painter.setPen(QPen(QColor("#F97316"), 1.0))
        painter.setBrush(QColor("#FFFFFF"))

        corners = [
            crop_screen_rect.topLeft(),
            crop_screen_rect.topRight(),
            crop_screen_rect.bottomLeft(),
            crop_screen_rect.bottomRight(),
        ]
        for corner in corners:
            h_rect = QRectF(corner.x() - handle_size / 2, corner.y() - handle_size / 2, handle_size, handle_size)
            painter.drawRect(h_rect)

        # Dimension badge
        label_text = f" {cw} × {ch} px "
        painter.setFont(QFont("Sans", 9, QFont.Bold))
        fm = painter.fontMetrics()
        lbl_w = fm.horizontalAdvance(label_text) + 8
        lbl_h = fm.height() + 4
        lbl_x = max(canvas_screen_rect.left(), crop_screen_rect.left())
        lbl_y = max(canvas_screen_rect.top(), crop_screen_rect.top() - lbl_h - 4)

        lbl_rect = QRectF(lbl_x, lbl_y, lbl_w, lbl_h)
        painter.fillRect(lbl_rect, QColor("#1E293B"))
        painter.setPen(QPen(QColor("#F97316"), 1.0))
        painter.drawRect(lbl_rect)

        painter.setPen(QColor("#F8FAFC"))
        painter.drawText(lbl_rect, Qt.AlignCenter, label_text)

    def _draw_selection(self, painter: QPainter) -> None:
        """Renders the selection overlay: semi-transparent fill + dashed border on edges (viewport clipped)."""
        selected = self.selection.selected
        if not selected:
            return

        fill_color = QColor(91, 155, 255, 55)   # semi-transparent blue fill
        border_color = QColor(255, 255, 255, 200)
        border_pen = QPen(border_color, 1.0, Qt.DashLine)
        border_pen.setDashPattern([3, 3])

        z = self.zoom_level
        ox = self.pan_offset.x()
        oy = self.pan_offset.y()

        # Viewport bounds in tile coordinates
        min_x = max(0, int((-ox) / z))
        max_x = min(self.doc.width - 1, int((self.width() - ox) / z))
        min_y = max(0, int((-oy) / z))
        max_y = min(self.doc.height - 1, int((self.height() - oy) / z))

        for (px, py) in selected:
            if not (min_x <= px <= max_x and min_y <= py <= max_y):
                continue
            rect = QRectF(ox + px * z, oy + py * z, z, z)
            painter.fillRect(rect, fill_color)

            # Draw dashed edges only on borders adjacent to non-selected pixels
            painter.setPen(border_pen)
            # Top edge
            if (px, py - 1) not in selected:
                painter.drawLine(QPointF(ox + px * z, oy + py * z), QPointF(ox + (px + 1) * z, oy + py * z))
            # Bottom edge
            if (px, py + 1) not in selected:
                painter.drawLine(QPointF(ox + px * z, oy + (py + 1) * z), QPointF(ox + (px + 1) * z, oy + (py + 1) * z))
            # Left edge
            if (px - 1, py) not in selected:
                painter.drawLine(QPointF(ox + px * z, oy + py * z), QPointF(ox + px * z, oy + (py + 1) * z))
            # Right edge
            if (px + 1, py) not in selected:
                painter.drawLine(QPointF(ox + (px + 1) * z, oy + py * z), QPointF(ox + (px + 1) * z, oy + (py + 1) * z))

    def _draw_vector_paths(self, painter: QPainter) -> None:
        """Renders vector path Bezier curves, dynamic stroke/fill, and active selection wireframe overlays."""
        if not self.doc.paths:
            return

        is_pen_active = isinstance(self.active_tool, PenTool)
        parent_window = self.window()
        path_panel = getattr(parent_window, "path_panel", None)
        is_panel_visible = path_panel.isVisible() if path_panel is not None else False

        # When the paths panel is minimized and Pen Tool is not active, do NOT render paths on canvas
        if not is_panel_visible and not is_pen_active:
            return

        z = self.zoom_level
        ox = self.pan_offset.x()
        oy = self.pan_offset.y()

        active_layer_name = self.doc.active_layer.name if self.doc.active_layer else ""
        active_frame_idx = getattr(self.doc, "active_frame_index", 0)
        active_path_idx = self.doc.active_path_index

        for idx, path in enumerate(self.doc.paths):
            if not path.visible or not path.anchors:
                continue

            # Only show paths on the current layer and current frame
            if path.layer_id and path.layer_id != active_layer_name:
                continue
            if path.frame_index is not None and path.frame_index != active_frame_idx:
                continue

            is_active_path = (idx == active_path_idx)

            # Build screen-transformed QPainterPath
            qpath = path.to_qpainterpath()
            transform = QTransform()
            transform.translate(ox, oy)
            transform.scale(z, z)
            screen_path = transform.map(qpath)

            # Selected Path Wireframe & Control Handles (Visualized ONLY for active path when Pen Tool or Paths Panel is open)
            if is_active_path and (is_pen_active or is_panel_visible):
                wire_pen = QPen(QColor("#F97316"), 2.0)  # Prominent bright orange wireframe for selected path
                painter.setPen(wire_pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(screen_path)

                selected_idx = getattr(self.active_tool, "selected_anchor_idx", None) if is_pen_active else None


                for a_idx, anchor in enumerate(path.anchors):
                    ax_screen = ox + anchor.x * z
                    ay_screen = oy + anchor.y * z

                    is_selected_anchor = (is_pen_active and selected_idx == a_idx)

                    # Draw handles for selected anchor point
                    if is_selected_anchor or is_pen_active:
                        hin = anchor.handle_in_abs
                        hout = anchor.handle_out_abs
                        h_in_screen = QPointF(ox + hin.x() * z, oy + hin.y() * z)
                        h_out_screen = QPointF(ox + hout.x() * z, oy + hout.y() * z)

                        # Handle lines
                        painter.setPen(QPen(QColor(255, 255, 255, 200), 1.0))
                        painter.drawLine(QPointF(ax_screen, ay_screen), h_in_screen)
                        painter.drawLine(QPointF(ax_screen, ay_screen), h_out_screen)

                        # Handle circles
                        painter.setPen(QPen(QColor("#000000"), 1.0))
                        painter.setBrush(QColor("#00E436") if is_selected_anchor else QColor("#FFFFFF"))
                        painter.drawEllipse(h_in_screen, 3.5, 3.5)
                        painter.drawEllipse(h_out_screen, 3.5, 3.5)

                    # Draw Anchor Box
                    box_size = 7.0 if is_selected_anchor else 5.0
                    box_rect = QRectF(ax_screen - box_size / 2, ay_screen - box_size / 2, box_size, box_size)
                    painter.setPen(QPen(QColor("#000000"), 1.2))
                    painter.setBrush(QColor("#F97316") if is_selected_anchor else QColor("#FFFFFF"))
                    painter.drawRect(box_rect)

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------



    def _draw_pivot_overlay(self, painter: QPainter) -> None:
        """Renders an antialiased pivot point crosshair indicator on the active animation."""
        if not self.doc or not self.doc.active_animation:
            return
        anim = self.doc.active_animation
        px = anim.pivot_x
        py = anim.pivot_y

        z = self.zoom_level
        cx = self.pan_offset.x() + (px + 0.5) * z
        cy = self.pan_offset.y() + (py + 0.5) * z

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        radius = max(8.0, min(24.0, z * 0.8))

        # Outer shadow circle
        painter.setPen(QPen(QColor(0, 0, 0, 180), 3))
        painter.setBrush(QColor(249, 115, 22, 50))  # Translucent orange fill
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # Main bright orange ring
        painter.setPen(QPen(QColor("#F97316"), 2))
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # Center cyan dot
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#38BDF8"))
        painter.drawEllipse(QPointF(cx, cy), 3.5, 3.5)

        # Crosshair lines
        painter.setPen(QPen(QColor("#F97316"), 2))
        painter.drawLine(QPointF(cx - radius - 5, cy), QPointF(cx + radius + 5, cy))
        painter.drawLine(QPointF(cx, cy - radius - 5), QPointF(cx, cy + radius + 5))

        painter.restore()

    def _is_selection_tool(self) -> bool:
        return isinstance(self.active_tool, SelectionTool)

    def _sample_color_at(self, px: int, py: int) -> Optional[str]:
        if not self.doc or not self.doc.is_valid_coord(px, py):
            return None
        comp_img = self.get_composite_image()
        if 0 <= px < comp_img.width() and 0 <= py < comp_img.height():
            qcol = comp_img.pixelColor(px, py)
            if qcol.alpha() > 0:
                return qcolor_to_hex(qcol)
        layer = self.doc.active_layer
        if layer:
            return layer.get_pixel(px, py)
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        # Middle mouse = pan
        if event.button() == Qt.MiddleButton:
            self.is_panning = True
            self.last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            return

        # Alt + LeftButton = pick color underneath mouse into primary color
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.AltModifier):
            px, py = self.window_to_canvas_coord(event.position())
            color_hex = self._sample_color_at(px, py)
            if color_hex:
                self.color_picked.emit(color_hex)
            return

        if event.button() == Qt.LeftButton:
            px, py = self.window_to_canvas_coord(event.position())
            if not self.active_tool:
                return

            self._stroke_dirty = False

            # Shift-constrain for crop tool & move tool
            if isinstance(self.active_tool, (CropTool, MoveTool)):
                self.active_tool.constrain_square = bool(event.modifiers() & Qt.ShiftModifier)

            # Set operation modifier for selection tool
            if self._is_selection_tool():
                sel_tool: SelectionTool = self.active_tool  # type: ignore
                if event.modifiers() & Qt.ShiftModifier:
                    sel_tool._op = "add"
                elif event.modifiers() & Qt.AltModifier:
                    sel_tool._op = "remove"
                else:
                    sel_tool._op = "replace"

            # Notify Pen Tool whether Paths Panel is open
            parent_window = self.window()
            path_panel = getattr(parent_window, "path_panel", None)
            is_path_panel_open = path_panel.isVisible() if path_panel is not None else False

            if isinstance(self.active_tool, MoveTool):
                changed = self.active_tool.mouse_press(
                    self.doc,
                    px,
                    py,
                    self.primary_color,
                    self.secondary_color,
                    self.brush_size,
                    self.shape_filled,
                    self.selection,
                    screen_pos=event.position(),
                    pan_offset=self.pan_offset,
                    zoom=self.zoom_level,
                    path_panel_open=is_path_panel_open,
                )
            else:
                changed = self.active_tool.mouse_press(
                    self.doc,
                    px,
                    py,
                    self.primary_color,
                    self.secondary_color,
                    self.brush_size,
                    self.shape_filled,
                    self.selection,
                    shift_pressed=bool(event.modifiers() & Qt.ShiftModifier),
                )

            if changed or isinstance(self.active_tool, PivotTool):
                self._stroke_dirty = True
                self.canvas_updated.emit()
                if isinstance(self.active_tool, (PenTool, MoveTool)):
                    self.path_modified.emit()
                elif isinstance(self.active_tool, PivotTool):
                    if self.doc and self.doc.active_animation:
                        anim = self.doc.active_animation
                        self.pivot_modified.emit(anim.pivot_x, anim.pivot_y)
            elif self._is_selection_tool():
                self.update()

            if isinstance(self.active_tool, CropTool) and self.active_tool.crop_box:
                cx, cy, cw, ch = self.active_tool.crop_box
                self.crop_box_changed.emit(cx, cy, cw, ch)
            self.update()

        elif event.button() == Qt.RightButton and self._is_selection_tool():
            # Right-click with selection tool always removes
            px, py = self.window_to_canvas_coord(event.position())
            sel_tool: SelectionTool = self.active_tool  # type: ignore
            old_op = sel_tool._op
            sel_tool._op = "remove"
            sel_tool.mouse_press(self.doc, px, py, self.primary_color, self.secondary_color, self.brush_size, self.shape_filled, self.selection)
            sel_tool._op = old_op
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        px, py = self.window_to_canvas_coord(event.position())
        self.hover_coord = (px, py)
        self.cursor_moved.emit(px, py)

        if self.is_panning:
            delta = event.pos() - self.last_pan_pos
            self.pan_offset += QPointF(delta.x(), delta.y())
            self.last_pan_pos = event.pos()
            self.update()
            return

        if (event.buttons() & Qt.LeftButton) and (event.modifiers() & Qt.AltModifier):
            color_hex = self._sample_color_at(px, py)
            if color_hex:
                self.color_picked.emit(color_hex)
            return

        # Cursor shape update when hovering over move tool handle
        if isinstance(self.active_tool, MoveTool) and not (event.buttons() & Qt.LeftButton):
            if self.active_tool.is_over_resize_handle(self.doc, event.position(), self.pan_offset, self.zoom_level):
                self.setCursor(Qt.SizeFDiagCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

        if self.active_tool and (event.buttons() & Qt.LeftButton):
            # Update shift-constrain live during drag
            if isinstance(self.active_tool, (CropTool, MoveTool)):
                self.active_tool.constrain_square = bool(event.modifiers() & Qt.ShiftModifier)

            parent_window = self.window()
            path_panel = getattr(parent_window, "path_panel", None)
            is_path_panel_open = path_panel.isVisible() if path_panel is not None else False

            if isinstance(self.active_tool, MoveTool):
                changed = self.active_tool.mouse_move(
                    self.doc,
                    px,
                    py,
                    self.primary_color,
                    self.secondary_color,
                    self.brush_size,
                    self.shape_filled,
                    self.selection,
                    path_panel_open=is_path_panel_open,
                )
            else:
                changed = self.active_tool.mouse_move(
                    self.doc, px, py, self.primary_color, self.secondary_color, self.brush_size, self.shape_filled, self.selection
                )

            if changed:
                self._stroke_dirty = True
                self.invalidate_cache()
                self.canvas_updated.emit()
                if isinstance(self.active_tool, (PenTool, MoveTool)):
                    self.path_modified.emit()
                elif isinstance(self.active_tool, PivotTool):
                    if self.doc and self.doc.active_animation:
                        anim = self.doc.active_animation
                        self.pivot_modified.emit(anim.pivot_x, anim.pivot_y)

            elif self._is_selection_tool():
                self.update()  # Repaint for rubber-band preview

            if isinstance(self.active_tool, CropTool) and self.active_tool.crop_box:
                cx, cy, cw, ch = self.active_tool.crop_box
                self.crop_box_changed.emit(cx, cy, cw, ch)

        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() in (Qt.MiddleButton, Qt.LeftButton) and self.is_panning:
            self.is_panning = False
            self.setCursor(Qt.ArrowCursor)
            return

        if event.button() == Qt.LeftButton and self.active_tool:
            px, py = self.window_to_canvas_coord(event.position())

            # Final shift-constrain state on release
            if isinstance(self.active_tool, (CropTool, MoveTool)):
                self.active_tool.constrain_square = bool(event.modifiers() & Qt.ShiftModifier)

            changed = self.active_tool.mouse_release(
                self.doc, px, py, self.primary_color, self.secondary_color, self.brush_size, self.shape_filled, self.selection
            )
            if changed:
                self._stroke_dirty = True

            if isinstance(self.active_tool, PenTool):
                self.path_modified.emit()


            # Commit full stroke to history only on mouse_release
            if self._stroke_dirty:
                self._stroke_dirty = False
                self.invalidate_cache()
                self.stroke_committed.emit()

            if isinstance(self.active_tool, CropTool) and self.active_tool.crop_box:
                cx, cy, cw, ch = self.active_tool.crop_box
                self.crop_box_changed.emit(cx, cy, cw, ch)

            if self._is_selection_tool():
                self.selection_committed.emit()
                self.update()

            self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        # Zoom centered on mouse pointer position
        cursor_pos = event.position()
        old_px, old_py = self.window_to_canvas_coord(cursor_pos)

        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_level = min(128.0, self.zoom_level * 1.2)
        else:
            self.zoom_level = max(1.0, self.zoom_level / 1.2)

        # Adjust pan to keep canvas position under cursor stable
        new_rel_x = old_px * self.zoom_level
        new_rel_y = old_py * self.zoom_level
        self.pan_offset = QPointF(cursor_pos.x() - new_rel_x, cursor_pos.y() - new_rel_y)

        self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and isinstance(self.active_tool, CropTool):
            crop_tool: CropTool = self.active_tool
            if crop_tool.crop_box:
                cx, cy, cw, ch = crop_tool.crop_box
                px, py = self.window_to_canvas_coord(event.position())
                if cx <= px < cx + cw and cy <= py < cy + ch:
                    self.crop_committed.emit(cx, cy, cw, ch)
                    return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event) -> None:
        if isinstance(self.active_tool, CropTool):
            crop_tool: CropTool = self.active_tool
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if crop_tool.crop_box:
                    cx, cy, cw, ch = crop_tool.crop_box
                    self.crop_committed.emit(cx, cy, cw, ch)
                    return
            elif event.key() == Qt.Key_Escape:
                crop_tool.clear_box()
                self.update()
                return

        if isinstance(self.active_tool, MoveTool):
            move_tool: MoveTool = self.active_tool
            dx, dy = 0, 0
            if event.key() == Qt.Key_Left:
                dx = -1
            elif event.key() == Qt.Key_Right:
                dx = 1
            elif event.key() == Qt.Key_Up:
                dy = -1
            elif event.key() == Qt.Key_Down:
                dy = 1

            if dx != 0 or dy != 0:
                changed = move_tool.nudge(self.doc, dx, dy, selection=self.selection)
                if changed:
                    self.stroke_committed.emit()
                    self.update()
                return

        if event.key() == Qt.Key_BracketLeft:
            main_win = self.window()
            if hasattr(main_win, "_decrease_brush_size"):
                main_win._decrease_brush_size()
            elif self.brush_size > 1:
                self.brush_size -= 1
                self.update()
            return
        elif event.key() == Qt.Key_BracketRight:
            main_win = self.window()
            if hasattr(main_win, "_increase_brush_size"):
                main_win._increase_brush_size()
            elif self.brush_size < 32:
                self.brush_size += 1
                self.update()
            return

        if event.key() == Qt.Key_A:
            self.center_canvas()
            return

        if event.key() == Qt.Key_Escape and not self.selection.is_empty():
            self.selection.clear()
            self.selection_committed.emit()
            self.update()
            return

        super().keyPressEvent(event)
