"""
Color Picker Eyedropper tool for Coopixel.
"""

from typing import Callable, Optional
from coopixel.models.document import PixelDocument
from coopixel.tools.base import Tool


class ColorPickerTool(Tool):
    name = "picker"
    display_name = "Color Picker"

    def __init__(self, on_color_picked: Optional[Callable[[str], None]] = None):
        super().__init__()
        self.on_color_picked = on_color_picked

    def mouse_press(self, doc: PixelDocument, x: int, y: int, primary_color: str, secondary_color: str, size: int = 1, filled: bool = False, selection=None, *args, **kwargs) -> bool:
        super().mouse_press(doc, x, y, primary_color, secondary_color, size, filled, selection, *args, **kwargs)


        if not doc.is_valid_coord(x, y):
            return False

        layer = doc.active_layer
        if not layer:
            return False

        color_hex = layer.get_pixel(x, y)
        if color_hex and self.on_color_picked:
            self.on_color_picked(color_hex)
        return False
