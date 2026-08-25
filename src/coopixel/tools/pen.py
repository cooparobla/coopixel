"""
Photoshop-style Vector Pen Tool for Coopixel.
Allows adding, dragging, and manipulating Bezier curve anchor points and handles on canvas.
"""

import math
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from PySide6.QtCore import QPointF
from coopixel.models.document import PixelDocument
from coopixel.models.path import AnchorPoint, VectorPath
from coopixel.tools.base import Tool

if TYPE_CHECKING:
    from coopixel.models.selection import SelectionModel


class PenTool(Tool):
    """
    Photoshop-style Pen Tool.
    Creates and edits vector Bezier paths.
    """

    name: str = "pen"
    display_name: str = "Pen Tool"

    def __init__(self):
        super().__init__()
        self.selected_anchor_idx: Optional[int] = None
        self.selected_handle: Optional[str] = None  # "anchor", "handle_in", "handle_out"
        self.is_dragging_handle: bool = False

    def _find_target(
        self, path: VectorPath, x: float, y: float, threshold: float = 1.5
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        Finds if (x, y) is near an anchor point or control handle.
        Returns (anchor_index, handle_type) where handle_type is "anchor", "handle_in", or "handle_out".
        """
        # First check active/selected anchor's handles
        if self.selected_anchor_idx is not None and 0 <= self.selected_anchor_idx < len(path.anchors):
            anchor = path.anchors[self.selected_anchor_idx]
            # Check handle_in
            hin = anchor.handle_in_abs
            if math.hypot(x - hin.x(), y - hin.y()) <= threshold:
                return self.selected_anchor_idx, "handle_in"
            # Check handle_out
            hout = anchor.handle_out_abs
            if math.hypot(x - hout.x(), y - hout.y()) <= threshold:
                return self.selected_anchor_idx, "handle_out"

        # Next check anchor positions
        for idx, anchor in enumerate(path.anchors):
            if math.hypot(x - anchor.x, y - anchor.y) <= threshold:
                return idx, "anchor"

        return None, None

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
        shift_pressed: bool = False,
    ) -> bool:
        self.is_drawing = True
        self.start_x = x
        self.start_y = y
        self.last_x = x
        self.last_y = y

        # Ensure document has an active path
        if not doc.active_path:
            doc.add_path()

        path = doc.active_path
        if not path:
            return False

        fx, fy = float(x), float(y)
        target_idx, target_type = self._find_target(path, fx, fy)

        if target_idx is not None:
            # Check if clicking on first anchor point to close loop
            if target_idx == 0 and len(path.anchors) >= 3 and not path.closed and target_type == "anchor":
                path.closed = True
                self.selected_anchor_idx = 0
                self.selected_handle = "anchor"
                self.is_dragging_handle = False
                return True

            self.selected_anchor_idx = target_idx
            self.selected_handle = target_type
            if target_type == "anchor":
                # Shift-click alters Bezier curve handles; normal click moves node position
                if shift_pressed:
                    self.is_dragging_handle = True
                else:
                    self.is_dragging_handle = False
            return True


        # Clicked empty space -> Add new anchor point
        new_anchor = AnchorPoint(fx, fy)
        path.add_anchor(new_anchor)
        self.selected_anchor_idx = len(path.anchors) - 1
        self.selected_handle = "handle_out"
        self.is_dragging_handle = True
        return True

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
        self.last_x = x
        self.last_y = y

        path = doc.active_path
        if not self.is_drawing or not path or self.selected_anchor_idx is None:
            return False

        if not (0 <= self.selected_anchor_idx < len(path.anchors)):
            return False

        anchor = path.anchors[self.selected_anchor_idx]
        fx, fy = float(x), float(y)

        if self.is_dragging_handle:
            # Dragging outgoing handle & symmetric incoming handle
            anchor.set_handle_out_abs(fx, fy)
            anchor.set_handle_in_abs(2 * anchor.x - fx, 2 * anchor.y - fy)
            return True

        if self.selected_handle == "anchor":
            anchor.x = fx
            anchor.y = fy
            return True

        if self.selected_handle == "handle_in":
            anchor.set_handle_in_abs(fx, fy)
            return True

        if self.selected_handle == "handle_out":
            anchor.set_handle_out_abs(fx, fy)
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
        selection: Optional["SelectionModel"] = None,
    ) -> bool:
        self.is_drawing = False
        self.is_dragging_handle = False
        return False

    def delete_selected_anchor(self, doc: PixelDocument) -> bool:
        path = doc.active_path
        if path and self.selected_anchor_idx is not None:
            if 0 <= self.selected_anchor_idx < len(path.anchors):
                path.remove_anchor(self.selected_anchor_idx)
                if not path.anchors:
                    self.selected_anchor_idx = None
                else:
                    self.selected_anchor_idx = max(0, self.selected_anchor_idx - 1)
                return True
        return False
