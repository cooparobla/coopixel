"""
Move tool for Coopixel pixel art editor.
Shifts the active layer pixels (and active selection) interactively across the canvas.
"""

from typing import Dict, Optional, Set, Tuple
from coopixel.models.document import PixelDocument
from coopixel.models.selection import SelectionModel
from coopixel.tools.base import Tool


class MoveTool(Tool):
    """Tool for moving active layer pixels by dragging or nudging."""

    name: str = "move"
    display_name: str = "Move Tool"

    def __init__(self):
        super().__init__()
        self.drag_start: Optional[Tuple[int, int]] = None
        self.initial_pixels: Dict[str, str] = {}
        self.initial_selection: Optional[Set[Tuple[int, int]]] = None

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
        self.drag_start = (x, y)
        active = doc.active_layer
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
