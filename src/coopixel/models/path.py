"""
Vector Path & Bezier Anchor Point Models for Coopixel.
Provides AnchorPoint and VectorPath for Photoshop-style vector path editing and rasterization.
"""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPen


def _hex_to_qcolor(hex_str: str) -> QColor:
    s = hex_str.lstrip("#")
    if len(s) == 8:
        r, g, b, a = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16)
        return QColor(r, g, b, a)
    elif len(s) == 6:
        r, g, b = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
        return QColor(r, g, b, 255)
    return QColor(hex_str)


def _qcolor_to_hex(col: QColor) -> str:
    return f"#{col.red():02X}{col.green():02X}{col.blue():02X}{col.alpha():02X}"


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
    Associated with a target layer and frame for rasterization & dynamic stroke/fill rendering.
    """

    def __init__(
        self,
        name: str = "Path 1",
        layer_id: str = "",
        anchors: Optional[List[AnchorPoint]] = None,
        closed: bool = False,
        visible: bool = True,
        frame_index: Optional[int] = None,
        stroked: bool = True,
        filled: bool = False,
        stroke_color: str = "#F97316FF",
        fill_color: str = "#F97316FF",
        stroke_width: int = 1,
    ):
        self.name: str = name
        self.layer_id: str = layer_id
        self.anchors: List[AnchorPoint] = anchors if anchors is not None else []
        self.closed: bool = closed
        self.visible: bool = visible
        self.frame_index: Optional[int] = frame_index
        self.stroked: bool = stroked
        self.filled: bool = filled
        self.stroke_color: str = stroke_color
        self.fill_color: str = fill_color
        self.stroke_width: int = stroke_width


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
            "frame_index": self.frame_index,
            "stroked": self.stroked,
            "filled": self.filled,
            "stroke_color": self.stroke_color,
            "fill_color": self.fill_color,
            "stroke_width": self.stroke_width,
        }

    def get_pixel_map(self, width: int, height: int) -> Dict[str, str]:
        """Rasterizes dynamic stroke & fill into pixel map dict ('x,y': '#RRGGBBAA') without anti-aliasing."""
        if not self.anchors or (not self.stroked and not self.filled):
            return {}

        qpath = self.to_qpainterpath()
        img = QImage(width, height, QImage.Format_ARGB32)
        img.fill(QColor(0, 0, 0, 0))

        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing, False)

        if self.filled:
            qcol = _hex_to_qcolor(self.fill_color)
            painter.setBrush(QBrush(qcol))
            if not self.stroked:
                painter.setPen(QPen(qcol, 1))

        if self.stroked:
            scol = _hex_to_qcolor(self.stroke_color)
            pen = QPen(scol, max(1, self.stroke_width))
            painter.setPen(pen)
            if not self.filled:
                painter.setBrush(Qt.NoBrush)

        painter.drawPath(qpath)
        painter.end()

        pixels: Dict[str, str] = {}
        for y in range(height):
            for x in range(width):
                col = img.pixelColor(x, y)
                if col.alpha() > 0:
                    pixels[f"{x},{y}"] = _qcolor_to_hex(col)

        return pixels

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
            frame_index=d.get("frame_index", None),
            stroked=d.get("stroked", True),
            filled=d.get("filled", False),
            stroke_color=d.get("stroke_color", "#F97316FF"),
            fill_color=d.get("fill_color", "#F97316FF"),
            stroke_width=d.get("stroke_width", 1),
        )





