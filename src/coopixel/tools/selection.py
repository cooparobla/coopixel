"""
Selection Tool for Coopixel.
Supports multiple selection modes: draw (paint), box, circle, fill-contiguous, fill-global.
"""

import math
from typing import Dict, Optional, Set, Tuple
from coopixel.models.document import PixelDocument
from coopixel.models.selection import SelectionModel
from coopixel.tools.base import Tool
from coopixel.tools.drawing import bresenham_line, flood_fill_coords, fill_all_coords, get_brush_coords


def _ellipse_coords(x0: int, y0: int, x1: int, y1: int) -> Set[Tuple[int, int]]:
    """Return all pixel coords inside (or on) the ellipse defined by bounding box (x0,y0)-(x1,y1)."""
    lx, rx = min(x0, x1), max(x0, x1)
    ty, by = min(y0, y1), max(y0, y1)
    cx = (lx + rx) / 2.0
    cy = (ty + by) / 2.0
    ra = max((rx - lx) / 2.0, 0.5)
    rb = max((by - ty) / 2.0, 0.5)
    result = set()
    for px in range(lx, rx + 1):
        for py in range(ty, by + 1):
            dx = (px + 0.5 - cx) / ra
            dy = (py + 0.5 - cy) / rb
            if dx * dx + dy * dy <= 1.0:
                result.add((px, py))
    return result


def _rect_coords(x0: int, y0: int, x1: int, y1: int) -> Set[Tuple[int, int]]:
    """Return all pixel coords inside the rectangle defined by (x0,y0)-(x1,y1)."""
    lx, rx = min(x0, x1), max(x0, x1)
    ty, by = min(y0, y1), max(y0, y1)
    return {(px, py) for px in range(lx, rx + 1) for py in range(ty, by + 1)}


class SelectionTool(Tool):
    """Pixel selection tool with multiple modes.

    Modes:
      draw        - paint pixels into/out of selection with brush
      box         - drag to select a rectangular region
      circle      - drag to select an elliptical region
      fill_contig - click to flood-select contiguous same-color pixels
      fill_global - click to select ALL pixels of the same color
    """

    name = "selection"
    display_name = "Selection"

    DRAW = "draw"
    BOX = "box"
    CIRCLE = "circle"
    FILL_CONTIG = "fill_contig"
    FILL_GLOBAL = "fill_global"

    def __init__(self, selection: Optional[SelectionModel] = None):
        super().__init__()
        self.selection: SelectionModel = selection if selection is not None else SelectionModel()
        self.mode: str = self.BOX
        # Drag start for box/circle
        self._drag_start: Optional[Tuple[int, int]] = None
        # Whether to ADD to or REPLACE selection (Shift = add, Alt = remove)
        self._op: str = "replace"   # "replace" | "add" | "remove"

    # ------------------------------------------------------------------
    # Tool interface
    # ------------------------------------------------------------------

    def mouse_press(self, doc: PixelDocument, x: int, y: int, primary_color: str, secondary_color: str, size: int = 1, filled: bool = False, selection=None) -> bool:
        super().mouse_press(doc, x, y, primary_color, secondary_color, size, filled, selection)
        self._drag_start = (x, y)

        if self.mode == self.DRAW:
            self._paint_select(x, y, size)
        elif self.mode in (self.BOX, self.CIRCLE):
            pass  # Will apply on release (live preview via get_preview_pixels)
        elif self.mode == self.FILL_CONTIG:
            layer = doc.active_layer
            if layer:
                coords = flood_fill_coords(doc, layer, x, y)
                self._apply(coords)
        elif self.mode == self.FILL_GLOBAL:
            layer = doc.active_layer
            if layer:
                coords = fill_all_coords(doc, layer, x, y)
                self._apply(coords)
        return False  # Selection tool doesn't modify the document

    def mouse_move(self, doc: PixelDocument, x: int, y: int, primary_color: str, secondary_color: str, size: int = 1, filled: bool = False, selection=None) -> bool:
        if not self.is_drawing:
            return False
        if self.mode == self.DRAW:
            # Paint-select along the drag path
            if self._drag_start:
                sx, sy = self.last_x, self.last_y
                for lx, ly in bresenham_line(sx, sy, x, y):
                    self._paint_select(lx, ly, size)
            self.last_x = x
            self.last_y = y
        # Box/circle update is driven by get_preview_pixels; no doc change
        return False

    def mouse_release(self, doc: PixelDocument, x: int, y: int, primary_color: str, secondary_color: str, size: int = 1, filled: bool = False, selection=None) -> bool:
        super().mouse_release(doc, x, y, primary_color, secondary_color, size, filled, selection)
        if self._drag_start is None:
            return False

        if self.mode == self.BOX:
            coords = _rect_coords(self._drag_start[0], self._drag_start[1], x, y)
            coords = {c for c in coords if doc.is_valid_coord(*c)}
            self._apply(coords)
        elif self.mode == self.CIRCLE:
            coords = _ellipse_coords(self._drag_start[0], self._drag_start[1], x, y)
            coords = {c for c in coords if doc.is_valid_coord(*c)}
            self._apply(coords)

        self._drag_start = None
        return False  # Selection changes don't write to the document

    def get_preview_pixels(self, doc: PixelDocument, hover_x: int, hover_y: int, primary_color: str, brush_size: int = 1, filled: bool = False, selection=None) -> Dict[Tuple[int, int], str]:

        """Show a live rubber-band outline for box/circle modes."""
        preview: Dict[Tuple[int, int], str] = {}
        if not self.is_drawing or self._drag_start is None:
            return preview

        OUTLINE_COLOR = "#5B9BFFCC"

        if self.mode == self.BOX:
            sx, sy = self._drag_start
            lx, rx = min(sx, hover_x), max(sx, hover_x)
            ty, by = min(sy, hover_y), max(sy, hover_y)
            for px in range(lx, rx + 1):
                preview[(px, ty)] = OUTLINE_COLOR
                preview[(px, by)] = OUTLINE_COLOR
            for py in range(ty, by + 1):
                preview[(lx, py)] = OUTLINE_COLOR
                preview[(rx, py)] = OUTLINE_COLOR

        elif self.mode == self.CIRCLE:
            coords = _ellipse_coords(self._drag_start[0], self._drag_start[1], hover_x, hover_y)
            for c in coords:
                if doc.is_valid_coord(*c):
                    preview[c] = OUTLINE_COLOR

        return preview

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _paint_select(self, x: int, y: int, size: int) -> None:
        for px, py in get_brush_coords(x, y, size):
            if self._op == "remove":
                self.selection.selected.discard((px, py))
            else:
                self.selection.selected.add((px, py))

    def _apply(self, coords: Set[Tuple[int, int]]) -> None:
        if self._op == "replace":
            self.selection.replace(coords)
        elif self._op == "add":
            self.selection.select(coords)
        elif self._op == "remove":
            self.selection.deselect(coords)
