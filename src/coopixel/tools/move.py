"""
Move tool for Coopixel pixel art editor.
Shifts the active layer pixels (and active selection) interactively across the canvas.
"""

from typing import Dict, Optional, Set, Tuple
from PySide6.QtCore import QPointF
from coopixel.models.document import PixelDocument
from coopixel.models.selection import SelectionModel
from coopixel.tools.base import Tool


class MoveTool(Tool):
    """Tool for moving or resizing active layer pixels by dragging or nudging."""

    name: str = "move"
    display_name: str = "Move Tool"

    def __init__(self):
        super().__init__()
        self.drag_start: Optional[Tuple[int, int]] = None
        self.initial_pixels: Dict[str, str] = {}
        self.initial_selection: Optional[Set[Tuple[int, int]]] = None
        self.is_resizing: bool = False
        self.initial_bbox: Optional[Tuple[int, int, int, int]] = None
        self.constrain_square: bool = False

    def is_over_resize_handle(
        self,
        doc: PixelDocument,
        screen_pos: QPointF,
        pan_offset: QPointF,
        zoom: float,
        tolerance: float = 8.0,
    ) -> bool:
        """Determines if the given screen position is hovering over the active layer's bottom-right resize handle."""
        active = doc.active_layer
        if not active or active.locked or not active.visible or not active.pixels:
            return False
        bbox = active.get_content_bbox()
        if not bbox:
            return False
        bx, by, bw, bh = bbox
        br_x = pan_offset.x() + (bx + bw) * zoom
        br_y = pan_offset.y() + (by + bh) * zoom
        return (abs(screen_pos.x() - br_x) <= tolerance) and (abs(screen_pos.y() - br_y) <= tolerance)

    def mouse_press(
        self,
        doc: PixelDocument,
        x: int,
        y: int,
        primary_color: str,
        secondary_color: str,
        size: int = 1,
        filled: bool = False,
        selection: Optional[SelectionModel] = None,
        screen_pos: Optional[QPointF] = None,
        pan_offset: Optional[QPointF] = None,
        zoom: float = 1.0,
    ) -> bool:
        self.is_drawing = True
        self.drag_start = (x, y)
        active = doc.active_layer

        if active and not active.locked and active.visible and active.pixels:
            bbox = active.get_content_bbox()
            if bbox:
                if screen_pos is not None and pan_offset is not None:
                    hit_handle = self.is_over_resize_handle(doc, screen_pos, pan_offset, zoom)
                else:
                    bx, by, bw, bh = bbox
                    hit_handle = (abs(x - (bx + bw)) <= 1) and (abs(y - (by + bh)) <= 1)

                if hit_handle:
                    self.is_resizing = True
                    self.initial_bbox = bbox
                else:
                    self.is_resizing = False
                    self.initial_bbox = None
            else:
                self.is_resizing = False
                self.initial_bbox = None
        else:
            self.is_resizing = False
            self.initial_bbox = None

        if active and not active.locked and active.visible:
            self.initial_pixels = dict(active.pixels)
            if selection and not selection.is_empty():
                self.initial_selection = set(selection.selected)
            else:
                self.initial_selection = None
        else:
            self.initial_pixels = {}
            self.initial_selection = None
        return False

    def mouse_move(
        self,
        doc: PixelDocument,
        x: int,
        y: int,
        primary_color: str,
        secondary_color: str,
        size: int = 1,
        filled: bool = False,
        selection: Optional[SelectionModel] = None,
    ) -> bool:
        if not self.is_drawing or not self.drag_start:
            return False

        active = doc.active_layer
        if not active or active.locked or not active.visible:
            return False

        if self.is_resizing and self.initial_bbox:
            bx, by, bw, bh = self.initial_bbox
            new_w = max(1, x - bx)
            new_h = max(1, y - by)
            if self.constrain_square:
                side = max(1, max(new_w, new_h))
                new_w = side
                new_h = side

            # Nearest-neighbor pixel scaling
            new_pixels: Dict[str, str] = {}
            for dx in range(new_w):
                for dy in range(new_h):
                    src_dx = int(dx * bw / new_w)
                    src_dy = int(dy * bh / new_h)
                    src_x = bx + src_dx
                    src_y = by + src_dy
                    color = self.initial_pixels.get(f"{src_x},{src_y}")
                    if color:
                        new_pixels[f"{bx + dx},{by + dy}"] = color
            active.pixels = new_pixels

            # Resample selection mask if active
            if selection and self.initial_selection is not None:
                new_sel = set()
                for sx, sy in self.initial_selection:
                    if bx <= sx < bx + bw and by <= sy < by + bh:
                        rel_x = sx - bx
                        rel_y = sy - by
                        nx_start = int(rel_x * new_w / bw)
                        nx_end = max(nx_start + 1, int((rel_x + 1) * new_w / bw))
                        ny_start = int(rel_y * new_h / bh)
                        ny_end = max(ny_start + 1, int((rel_y + 1) * new_h / bh))
                        for nx in range(nx_start, nx_end):
                            for ny in range(ny_start, ny_end):
                                target_x = bx + nx
                                target_y = by + ny
                                if doc.is_valid_coord(target_x, target_y):
                                    new_sel.add((target_x, target_y))
                    else:
                        dx_shift = x - self.drag_start[0]
                        dy_shift = y - self.drag_start[1]
                        if doc.is_valid_coord(sx + dx_shift, sy + dy_shift):
                            new_sel.add((sx + dx_shift, sy + dy_shift))
                selection.selected = new_sel

            return True

        dx = x - self.drag_start[0]
        dy = y - self.drag_start[1]

        # Shift layer pixels relative to initial state
        new_pixels: Dict[str, str] = {}
        for coord_str, color_hex in self.initial_pixels.items():
            parts = coord_str.split(",")
            if len(parts) == 2:
                px, py = int(parts[0]), int(parts[1])
                nx, ny = px + dx, py + dy
                new_pixels[f"{nx},{ny}"] = color_hex
        active.pixels = new_pixels

        # If active selection exists, also shift selection mask
        if selection and self.initial_selection is not None:
            new_sel = set()
            for sx, sy in self.initial_selection:
                nx, ny = sx + dx, sy + dy
                if doc.is_valid_coord(nx, ny):
                    new_sel.add((nx, ny))
            selection.selected = new_sel

        return True

    def mouse_release(
        self,
        doc: PixelDocument,
        x: int,
        y: int,
        primary_color: str,
        secondary_color: str,
        size: int = 1,
        filled: bool = False,
        selection: Optional[SelectionModel] = None,
    ) -> bool:
        was_drawing = self.is_drawing
        self.is_drawing = False
        self.is_resizing = False
        self.initial_bbox = None
        self.drag_start = None
        self.initial_pixels = {}
        self.initial_selection = None
        return was_drawing

    def nudge(self, doc: PixelDocument, dx: int, dy: int, selection: Optional[SelectionModel] = None) -> bool:
        """Nudges active layer pixels (and active selection mask) by dx, dy."""
        active = doc.active_layer
        if not active or active.locked or not active.visible:
            return False

        new_pixels: Dict[str, str] = {}
        for coord_str, color_hex in active.pixels.items():
            parts = coord_str.split(",")
            if len(parts) == 2:
                px, py = int(parts[0]), int(parts[1])
                nx, ny = px + dx, py + dy
                new_pixels[f"{nx},{ny}"] = color_hex
        active.pixels = new_pixels

        if selection and not selection.is_empty():
            new_sel = set()
            for sx, sy in selection.selected:
                nx, ny = sx + dx, sy + dy
                if doc.is_valid_coord(nx, ny):
                    new_sel.add((nx, ny))
            selection.selected = new_sel

        return True

