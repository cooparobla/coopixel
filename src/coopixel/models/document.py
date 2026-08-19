"""
Document and Layer data models for Coopixel.
Uses sparse dictionary storage for pixels: only filled/colored pixels are stored ("x,y": "#RRGGBBAA").
Supports extensible layer effects (e.g. Stroke).
"""

from typing import Dict, List, Optional, Tuple
from PySide6.QtGui import QColor, QImage, QPainter
from pycaml import CAMLMap
from coopixel.models.effects import LayerEffect, effect_from_dict


def hex_to_qcolor(hex_str: str) -> QColor:
    s = hex_str.lstrip("#")
    if len(s) == 8:
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
        a = int(s[6:8], 16)
        return QColor(r, g, b, a)
    elif len(s) == 6:
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
        return QColor(r, g, b, 255)
    return QColor(hex_str)


def qcolor_to_hex(qcol: QColor) -> str:
    return f"#{qcol.red():02X}{qcol.green():02X}{qcol.blue():02X}{qcol.alpha():02X}"


class Layer:
    """Represents a single layer in the pixel document."""

    def __init__(self, name: str = "Layer", visible: bool = True, locked: bool = False, opacity: float = 1.0):
        self.name = name
        self.visible = visible
        self.locked = locked
        self.opacity = max(0.0, min(1.0, float(opacity)))
        # Sparse dictionary mapping "x,y" string coordinates to hex color "#RRGGBBAA"
        self.pixels: Dict[str, str] = {}
        # Extensible list of layer effects
        self.effects: List[LayerEffect] = []

    def get_pixel(self, x: int, y: int) -> Optional[str]:
        """Returns "#RRGGBBAA" color string if present, else None."""
        return self.pixels.get(f"{x},{y}")

    def get_pixel_qcolor(self, x: int, y: int) -> Optional[QColor]:
        hex_str = self.get_pixel(x, y)
        if not hex_str:
            return None
        return hex_to_qcolor(hex_str)

    def set_pixel(self, x: int, y: int, hex_color: str) -> None:
        """Sets pixel color. If hex_color is None or fully transparent (#00000000), clears the pixel."""
        if not hex_color or hex_color.upper() in ("#00000000", "TRANSPARENT"):
            self.clear_pixel(x, y)
            return

        qcol = hex_to_qcolor(hex_color)
        if qcol.alpha() == 0:
            self.clear_pixel(x, y)
            return

        # Store standardized #RRGGBBAA format
        self.pixels[f"{x},{y}"] = qcolor_to_hex(qcol)

    def clear_pixel(self, x: int, y: int) -> None:
        key = f"{x},{y}"
        if key in self.pixels:
            del self.pixels[key]

    def clear_all(self) -> None:
        self.pixels.clear()

    def clone(self) -> "Layer":
        new_layer = Layer(name=f"{self.name} Copy", visible=self.visible, locked=self.locked, opacity=self.opacity)
        new_layer.pixels = dict(self.pixels)
        new_layer.effects = [effect_from_dict(eff.to_dict()) for eff in self.effects if eff]
        return new_layer

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "visible": self.visible,
            "locked": self.locked,
            "opacity": round(self.opacity, 3),
            "pixels": self.pixels,
            "effects": [eff.to_dict() for eff in self.effects],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Layer":
        layer = cls(
            name=data.get("name", "Layer"),
            visible=data.get("visible", True),
            locked=data.get("locked", False),
            opacity=float(data.get("opacity", 1.0)),
        )
        pixels_raw = data.get("pixels", {})
        if isinstance(pixels_raw, dict):
            layer.pixels = {str(k): str(v) for k, v in pixels_raw.items()}

        raw_effects = data.get("effects", [])
        if isinstance(raw_effects, list):
            for eff_data in raw_effects:
                eff_obj = effect_from_dict(eff_data)
                if eff_obj:
                    layer.effects.append(eff_obj)

        return layer


