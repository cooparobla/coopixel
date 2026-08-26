"""
Photoshop-style Vector Pen Tool for Coopixel.
Allows adding, dragging, and manipulating Bezier curve anchor points and handles on canvas.
"""

import math
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
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
        self, path: VectorPath, x: float, y: float, threshold: float = 2.5
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
            if math.hypot(x - hin.x(), y - hin.y()) <= threshold and (anchor.handle_in_x != 0 or anchor.handle_in_y != 0):
                return self.selected_anchor_idx, "handle_in"
            # Check handle_out
            hout = anchor.handle_out_abs
            if math.hypot(x - hout.x(), y - hout.y()) <= threshold and (anchor.handle_out_x != 0 or anchor.handle_out_y != 0):
                return self.selected_anchor_idx, "handle_out"

        # Check handles across all anchors if not found on active
        for idx, anchor in enumerate(path.anchors):
            hin = anchor.handle_in_abs
            if math.hypot(x - hin.x(), y - hin.y()) <= threshold and (anchor.handle_in_x != 0 or anchor.handle_in_y != 0):
                return idx, "handle_in"
            hout = anchor.handle_out_abs
            if math.hypot(x - hout.x(), y - hout.y()) <= threshold and (anchor.handle_out_x != 0 or anchor.handle_out_y != 0):
                return idx, "handle_out"

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
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        self.is_drawing = True
        self.start_x = x
        self.start_y = y
        self.last_x = x
        self.last_y = y

        # Ensure document has an active path
        if not doc.active_path:
            doc.add_path(stroke_color=primary_color, fill_color=primary_color)

        path = doc.active_path
        if not path:
            return False

        # Assign primary selected color when starting a stroke / path
        if len(path.anchors) == 0 and primary_color:
            path.stroke_color = primary_color
            path.fill_color = primary_color

        self.initial_path_anchors = [(a.x, a.y) for a in path.anchors]
        fx, fy = float(x), float(y)
        target_idx, target_type = self._find_target(path, fx, fy)

        if target_idx is not None:
            self.selected_anchor_idx = target_idx
            self.selected_handle = target_type

            if target_type == "anchor":
                if shift_pressed:
                    # Shift+click on anchor point pulls out symmetric smooth Bezier handles
                    self.is_dragging_handle = True
                    self.selected_handle = "handle_out"
                else:
                    self.is_dragging_handle = False
                    self.selected_handle = "anchor"
            else:
                # Clicked on control handle knob ("handle_in" or "handle_out")
                self.is_dragging_handle = False

            return True

        # Clicked empty space -> Add new anchor point
        new_anchor = AnchorPoint(fx, fy)
        path.add_anchor(new_anchor)
        self.selected_anchor_idx = len(path.anchors) - 1

        if shift_pressed:
            # Shift+click in empty space creates point and pulls out smooth Bezier handles
            self.selected_handle = "handle_out"
            self.is_dragging_handle = True
        else:
            self.selected_handle = "anchor"
            self.is_dragging_handle = False

        self.initial_path_anchors = [(a.x, a.y) for a in path.anchors]
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
        shift_pressed: bool = False,
        ctrl_pressed: bool = False,
        alt_pressed: bool = False,
        *args: Any,
        **kwargs: Any,
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

        # 1. Dragging symmetric handles via Shift+drag on anchor point
        if self.is_dragging_handle:
            anchor.set_handle_out_abs(fx, fy)
            anchor.set_handle_in_abs(2 * anchor.x - fx, 2 * anchor.y - fy)
            return True

        # 2. Dragging specific handle knobs ("handle_in" or "handle_out")
        if self.selected_handle == "handle_in":
            anchor.set_handle_in_abs(fx, fy)
            if shift_pressed:
                # Shift preserves symmetric opposite handle
                anchor.set_handle_out_abs(2 * anchor.x - fx, 2 * anchor.y - fy)
            return True

        if self.selected_handle == "handle_out":
            anchor.set_handle_out_abs(fx, fy)
            if shift_pressed:
                # Shift preserves symmetric opposite handle
                anchor.set_handle_in_abs(2 * anchor.x - fx, 2 * anchor.y - fy)
            return True

        # 3. Moving anchor node position
        if self.selected_handle == "anchor":
            dx = fx - float(self.start_x)
            dy = fy - float(self.start_y)
            if ctrl_pressed or alt_pressed:
                # Move ALL nodes in the path together
                if hasattr(self, "initial_path_anchors") and len(self.initial_path_anchors) == len(path.anchors):
                    for idx, (orig_x, orig_y) in enumerate(self.initial_path_anchors):
                        path.anchors[idx].x = orig_x + dx
                        path.anchors[idx].y = orig_y + dy
                return True
            else:
                anchor.x = fx
                anchor.y = fy
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
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        was_drawing = self.is_drawing
        self.is_drawing = False
        self.is_dragging_handle = False
        return was_drawing

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
