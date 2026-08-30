"""
Move tool for Coopixel pixel art editor.
Shifts active/selected layers' pixels (and active selection) interactively across the canvas.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from PySide6.QtCore import QPointF
from coopixel.models.document import Layer, PixelDocument
from coopixel.models.selection import SelectionModel
from coopixel.tools.base import Tool


class MoveTool(Tool):
    """Tool for moving or resizing active and selected layers' pixels (or active vector path when Paths Panel is open) by dragging or nudging."""

    name: str = "move"
    display_name: str = "Move Tool"

    def __init__(self):
        super().__init__()
        self.drag_start: Optional[Tuple[int, int]] = None
        self.initial_layers_pixels: List[Tuple[Layer, Dict[str, str]]] = []
        self.initial_selection: Optional[Set[Tuple[int, int]]] = None
        self.is_resizing: bool = False
        self.initial_bbox: Optional[Tuple[int, int, int, int]] = None
        self.constrain_square: bool = False
        self.moving_path: bool = False
        self.initial_anchors: List[Tuple[float, float]] = []

    def is_over_resize_handle(
        self,
        doc: PixelDocument,
        screen_pos: QPointF,
        pan_offset: QPointF,
        zoom: float,
        tolerance: float = 8.0,
    ) -> bool:
        """Determines if the given screen position is hovering over the selected layers' bottom-right resize handle."""
        target_layers = [l for l in doc.selected_layers if l and not l.locked and l.visible and l.pixels]
        if not target_layers:
            return False
        bbox = doc.get_combined_selected_layers_bbox()
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
        path_panel_open: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        self.is_drawing = True
        self.drag_start = (x, y)

        if doc.active_path and path_panel_open and len(doc.active_path.anchors) > 0:
            self.moving_path = True
            self.initial_anchors = [(a.x, a.y) for a in doc.active_path.anchors]
            self.is_resizing = False
            self.initial_bbox = None
            self.initial_layers_pixels = []
            self.initial_selection = None
            return True

        self.moving_path = False
        self.initial_anchors = []
        target_layers = [l for l in doc.selected_layers if l and not l.locked and l.visible]

        if target_layers:
            bbox = doc.get_combined_selected_layers_bbox()
            if bbox:
                if screen_pos is not None and pan_offset is not None:
                    hit_handle = self.is_over_resize_handle(doc, screen_pos, pan_offset, zoom)
                else:
                    bx, by, bw, bh = bbox
                    hit_handle = (x == bx + bw) and (y == by + bh)

                if hit_handle:
                    self.is_resizing = True
                    self.initial_bbox = bbox
                else:
                    self.is_resizing = False
                    self.initial_bbox = None
            else:
                self.is_resizing = False
                self.initial_bbox = None

            self.initial_layers_pixels = [(l, dict(l.pixels)) for l in target_layers]
            if selection and not selection.is_empty():
                self.initial_selection = set(selection.selected)
            else:
                self.initial_selection = None
        else:
            self.is_resizing = False
            self.initial_bbox = None
            self.initial_layers_pixels = []
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
        path_panel_open: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        if not self.is_drawing or not self.drag_start:
            return False
        sx, sy = self.drag_start
        dx, dy = x - sx, y - sy

        if self.moving_path and doc.active_path:
            for idx, (ax, ay) in enumerate(self.initial_anchors):
                if idx < len(doc.active_path.anchors):
                    doc.active_path.anchors[idx].x = ax + dx
                    doc.active_path.anchors[idx].y = ay + dy
            return True

        if not self.initial_layers_pixels:
            return False

        if self.is_resizing and self.initial_bbox:
            bx, by, bw, bh = self.initial_bbox
            new_w = max(1, bw + dx)
            new_h = max(1, bh + dy)

            if self.constrain_square:
                side = max(new_w, new_h)
                new_w = side
                new_h = side

            for layer, orig_px in self.initial_layers_pixels:
                new_pixels: Dict[str, str] = {}
                for coord_str, color_hex in orig_px.items():
                    parts = coord_str.split(",")
                    if len(parts) == 2:
                        px, py = int(parts[0]), int(parts[1])
                        if bx <= px < bx + bw and by <= py < by + bh:
                            rel_x = px - bx
                            rel_y = py - by
                            nx_start = int(rel_x * new_w / bw)
                            nx_end = max(nx_start + 1, int((rel_x + 1) * new_w / bw))
                            ny_start = int(rel_y * new_h / bh)
                            ny_end = max(ny_start + 1, int((rel_y + 1) * new_h / bh))
                            for nx in range(nx_start, nx_end):
                                for ny in range(ny_start, ny_end):
                                    target_x = bx + nx
                                    target_y = by + ny
                                    new_pixels[f"{target_x},{target_y}"] = color_hex
                        else:
                            dx_shift = x - self.drag_start[0]
                            dy_shift = y - self.drag_start[1]
                            new_pixels[f"{px + dx_shift},{py + dy_shift}"] = color_hex
                layer.pixels = new_pixels

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

        dx_val = x - self.drag_start[0]
        dy_val = y - self.drag_start[1]

        # Shift all target layers' pixels relative to their initial state
        for layer, orig_px in self.initial_layers_pixels:
            new_pixels: Dict[str, str] = {}
            for coord_str, color_hex in orig_px.items():
                parts = coord_str.split(",")
                if len(parts) == 2:
                    px, py = int(parts[0]), int(parts[1])
                    nx, ny = px + dx_val, py + dy_val
                    new_pixels[f"{nx},{ny}"] = color_hex
            layer.pixels = new_pixels

        # If active selection exists, also shift selection mask
        if selection and self.initial_selection is not None:
            new_sel = set()
            for sx, sy in self.initial_selection:
                nx, ny = sx + dx_val, sy + dy_val
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
        self.moving_path = False
        self.initial_anchors = []
        self.initial_bbox = None
        self.drag_start = None
        self.initial_layers_pixels = []
        self.initial_selection = None
        return was_drawing

    def nudge(
        self,
        doc: PixelDocument,
        dx: int,
        dy: int,
        selection: Optional[SelectionModel] = None,
        path_panel_open: bool = False,
    ) -> bool:
        """Nudges active and selected layers' pixels (or active vector path when Paths Panel is open) by dx, dy."""
        if path_panel_open and doc.active_path:
            for anchor in doc.active_path.anchors:
                anchor.x += float(dx)
                anchor.y += float(dy)
            return True

        target_layers = [l for l in doc.selected_layers if l and not l.locked and l.visible]
        if not target_layers:
            return False

        for layer in target_layers:
            new_pixels: Dict[str, str] = {}
            for coord_str, color_hex in layer.pixels.items():
                parts = coord_str.split(",")
                if len(parts) == 2:
                    px, py = int(parts[0]), int(parts[1])
                    nx, ny = px + dx, py + dy
                    new_pixels[f"{nx},{ny}"] = color_hex
            layer.pixels = new_pixels

        if selection and not selection.is_empty():
            new_sel = set()
            for sx, sy in selection.selected:
                nx, ny = sx + dx, sy + dy
                if doc.is_valid_coord(nx, ny):
                    new_sel.add((nx, ny))
            selection.selected = new_sel

        return True