class PixelDocument:
    """Represents a multi-layer pixel art document."""

    def __init__(self, width: int = 32, height: int = 32, filepath: Optional[str] = None):
        self.width = max(1, width)
        self.height = max(1, height)
        self.filepath = filepath
        self.layers: List[Layer] = []
        self.active_layer_index: int = 0

        # Initialize with one default layer
        self.add_layer("Background")

    @property
    def active_layer(self) -> Optional[Layer]:
        if 0 <= self.active_layer_index < len(self.layers):
            return self.layers[self.active_layer_index]
        return None

    def add_layer(self, name: Optional[str] = None) -> Layer:
        if name is None:
            name = f"Layer {len(self.layers) + 1}"
        layer = Layer(name=name)
        insert_idx = self.active_layer_index + 1 if self.layers else 0
        self.layers.insert(insert_idx, layer)
        self.active_layer_index = insert_idx
        return layer

    def duplicate_layer(self, index: int) -> Optional[Layer]:
        if 0 <= index < len(self.layers):
            cloned = self.layers[index].clone()
            self.layers.insert(index + 1, cloned)
            self.active_layer_index = index + 1
            return cloned
        return None

    def delete_layer(self, index: int) -> bool:
        if len(self.layers) <= 1:
            return False  # Keep at least one layer
        if 0 <= index < len(self.layers):
            del self.layers[index]
            if self.active_layer_index >= len(self.layers):
                self.active_layer_index = len(self.layers) - 1
            return True
        return False

    def move_layer_up(self, index: int) -> bool:
        if index < len(self.layers) - 1:
            self.layers[index], self.layers[index + 1] = self.layers[index + 1], self.layers[index]
            if self.active_layer_index == index:
                self.active_layer_index = index + 1
            elif self.active_layer_index == index + 1:
                self.active_layer_index = index
            return True
        return False

    def move_layer_down(self, index: int) -> bool:
        if index > 0:
            self.layers[index], self.layers[index - 1] = self.layers[index - 1], self.layers[index]
            if self.active_layer_index == index:
                self.active_layer_index = index - 1
            elif self.active_layer_index == index - 1:
                self.active_layer_index = index
            return True
        return False

    def is_valid_coord(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def to_dict(self) -> dict:
        """Serializes document data into dictionary format suitable for pycaml encoding."""
        return {
            "format": "coopixel",
            "version": "1.0",
            "width": self.width,
            "height": self.height,
            "active_layer": self.active_layer_index,
            "layers": [layer.to_dict() for layer in self.layers],
        }

    @classmethod
    def from_dict(cls, data: dict, filepath: Optional[str] = None) -> "PixelDocument":
        width = int(data.get("width", 32))
        height = int(data.get("height", 32))
        doc = cls(width=width, height=height, filepath=filepath)
        doc.layers.clear()

        raw_layers = data.get("layers", [])
        if raw_layers:
            for l_data in raw_layers:
                doc.layers.append(Layer.from_dict(l_data))
        else:
            doc.add_layer("Background")

        active_idx = int(data.get("active_layer", 0))
        doc.active_layer_index = max(0, min(active_idx, len(doc.layers) - 1))
        return doc

    def save_to_pix(self, filepath: str, passphrase: str = None) -> None:
        """Encodes document state to a pycaml .pix file."""
        doc_dict = self.to_dict()
        cmap = CAMLMap(doc_dict)
        if passphrase:
            cmap.save_pix(filepath, passphrase=passphrase)
        else:
            cmap.save_pix(filepath)
        self.filepath = filepath

    @classmethod
    def load_from_pix(cls, filepath: str, passphrase: str = None) -> "PixelDocument":
        """Loads and decodes document state from a pycaml .pix file."""
        if passphrase:
            cmap = CAMLMap.load_pix(filepath, passphrase=passphrase)
        else:
            cmap = CAMLMap.load_pix(filepath)
        return cls.from_dict(cmap.data, filepath=filepath)

    def render_composite_qimage(self) -> QImage:
        """Renders all visible layers into a single QImage with transparency, opacity, and layer effects."""
        image = QImage(self.width, self.height, QImage.Format_ARGB32_Premultiplied)
        image.fill(QColor(0, 0, 0, 0))  # Clear transparent

        painter = QPainter(image)
        for layer in self.layers:
            if not layer.visible or layer.opacity <= 0:
                continue

            painter.setOpacity(layer.opacity)

            # Compute layer effects
            below_map: Dict[str, str] = {}
            above_map: Dict[str, str] = {}
            for eff in layer.effects:
                if eff and eff.enabled:
                    b_dict, a_dict = eff.render_effect(layer.pixels, self.width, self.height)
                    below_map.update(b_dict)
                    above_map.update(a_dict)

            # 1. Render below-effect pixels (e.g. outside stroke)
            for coord, hex_str in below_map.items():
                parts = coord.split(",")
                if len(parts) == 2:
                    x, y = int(parts[0]), int(parts[1])
                    if self.is_valid_coord(x, y):
                        painter.setPen(hex_to_qcolor(hex_str))
                        painter.drawPoint(x, y)

            # 2. Render base layer pixels
            for coord, hex_str in layer.pixels.items():
                parts = coord.split(",")
                if len(parts) == 2:
                    x, y = int(parts[0]), int(parts[1])
                    if self.is_valid_coord(x, y):
                        painter.setPen(hex_to_qcolor(hex_str))
                        painter.drawPoint(x, y)

            # 3. Render above-effect pixels (e.g. inside stroke)
            for coord, hex_str in above_map.items():
                parts = coord.split(",")
                if len(parts) == 2:
                    x, y = int(parts[0]), int(parts[1])
                    if self.is_valid_coord(x, y):
                        painter.setPen(hex_to_qcolor(hex_str))
                        painter.drawPoint(x, y)

        painter.end()
        return image

    def export_png(self, filepath: str) -> bool:
        """Exports composite image to PNG format."""
        image = self.render_composite_qimage()
        return image.save(filepath, "PNG")
