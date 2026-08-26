"""
Crop tool for interactive canvas cropping in Coopixel.
Allows drawing a crop box rectangle over canvas and committing the crop.
Hold Shift while dragging to constrain the box to a square.
"""

from typing import Any, Optional, Tuple
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
        # Set by canvas on mouse events when Shift is held
        self.constrain_square: bool = False

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _compute_box(self, sx: int, sy: int, ex: int, ey: int) -> Tuple[int, int, int, int]:
        """Computes (x, y, w, h) from drag start/end, applying square constraint if set."""
        min_x = min(sx, ex)
        max_x = max(sx, ex)
        min_y = min(sy, ey)
        max_y = max(sy, ey)
        w = max_x - min_x + 1
        h = max_y - min_y + 1
        if self.constrain_square:
            side = max(w, h)
            # Expand towards the drag direction to keep origin stable
            if ex < sx:
                min_x = sx - side + 1
            if ey < sy:
                min_y = sy - side + 1
            w = h = side
        return (min_x, min_y, w, h)

    # ------------------------------------------------------------------
    # Tool interface
    # ------------------------------------------------------------------

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
        *args: Any,
        **kwargs: Any,
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
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        if self.is_dragging and self.drag_start:
            sx, sy = self.drag_start
            self.crop_box = self._compute_box(sx, sy, x, y)
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
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        if self.is_dragging and self.drag_start:
            sx, sy = self.drag_start
            self.crop_box = self._compute_box(sx, sy, x, y)
        self.is_dragging = False
        self.is_drawing = False
        return False

    def clear_box(self) -> None:
        self.crop_box = None

    def set_box(self, x: int, y: int, width: int, height: int) -> None:
        self.crop_box = (x, y, max(1, width), max(1, height))

    def set_box_wh(self, width: int, height: int) -> None:
        """Resize existing crop box to the given dimensions, keeping its origin."""
        if self.crop_box:
            x, y, _w, _h = self.crop_box
            self.crop_box = (x, y, max(1, width), max(1, height))
