"""
SelectionModel: tracks the current pixel selection state.
"""

from typing import Set, Tuple
from coopixel.models.document import PixelDocument


class SelectionModel:
    """Tracks which pixels are currently selected."""

    def __init__(self):
        self.selected: Set[Tuple[int, int]] = set()

    def is_empty(self) -> bool:
        return len(self.selected) == 0

    def is_selected(self, x: int, y: int) -> bool:
        return (x, y) in self.selected

    def select(self, coords) -> None:
        for c in coords:
            self.selected.add(c)

    def deselect(self, coords) -> None:
        for c in coords:
            self.selected.discard(c)

    def toggle(self, x: int, y: int) -> None:
        if (x, y) in self.selected:
            self.selected.discard((x, y))
        else:
            self.selected.add((x, y))

    def replace(self, coords) -> None:
        self.selected = set(coords)

    def clear(self) -> None:
        self.selected.clear()

    def select_all(self, doc: PixelDocument) -> None:
        self.selected = {(x, y) for x in range(doc.width) for y in range(doc.height)}

    def invert(self, doc: PixelDocument) -> None:
        all_px = {(x, y) for x in range(doc.width) for y in range(doc.height)}
        self.selected = all_px - self.selected

    def select_layer_pixels(self, layer, doc: PixelDocument) -> None:
        """Selects every pixel that the layer has values for within the document bounds."""
        coords = set()
        for key, val in layer.pixels.items():
            if val and str(val).upper() not in ("#00000000", "TRANSPARENT"):
                parts = key.split(",")
                if len(parts) == 2:
                    x, y = int(parts[0]), int(parts[1])
                    if 0 <= x < doc.width and 0 <= y < doc.height:
                        coords.add((x, y))
        self.replace(coords)

