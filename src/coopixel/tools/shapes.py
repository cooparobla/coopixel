"""
Shape tools for Coopixel: Line, Rectangle, and Circle with live preview.
"""

from typing import Dict, List, Set, Tuple
from coopixel.models.document import PixelDocument
from coopixel.tools.base import Tool, is_pixel_editable
from coopixel.tools.drawing import bresenham_line, get_brush_coords


def get_rectangle_pixels(x0: int, y0: int, x1: int, y1: int, filled: bool) -> List[Tuple[int, int]]:
    min_x, max_x = min(x0, x1), max(x0, x1)
    min_y, max_y = min(y0, y1), max(y0, y1)

    pixels = []
    for x in range(min_x, max_x + 1):
        for y in range(min_y, max_y + 1):
            if filled or x == min_x or x == max_x or y == min_y or y == max_y:
                pixels.append((x, y))
    return pixels


def get_circle_pixels(x0: int, y0: int, x1: int, y1: int, filled: bool) -> List[Tuple[int, int]]:
    min_x, max_x = min(x0, x1), max(x0, x1)
    min_y, max_y = min(y0, y1), max(y0, y1)

    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    rx = (max_x - min_x) / 2.0
    ry = (max_y - min_y) / 2.0

    if rx <= 0 or ry <= 0:
        return [(min_x, min_y)]

    pixels = []
    for x in range(min_x, max_x + 1):
        for y in range(min_y, max_y + 1):
            norm_val = ((x - center_x) / rx) ** 2 + ((y - center_y) / ry) ** 2
            if filled:
                if norm_val <= 1.05:
                    pixels.append((x, y))
            else:
                if 0.75 <= norm_val <= 1.25:
                    pixels.append((x, y))
    return pixels


class LineTool(Tool):
    name = "line"
    display_name = "Line"

    def get_preview_pixels(self, doc: PixelDocument, x: int, y: int, primary_color: str, size: int = 1, filled: bool = False, selection=None) -> Dict[Tuple[int, int], str]:
        if not self.is_drawing:
            return {}
        preview = {}
        line_pts = bresenham_line(self.start_x, self.start_y, x, y)
        for lx, ly in line_pts:
            for px, py in get_brush_coords(lx, ly, size):
                if doc.is_valid_coord(px, py) and is_pixel_editable(selection, px, py):
                    preview[(px, py)] = primary_color
        return preview

    def mouse_release(self, doc: PixelDocument, x: int, y: int, primary_color: str, secondary_color: str, size: int = 1, filled: bool = False, selection=None) -> bool:
        if not self.is_drawing:
            return False
        super().mouse_release(doc, x, y, primary_color, secondary_color, size, filled, selection)
        layer = doc.active_layer
        if not layer or layer.locked or not layer.visible:
            return False

        changed = False
        line_pts = bresenham_line(self.start_x, self.start_y, x, y)
        for lx, ly in line_pts:
            for px, py in get_brush_coords(lx, ly, size):
                if doc.is_valid_coord(px, py) and is_pixel_editable(selection, px, py):
                    layer.set_pixel(px, py, primary_color)
                    changed = True
        return changed


class RectangleTool(Tool):
    name = "rectangle"
    display_name = "Rectangle"

    def get_preview_pixels(self, doc: PixelDocument, x: int, y: int, primary_color: str, size: int = 1, filled: bool = False, selection=None) -> Dict[Tuple[int, int], str]:
        if not self.is_drawing:
            return {}
        preview = {}
        pts = get_rectangle_pixels(self.start_x, self.start_y, x, y, filled)
        for px, py in pts:
            if doc.is_valid_coord(px, py) and is_pixel_editable(selection, px, py):
                preview[(px, py)] = primary_color
        return preview

    def mouse_release(self, doc: PixelDocument, x: int, y: int, primary_color: str, secondary_color: str, size: int = 1, filled: bool = False, selection=None) -> bool:
        if not self.is_drawing:
            return False
        super().mouse_release(doc, x, y, primary_color, secondary_color, size, filled, selection)
        layer = doc.active_layer
        if not layer or layer.locked or not layer.visible:
            return False

        changed = False
        pts = get_rectangle_pixels(self.start_x, self.start_y, x, y, filled)
        for px, py in pts:
            if doc.is_valid_coord(px, py) and is_pixel_editable(selection, px, py):
                layer.set_pixel(px, py, primary_color)
                changed = True
        return changed


class CircleTool(Tool):
    name = "circle"
    display_name = "Circle"

    def get_preview_pixels(self, doc: PixelDocument, x: int, y: int, primary_color: str, size: int = 1, filled: bool = False, selection=None) -> Dict[Tuple[int, int], str]:
        if not self.is_drawing:
            return {}
        preview = {}
        pts = get_circle_pixels(self.start_x, self.start_y, x, y, filled)
        for px, py in pts:
            if doc.is_valid_coord(px, py) and is_pixel_editable(selection, px, py):
                preview[(px, py)] = primary_color
        return preview

    def mouse_release(self, doc: PixelDocument, x: int, y: int, primary_color: str, secondary_color: str, size: int = 1, filled: bool = False, selection=None) -> bool:
        if not self.is_drawing:
            return False
        super().mouse_release(doc, x, y, primary_color, secondary_color, size, filled, selection)
        layer = doc.active_layer
        if not layer or layer.locked or not layer.visible:
            return False

        changed = False
        pts = get_circle_pixels(self.start_x, self.start_y, x, y, filled)
        for px, py in pts:
            if doc.is_valid_coord(px, py) and is_pixel_editable(selection, px, py):
                layer.set_pixel(px, py, primary_color)
                changed = True
        return changed
