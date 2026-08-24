"""
Interactive Pixel Canvas Widget for Coopixel.
Handles zooming, panning, grid rendering, checkerboard background, tool interaction, and live preview.
"""

from typing import Dict, Optional, Set, Tuple
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QMouseEvent,
    QPainter,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import QWidget
from coopixel.models.document import PixelDocument, hex_to_qcolor
from coopixel.models.selection import SelectionModel
from coopixel.tools.base import Tool
from coopixel.tools.crop import CropTool
from coopixel.tools.move import MoveTool
from coopixel.tools.selection import SelectionTool


class CanvasWidget(QWidget):
    cursor_moved = Signal(int, int)
    # Emitted when a complete drawing stroke finishes (mouse_release) — triggers history push
    stroke_committed = Signal()
    # Emitted on live pixel changes during a stroke (mouse_move) — triggers repaint only, NO history
    canvas_updated = Signal()
    # Emitted when a crop box is committed via canvas interaction (Enter / double-click)
    crop_committed = Signal(int, int, int, int)
    # Emitted when a selection is created, modified, or cleared via canvas interaction
    selection_committed = Signal()

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
        self.pan_offset: QPointF = QPointF(40.0, 40.0)
        self.is_panning: bool = False
        self.last_pan_pos: QPoint = QPoint()

        # Track whether the current stroke has made any pixel changes
        self._stroke_dirty: bool = False

        # Canvas hover / cursor state
        self.hover_coord: Optional[Tuple[int, int]] = None

        # Enable mouse tracking for hover effects & coordinate updates
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(400, 300)

    def set_document(self, doc: PixelDocument) -> None:
        self.doc = doc
        self.center_canvas()
        self.update()

    def center_canvas(self) -> None:
        canvas_pixel_width = self.doc.width * self.zoom_level
        canvas_pixel_height = self.doc.height * self.zoom_level
        dx = max(20.0, (self.width() - canvas_pixel_width) / 2.0)
        dy = max(20.0, (self.height() - canvas_pixel_height) / 2.0)
        self.pan_offset = QPointF(dx, dy)

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

    def window_to_canvas_coord(self, pos: QPointF) -> Tuple[int, int]:
        """Converts widget window pixel position to document pixel (x, y) coordinate."""
        rel_x = pos.x() - self.pan_offset.x()
        rel_y = pos.y() - self.pan_offset.y()
        px = int(rel_x // self.zoom_level)
        py = int(rel_y // self.zoom_level)
        return px, py

    def draw_checkerboard(self, painter: QPainter, rect: QRectF) -> None:
        """Draws a subtle dark checkerboard pattern to indicate transparency."""
        square_size = max(4.0, self.zoom_level / 2.0)
        start_x = rect.x()
        start_y = rect.y()
        end_x = rect.x() + rect.width()
        end_y = rect.y() + rect.height()

        c1 = QColor("#222222")
        c2 = QColor("#1A1A1A")

        y = start_y
        row = 0
        while y < end_y:
            x = start_x
            col = 0
            while x < end_x:
                color = c1 if (row + col) % 2 == 0 else c2
                painter.fillRect(QRectF(x, y, square_size, square_size), color)
                x += square_size
                col += 1
            y += square_size
            row += 1

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

        # 2. Composite render of all layers
        comp_img = self.doc.render_composite_qimage()
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

        # 4. Pixel Grid Lines
        if self.show_grid and self.zoom_level >= 6.0:
            pen = QPen(QColor(255, 255, 255, 30), 1)
            painter.setPen(pen)
            for x in range(self.doc.width + 1):
                lx = self.pan_offset.x() + x * self.zoom_level
                painter.drawLine(QPointF(lx, canvas_rect.top()), QPointF(lx, canvas_rect.bottom()))
            for y in range(self.doc.height + 1):
                ly = self.pan_offset.y() + y * self.zoom_level
                painter.drawLine(QPointF(canvas_rect.left(), ly), QPointF(canvas_rect.right(), ly))

        # 5. Canvas Border
        border_pen = QPen(QColor("#F97316"), 1.5)
        painter.setPen(border_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(canvas_rect)

        # 6. Selection Overlay
        if not self.selection.is_empty():
            self._draw_selection(painter)

        # 7. Crop Box Overlay
        if isinstance(self.active_tool, CropTool):
            self._draw_crop_overlay(painter)

        # 8. Hover cursor indicator
        if self.hover_coord:
            hx, hy = self.hover_coord
            if self.doc.is_valid_coord(hx, hy):
                cursor_rect = QRectF(
                    self.pan_offset.x() + hx * self.zoom_level,
                    self.pan_offset.y() + hy * self.zoom_level,
                    self.zoom_level,
                    self.zoom_level,
                )
                c_pen = QPen(QColor("#60A5FA"), 1.5, Qt.DashLine)
                painter.setPen(c_pen)
                painter.drawRect(cursor_rect)

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
        """Renders the selection overlay: semi-transparent fill + dashed border on edges."""
        selected = self.selection.selected
        fill_color = QColor(91, 155, 255, 55)   # semi-transparent blue fill
        border_color = QColor(255, 255, 255, 200)
        border_pen = QPen(border_color, 1.0, Qt.DashLine)
        border_pen.setDashPattern([3, 3])

        z = self.zoom_level
        ox = self.pan_offset.x()
        oy = self.pan_offset.y()

        for (px, py) in selected:
            if not self.doc.is_valid_coord(px, py):
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

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def _is_selection_tool(self) -> bool:
        return isinstance(self.active_tool, SelectionTool)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        # Middle mouse or Alt+Left = pan
        if event.button() == Qt.MiddleButton or (
            event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier
            and not self._is_selection_tool()
        ):
            self.is_panning = True
            self.last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            return

        if event.button() == Qt.LeftButton and self.active_tool:
            px, py = self.window_to_canvas_coord(event.position())

            # Set operation modifier for selection tool
            if self._is_selection_tool():
                sel_tool: SelectionTool = self.active_tool  # type: ignore
                if event.modifiers() & Qt.ShiftModifier:
                    sel_tool._op = "add"
                elif event.modifiers() & Qt.AltModifier:
                    sel_tool._op = "remove"
                else:
                    sel_tool._op = "replace"

            changed = self.active_tool.mouse_press(
                self.doc, px, py, self.primary_color, self.secondary_color, self.brush_size, self.shape_filled, self.selection
            )
            if changed:
                self._stroke_dirty = True
                self.canvas_updated.emit()
            elif self._is_selection_tool():
                # Selection changes don't dirty the document but need a repaint
                self.update()
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

        if self.active_tool and (event.buttons() & Qt.LeftButton):
            changed = self.active_tool.mouse_move(
                self.doc, px, py, self.primary_color, self.secondary_color, self.brush_size, self.shape_filled, self.selection
            )
            if changed:
                self._stroke_dirty = True
                self.canvas_updated.emit()
            elif self._is_selection_tool():
                self.update()  # Repaint for rubber-band preview

        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() in (Qt.MiddleButton, Qt.LeftButton) and self.is_panning:
            self.is_panning = False
            self.setCursor(Qt.ArrowCursor)
            return

        if event.button() == Qt.LeftButton and self.active_tool:
            px, py = self.window_to_canvas_coord(event.position())
            changed = self.active_tool.mouse_release(
                self.doc, px, py, self.primary_color, self.secondary_color, self.brush_size, self.shape_filled, self.selection
            )
            if changed:
                self._stroke_dirty = True

            # Commit full stroke to history only on mouse_release
            if self._stroke_dirty:
                self._stroke_dirty = False
                self.stroke_committed.emit()

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

        if event.key() == Qt.Key_Escape and not self.selection.is_empty():
            self.selection.clear()
            self.selection_committed.emit()
            self.update()
            return

        super().keyPressEvent(event)
