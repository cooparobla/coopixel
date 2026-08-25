"""
Vector Path & Bezier Anchor Point Models for Coopixel.
Provides AnchorPoint and VectorPath for Photoshop-style vector path editing and rasterization.
"""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath


class AnchorPoint:
    """
    Represents a single anchor point in a vector Bezier curve.
    (x, y) is the main anchor position.
    handle_in is the incoming control handle offset relative to (x, y).
    handle_out is the outgoing control handle offset relative to (x, y).
    """

    def __init__(
        self,
        x: float,
        y: float,
        handle_in_x: float = 0.0,
        handle_in_y: float = 0.0,
        handle_out_x: float = 0.0,
        handle_out_y: float = 0.0,
    ):
        self.x: float = float(x)
        self.y: float = float(y)
        self.handle_in_x: float = float(handle_in_x)
        self.handle_in_y: float = float(handle_in_y)
        self.handle_out_x: float = float(handle_out_x)
        self.handle_out_y: float = float(handle_out_y)

    @property
    def handle_in_abs(self) -> QPointF:
        return QPointF(self.x + self.handle_in_x, self.y + self.handle_in_y)

    @property
    def handle_out_abs(self) -> QPointF:
        return QPointF(self.x + self.handle_out_x, self.y + self.handle_out_y)

    def set_handle_in_abs(self, abs_x: float, abs_y: float) -> None:
        self.handle_in_x = abs_x - self.x
        self.handle_in_y = abs_y - self.y

    def set_handle_out_abs(self, abs_x: float, abs_y: float) -> None:
        self.handle_out_x = abs_x - self.x
        self.handle_out_y = abs_y - self.y

    def to_dict(self) -> Dict[str, float]:
        return {
            "x": self.x,
            "y": self.y,
            "handle_in_x": self.handle_in_x,
            "handle_in_y": self.handle_in_y,
            "handle_out_x": self.handle_out_x,
            "handle_out_y": self.handle_out_y,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AnchorPoint":
        return cls(
            x=d.get("x", 0.0),
            y=d.get("y", 0.0),
            handle_in_x=d.get("handle_in_x", 0.0),
            handle_in_y=d.get("handle_in_y", 0.0),
            handle_out_x=d.get("handle_out_x", 0.0),
            handle_out_y=d.get("handle_out_y", 0.0),
        )


class VectorPath:
    """
    Represents a vector path consisting of anchor points connected by Bezier curves.
    Associated with a target layer for rasterization.
    """

    def __init__(
        self,
        name: str = "Path 1",
        layer_id: str = "",
        anchors: Optional[List[AnchorPoint]] = None,
        closed: bool = False,
        visible: bool = True,
    ):
        self.name: str = name
        self.layer_id: str = layer_id
        self.anchors: List[AnchorPoint] = anchors if anchors is not None else []
        self.closed: bool = closed
        self.visible: bool = visible

    def add_anchor(self, anchor: AnchorPoint) -> None:
        self.anchors.append(anchor)

    def remove_anchor(self, index: int) -> None:
        if 0 <= index < len(self.anchors):
            self.anchors.pop(index)

    def to_qpainterpath(self) -> QPainterPath:
        """Constructs a PySide6 QPainterPath representing the Bezier curve."""

        path = QPainterPath()
        if not self.anchors:
            return path

        p0 = self.anchors[0]
        path.moveTo(p0.x, p0.y)

        n = len(self.anchors)
        for i in range(1, n):
            prev = self.anchors[i - 1]
            curr = self.anchors[i]
            c1 = prev.handle_out_abs
            c2 = curr.handle_in_abs
            path.cubicTo(c1.x(), c1.y(), c2.x(), c2.y(), curr.x, curr.y)

        if self.closed and n > 1:
            last = self.anchors[-1]
            first = self.anchors[0]
            c1 = last.handle_out_abs
            c2 = first.handle_in_abs
            path.cubicTo(c1.x(), c1.y(), c2.x(), c2.y(), first.x, first.y)
            path.closeSubpath()

        return path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "layer_id": self.layer_id,
            "anchors": [a.to_dict() for a in self.anchors],
            "closed": self.closed,
            "visible": self.visible,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VectorPath":
        anchors_data = d.get("anchors", [])
        anchors = [AnchorPoint.from_dict(a) for a in anchors_data]
        return cls(
            name=d.get("name", "Path"),
            layer_id=d.get("layer_id", ""),
            anchors=anchors,
            closed=d.get("closed", False),
            visible=d.get("visible", True),
        )
