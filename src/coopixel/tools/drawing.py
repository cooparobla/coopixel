"""
Drawing tools for Coopixel: Pencil, Eraser, and Flood Bucket Fill.
"""

from collections import deque
from typing import Dict, List, Optional, Set, Tuple
from coopixel.models.document import PixelDocument
from coopixel.tools.base import Tool, is_pixel_editable


def bresenham_line(x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
    """Returns list of (x, y) coordinates along a line using Bresenham's algorithm."""
    points = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    x, y = x0, y0
    while True:
        points.append((x, y))
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    return points


def get_brush_coords(center_x: int, center_y: int, size: int) -> List[Tuple[int, int]]:
    """Returns list of (x, y) coordinates within a square brush centered at (center_x, center_y)."""
    coords = []
    half = size // 2
    for dx in range(-half, size - half):
        for dy in range(-half, size - half):
            coords.append((center_x + dx, center_y + dy))
    return coords


def flood_fill_coords(doc: PixelDocument, layer, x: int, y: int) -> Set[Tuple[int, int]]:
    """Return the set of contiguous pixel coords with the same color as (x, y)."""
    if not doc.is_valid_coord(x, y):
        return set()
    target_color = layer.get_pixel(x, y)
    queue = deque([(x, y)])
    visited: Set[Tuple[int, int]] = {(x, y)}
    result: Set[Tuple[int, int]] = set()
    while queue:
        cx, cy = queue.popleft()
        if layer.get_pixel(cx, cy) == target_color:
            result.add((cx, cy))
            for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if (nx, ny) not in visited and doc.is_valid_coord(nx, ny):
                    visited.add((nx, ny))
                    queue.append((nx, ny))
    return result


def fill_all_coords(doc: PixelDocument, layer, x: int, y: int) -> Set[Tuple[int, int]]:
    """Return all pixels on the document with the same color as (x, y)."""
    if not doc.is_valid_coord(x, y):
        return set()
    target_color = layer.get_pixel(x, y)
    result: Set[Tuple[int, int]] = set()
    for py in range(doc.height):
        for px in range(doc.width):
            if layer.get_pixel(px, py) == target_color:
                result.add((px, py))
    return result


class PencilTool(Tool):
    name = "pencil"
    display_name = "Pencil"

    def mouse_press(self, doc: PixelDocument, x: int, y: int, primary_color: str, secondary_color: str, size: int = 1, filled: bool = False, selection=None, *args, **kwargs) -> bool:
        super().mouse_press(doc, x, y, primary_color, secondary_color, size, filled, selection, *args, **kwargs)
        layers = doc.editable_layers
        if not layers:
            return False

        changed = False
        coords = [c for c in get_brush_coords(x, y, size) if doc.is_valid_coord(c[0], c[1]) and is_pixel_editable(selection, c[0], c[1])]
        if coords:
            for layer in layers:
                for px, py in coords:
                    layer.set_pixel(px, py, primary_color)
                changed = True
        return changed

    def mouse_move(self, doc: PixelDocument, x: int, y: int, primary_color: str, secondary_color: str, size: int = 1, filled: bool = False, selection=None, *args, **kwargs) -> bool:
        if not self.is_drawing:
            return False
        layers = doc.editable_layers
        if not layers:
            return False

        changed = False
        line_points = bresenham_line(self.last_x, self.last_y, x, y)
        coords = []
        for lx, ly in line_points:
            for px, py in get_brush_coords(lx, ly, size):
                if doc.is_valid_coord(px, py) and is_pixel_editable(selection, px, py):
                    coords.append((px, py))

        if coords:
            for layer in layers:
                for px, py in coords:
                    layer.set_pixel(px, py, primary_color)
                changed = True

        self.last_x = x
        self.last_y = y
        return changed


class EraserTool(Tool):
    name = "eraser"
    display_name = "Eraser"

    def mouse_press(self, doc: PixelDocument, x: int, y: int, primary_color: str, secondary_color: str, size: int = 1, filled: bool = False, selection=None, *args, **kwargs) -> bool:
        super().mouse_press(doc, x, y, primary_color, secondary_color, size, filled, selection, *args, **kwargs)
        layers = doc.editable_layers
        if not layers:
            return False

        changed = False
        coords = [c for c in get_brush_coords(x, y, size) if doc.is_valid_coord(c[0], c[1]) and is_pixel_editable(selection, c[0], c[1])]
        if coords:
            for layer in layers:
                for px, py in coords:
                    if layer.has_pixel(px, py):
                        layer.clear_pixel(px, py)
                        changed = True
        return changed

    def mouse_move(self, doc: PixelDocument, x: int, y: int, primary_color: str, secondary_color: str, size: int = 1, filled: bool = False, selection=None, *args, **kwargs) -> bool:
        if not self.is_drawing:
            return False
        layers = doc.editable_layers
        if not layers:
            return False

        changed = False
        line_points = bresenham_line(self.last_x, self.last_y, x, y)
        coords = []
        for lx, ly in line_points:
            for px, py in get_brush_coords(lx, ly, size):
                if doc.is_valid_coord(px, py) and is_pixel_editable(selection, px, py):
                    coords.append((px, py))

        if coords:
            for layer in layers:
                for px, py in coords:
                    if layer.has_pixel(px, py):
                        layer.clear_pixel(px, py)
                        changed = True

        self.last_x = x
        self.last_y = y
        return changed


class BucketFillTool(Tool):
    """Flood fill tool. Supports contiguous (flood) and global (all matching pixels) modes."""

    name = "fill"
    display_name = "Bucket Fill"

    CONTIGUOUS = "contiguous"
    GLOBAL = "global"

    def __init__(self):
        super().__init__()
        self.fill_mode: str = self.CONTIGUOUS

    def mouse_press(self, doc: PixelDocument, x: int, y: int, primary_color: str, secondary_color: str, size: int = 1, filled: bool = False, selection=None, *args, **kwargs) -> bool:
        super().mouse_press(doc, x, y, primary_color, secondary_color, size, filled, selection, *args, **kwargs)
        layers = doc.editable_layers
        if not layers or not doc.is_valid_coord(x, y):
            return False

        changed = False
        for layer in layers:
            target_color = layer.get_pixel(x, y)
            if target_color == primary_color:
                continue

            if self.fill_mode == self.CONTIGUOUS:
                coords = flood_fill_coords(doc, layer, x, y)
            else:
                coords = fill_all_coords(doc, layer, x, y)

            for cx, cy in coords:
                if is_pixel_editable(selection, cx, cy):
                    layer.set_pixel(cx, cy, primary_color)
                    changed = True

        return changed



class DrawTool(Tool):
    """Unified drawing tool encompassing Pencil, Line, Rectangle, and Circle modes."""

    name = "draw"
    display_name = "Draw Tool"

    PENCIL = "pencil"
    LINE = "line"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"

    def __init__(self):
        super().__init__()
        from coopixel.tools.shapes import CircleTool, LineTool, RectangleTool

        self.mode: str = self.PENCIL
        self.pencil_tool = PencilTool()
        self.line_tool = LineTool()
        self.rect_tool = RectangleTool()
        self.circle_tool = CircleTool()

    @property
    def active_sub_tool(self) -> Tool:
        if self.mode == self.LINE:
            return self.line_tool
        elif self.mode == self.RECTANGLE:
            return self.rect_tool
        elif self.mode == self.CIRCLE:
            return self.circle_tool
        return self.pencil_tool

    def mouse_press(
        self,
        doc: PixelDocument,
        x: int,
        y: int,
        primary_color: str,
        secondary_color: str,
        size: int = 1,
        filled: bool = False,
        selection=None,
        *args,
        **kwargs,
    ) -> bool:
        self.is_drawing = True
        return self.active_sub_tool.mouse_press(doc, x, y, primary_color, secondary_color, size, filled, selection, *args, **kwargs)

    def mouse_move(
        self,
        doc: PixelDocument,
        x: int,
        y: int,
        primary_color: str,
        secondary_color: str,
        size: int = 1,
        filled: bool = False,
        selection=None,
        *args,
        **kwargs,
    ) -> bool:
        return self.active_sub_tool.mouse_move(doc, x, y, primary_color, secondary_color, size, filled, selection, *args, **kwargs)

    def mouse_release(
        self,
        doc: PixelDocument,
        x: int,
        y: int,
        primary_color: str,
        secondary_color: str,
        size: int = 1,
        filled: bool = False,
        selection=None,
        *args,
        **kwargs,
    ) -> bool:
        self.is_drawing = False
        return self.active_sub_tool.mouse_release(doc, x, y, primary_color, secondary_color, size, filled, selection, *args, **kwargs)


    def get_preview_pixels(
        self,
        doc: PixelDocument,
        x: int,
        y: int,
        primary_color: str,
        size: int = 1,
        filled: bool = False,
        selection=None,
    ) -> Dict[Tuple[int, int], str]:
        if hasattr(self.active_sub_tool, "get_preview_pixels"):
            return self.active_sub_tool.get_preview_pixels(doc, x, y, primary_color, size, filled, selection)
        return {}
