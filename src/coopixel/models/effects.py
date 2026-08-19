"""
Layer Effects System for Coopixel.
Provides modular, extensible layer effects (starting with Stroke).
"""

from typing import Dict, List, Optional, Set, Tuple


class LayerEffect:
    """Base class for all layer effects."""

    type_name: str = "base"
    display_name: str = "Base Effect"

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def render_effect(self, pixels: Dict[str, str], doc_width: int, doc_height: int) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Given base layer pixels dict {"x,y": "#RRGGBBAA"}, returns:
        (below_pixels, above_pixels) dicts of extra/modified pixels to render below or above the base layer.
        """
        return {}, {}

    def to_dict(self) -> dict:
        return {"type": self.type_name, "enabled": self.enabled}

    @classmethod
    def from_dict(cls, data: dict) -> "LayerEffect":
        return cls(enabled=data.get("enabled", True))


class StrokeEffect(LayerEffect):
    """Outline stroke effect for layer pixels.
    Supports outside, inside, and center positions with customizable width and color.
    """

    type_name: str = "stroke"
    display_name: str = "Stroke"

    POSITION_OUTSIDE = "outside"
    POSITION_INSIDE = "inside"
    POSITION_CENTER = "center"

    def __init__(
        self,
        enabled: bool = True,
        size: int = 1,
        color: str = "#000000FF",
        position: str = "outside",
    ):
        super().__init__(enabled=enabled)
        self.size: int = max(1, min(10, int(size)))
        self.color: str = color
        self.position: str = position if position in (self.POSITION_OUTSIDE, self.POSITION_INSIDE, self.POSITION_CENTER) else self.POSITION_OUTSIDE

    def render_effect(self, pixels: Dict[str, str], doc_width: int, doc_height: int) -> Tuple[Dict[str, str], Dict[str, str]]:
        if not self.enabled or not pixels or self.size <= 0:
            return {}, {}

        # Parse filled coordinates
        filled_coords: Set[Tuple[int, int]] = set()
        for coord_str in pixels.keys():
            parts = coord_str.split(",")
            if len(parts) == 2:
                filled_coords.add((int(parts[0]), int(parts[1])))

        if not filled_coords:
            return {}, {}

        below_dict: Dict[str, str] = {}
        above_dict: Dict[str, str] = {}

        if self.position == self.POSITION_OUTSIDE:
            # Expand outside filled pixels up to self.size Chebyshev/Euclidean distance
            stroke_coords: Set[Tuple[int, int]] = set()
            radius = self.size
            for cx, cy in filled_coords:
                for dx in range(-radius, radius + 1):
                    for dy in range(-radius, radius + 1):
                        if dx == 0 and dy == 0:
                            continue
                        if dx * dx + dy * dy <= (radius + 0.5) ** 2:
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < doc_width and 0 <= ny < doc_height:
                                stroke_coords.add((nx, ny))

            # Outside stroke is placed below layer pixels
            for sx, sy in stroke_coords - filled_coords:
                below_dict[f"{sx},{sy}"] = self.color

        elif self.position == self.POSITION_INSIDE:
            # Identify filled pixels that border an empty pixel or canvas boundary
            stroke_coords: Set[Tuple[int, int]] = set()
            radius = self.size
            for cx, cy in filled_coords:
                is_border = False
                for dx in range(-radius, radius + 1):
                    for dy in range(-radius, radius + 1):
                        if dx == 0 and dy == 0:
                            continue
                        if dx * dx + dy * dy <= (radius + 0.5) ** 2:
                            nx, ny = cx + dx, cy + dy
                            if not (0 <= nx < doc_width and 0 <= ny < doc_height) or (nx, ny) not in filled_coords:
                                is_border = True
                                break
                    if is_border:
                        break
                if is_border:
                    stroke_coords.add((cx, cy))

            # Inside stroke is placed above layer pixels
            for sx, sy in stroke_coords:
                above_dict[f"{sx},{sy}"] = self.color

        elif self.position == self.POSITION_CENTER:
            # Half inside, half outside
            out_radius = max(1, self.size // 2)
            stroke_coords: Set[Tuple[int, int]] = set()
            for cx, cy in filled_coords:
                for dx in range(-out_radius, out_radius + 1):
                    for dy in range(-out_radius, out_radius + 1):
                        if dx * dx + dy * dy <= (out_radius + 0.5) ** 2:
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < doc_width and 0 <= ny < doc_height:
                                stroke_coords.add((nx, ny))

            for sx, sy in stroke_coords:
                if (sx, sy) in filled_coords:
                    above_dict[f"{sx},{sy}"] = self.color
                else:
                    below_dict[f"{sx},{sy}"] = self.color

        return below_dict, above_dict

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "size": self.size,
            "color": self.color,
            "position": self.position,
        })
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "StrokeEffect":
        return cls(
            enabled=data.get("enabled", True),
            size=int(data.get("size", 1)),
            color=data.get("color", "#000000FF"),
            position=data.get("position", "outside"),
        )


def effect_from_dict(data: dict) -> Optional[LayerEffect]:
    """Factory helper to construct a LayerEffect instance from dictionary serialization."""
    if not isinstance(data, dict):
        return None
    type_name = data.get("type", "")
    if type_name == StrokeEffect.type_name:
        return StrokeEffect.from_dict(data)
    return None
