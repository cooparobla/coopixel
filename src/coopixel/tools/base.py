"""
Base Tool interface for Coopixel drawing tools.
"""

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from coopixel.models.document import PixelDocument

if TYPE_CHECKING:
    from coopixel.models.selection import SelectionModel


def is_pixel_editable(selection: Optional["SelectionModel"], x: int, y: int) -> bool:
    """Returns True if the coordinate (x, y) can be edited given the current selection mask."""
    if selection is None or selection.is_empty():
        return True
    return selection.is_selected(x, y)


class Tool:
    """Abstract base class for editor tools."""

    name: str = "base"
    display_name: str = "Base Tool"

    def __init__(self):
        self.is_drawing: bool = False
        self.start_x: int = 0
        self.start_y: int = 0
        self.last_x: int = 0
        self.last_y: int = 0

    def mouse_press(
        self,
        doc: PixelDocument,
        x: int,
        y: int,
        primary_color: str,
        secondary_color: str,
        size: int = 1,
        filled: bool = False,
        selection: Optional["SelectionModel"] = None,
    ) -> bool:
        """Called when mouse press occurs on canvas. Returns True if document was modified."""
        self.is_drawing = True
        self.start_x = x
        self.start_y = y
        self.last_x = x
        self.last_y = y
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
        selection: Optional["SelectionModel"] = None,
    ) -> bool:
        """Called when mouse moves while dragging. Returns True if document was modified."""
        self.last_x = x
        self.last_y = y
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
        selection: Optional["SelectionModel"] = None,
    ) -> bool:
        """Called when mouse release occurs. Returns True if document was modified."""
        self.is_drawing = False
        self.last_x = x
        self.last_y = y
        return False

    def get_preview_pixels(
        self,
        doc: PixelDocument,
        x: int,
        y: int,
        primary_color: str,
        size: int = 1,
        filled: bool = False,
        selection: Optional["SelectionModel"] = None,
    ) -> Dict[Tuple[int, int], str]:
        """Returns dict of (x, y) -> hex_color for live preview rendering on canvas (e.g., shape previews)."""
        return {}

