"""
Crop tool for interactive canvas cropping in Coopixel.
Allows drawing a crop box rectangle over canvas and committing the crop.
"""

from typing import Optional, Tuple
from coopixel.models.document import PixelDocument
from coopixel.models.selection import SelectionModel
from coopixel.tools.base import Tool


class CropTool(Tool):
    """Tool for dragging a crop rectangle over the canvas."""

    name: str = "crop"
    display_name: str = "Crop Tool"

    def __init__(self):
        super().__init__()
        self.crop_box: Optional[Tuple[int, int, int, int]] = None  # (x, y, width, height)
        self.is_dragging: bool = False
        self.drag_start: Optional[Tuple[int, int]] = None

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
    ) -> bool:
        self.is_drawing = True
        self.is_dragging = True
        self.drag_start = (x, y)
        self.crop_box = (x, y, 1, 1)
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
        if self.is_dragging and self.drag_start:
            sx, sy = self.drag_start
            min_x = min(sx, x)
            max_x = max(sx, x)
            min_y = min(sy, y)
            max_y = max(sy, y)
            w = max_x - min_x + 1
            h = max_y - min_y + 1
            self.crop_box = (min_x, min_y, w, h)
        return False

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
        self.is_drawing = False
        self.is_dragging = False
        if self.drag_start:
            sx, sy = self.drag_start
            min_x = min(sx, x)
            max_x = max(sx, x)
            min_y = min(sy, y)
            max_y = max(sy, y)
            w = max_x - min_x + 1
            h = max_y - min_y + 1
            self.crop_box = (min_x, min_y, w, h)
        return False

    def clear_box(self) -> None:
        self.crop_box = None

    def set_box(self, x: int, y: int, width: int, height: int) -> None:
        self.crop_box = (x, y, max(1, width), max(1, height))
