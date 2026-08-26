"""
Pivot tool for Coopixel pixel art editor.
Allows interactively setting and dragging the active animation's pivot point on the canvas.
"""

from typing import Any, Optional, Tuple
from coopixel.models.document import PixelDocument
from coopixel.models.selection import SelectionModel
from coopixel.tools.base import Tool


class PivotTool(Tool):
    """Tool for positioning the active animation's pivot point."""

    name: str = "pivot"
    display_name: str = "Pivot Tool"

    def __init__(self):
        super().__init__()
        self.is_dragging: bool = False

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
        super().mouse_press(doc, x, y, primary_color, secondary_color, size, filled, selection, *args, **kwargs)
        self.is_dragging = True
        anim = doc.active_animation if doc else None
        if anim:
            if anim.pivot_x != x or anim.pivot_y != y:
                anim.pivot_x = x
                anim.pivot_y = y
                return True
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
        if not self.is_drawing and not self.is_dragging:
            return False
        anim = doc.active_animation if doc else None
        if anim:
            if anim.pivot_x != x or anim.pivot_y != y:
                anim.pivot_x = x
                anim.pivot_y = y
                return True
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
        super().mouse_release(doc, x, y, primary_color, secondary_color, size, filled, selection, *args, **kwargs)
        self.is_dragging = False
        anim = doc.active_animation if doc else None
        if anim:
            if anim.pivot_x != x or anim.pivot_y != y:
                anim.pivot_x = x
                anim.pivot_y = y
                return True
        return False
