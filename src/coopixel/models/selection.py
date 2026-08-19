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
