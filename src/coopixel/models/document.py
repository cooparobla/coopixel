"""
Document and Layer data models for Coopixel.
Uses sparse dictionary storage for pixels: only filled/colored pixels are stored ("x,y": "#RRGGBBAA").
Supports extensible layer effects (e.g. Stroke).
"""

import os
from typing import Dict, List, Optional, Tuple
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPen
from pycaml import CAMLMap
from coopixel.models.effects import LayerEffect, effect_from_dict
from coopixel.models.path import AnchorPoint, VectorPath



_COLOR_CACHE: Dict[str, QColor] = {}


def hex_to_qcolor(hex_str: str) -> QColor:
    col = _COLOR_CACHE.get(hex_str)
    if col is None:
        s = hex_str.lstrip("#")
        if len(s) == 8:
            r = int(s[0:2], 16)
            g = int(s[2:4], 16)
            b = int(s[4:6], 16)
            a = int(s[6:8], 16)
            col = QColor(r, g, b, a)
        elif len(s) == 6:
            r = int(s[0:2], 16)
            g = int(s[2:4], 16)
            b = int(s[4:6], 16)
            col = QColor(r, g, b, 255)
        else:
            col = QColor(hex_str)
        _COLOR_CACHE[hex_str] = col
    return col


def qcolor_to_hex(qcol: QColor) -> str:
    return f"#{qcol.red():02X}{qcol.green():02X}{qcol.blue():02X}{qcol.alpha():02X}"


class Layer:
    """Represents a single drawing layer with sparse pixel data and effects."""

    def __init__(
        self,
        name: str = "Layer",
        visible: bool = True,
        locked: bool = False,
        opacity: float = 1.0,
        tag: str = "",
    ):
        self.name = name
        self.visible = visible
        self.locked = locked
        self.opacity = max(0.0, min(1.0, float(opacity)))
        self.tag = tag.strip()
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

    def crop_to_bounds(self, width: int, height: int) -> int:
        """Removes any pixels in this layer lying outside (0 <= x < width) and (0 <= y < height). Returns count removed."""
        to_delete = []
        for key in list(self.pixels.keys()):
            parts = key.split(",")
            if len(parts) == 2:
                x, y = int(parts[0]), int(parts[1])
                if not (0 <= x < width and 0 <= y < height):
                    to_delete.append(key)
        for k in to_delete:
            del self.pixels[k]
        return len(to_delete)

    def get_content_bbox(self, clip_to_doc: bool = False, doc_width: int = 0, doc_height: int = 0) -> Optional[Tuple[int, int, int, int]]:
        """Returns (x, y, width, height) bounding box of non-empty pixels in this layer, or None if empty."""
        if not self.pixels:
            return None
        min_x, min_y = float("inf"), float("inf")
        max_x, max_y = float("-inf"), float("-inf")
        found = False

        for coord_str in self.pixels.keys():
            parts = coord_str.split(",")
            if len(parts) == 2:
                px, py = int(parts[0]), int(parts[1])
                if clip_to_doc and doc_width > 0 and doc_height > 0 and not (0 <= px < doc_width and 0 <= py < doc_height):
                    continue
                found = True
                if px < min_x:
                    min_x = px
                if px > max_x:
                    max_x = px
                if py < min_y:
                    min_y = py
                if py > max_y:
                    max_y = py

        if not found:
            return None
        return (int(min_x), int(min_y), int(max_x - min_x + 1), int(max_y - min_y + 1))

    def clone(self, name: Optional[str] = None) -> "Layer":
        layer_name = name if name is not None else f"{self.name} Copy"
        new_layer = Layer(
            name=layer_name, visible=self.visible, locked=self.locked, opacity=self.opacity, tag=self.tag
        )
        new_layer.pixels = dict(self.pixels)
        new_layer.effects = [effect_from_dict(eff.to_dict()) for eff in self.effects if eff]
        return new_layer

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "visible": self.visible,
            "locked": self.locked,
            "opacity": round(self.opacity, 3),
            "tag": self.tag,
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
            tag=data.get("tag", ""),
        )
        pixels_raw = data.get("pixels", {})
        if isinstance(pixels_raw, dict):
            layer.pixels = {str(k): str(v) for k, v in pixels_raw.items()}

        raw_effects = data.get("effects", [])
        if isinstance(raw_effects, list):
            for eff_data in raw_effects:
                eff = effect_from_dict(eff_data)
                if eff:
                    layer.effects.append(eff)

        return layer


class AnimationFrame:
    """Represents a single animation frame containing layers."""

    def __init__(self, name: str = "Frame 1", duration_ms: int = 100):
        self.name = name
        self.duration_ms = duration_ms
        self.layers: List[Layer] = []
        self.active_layer_index: int = 0
        # Initialize with default layer
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

    def clone(self) -> "AnimationFrame":
        new_frame = AnimationFrame(name=f"{self.name} Copy", duration_ms=self.duration_ms)
        new_frame.layers = [l.clone() for l in self.layers]
        new_frame.active_layer_index = min(self.active_layer_index, max(0, len(new_frame.layers) - 1))
        return new_frame

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "active_layer": self.active_layer_index,
            "layers": [layer.to_dict() for layer in self.layers],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AnimationFrame":
        frame = cls(
            name=data.get("name", "Frame"),
            duration_ms=int(data.get("duration_ms", 100))
        )
        frame.layers.clear()
        raw_layers = data.get("layers", [])
        if raw_layers:
            for l_data in raw_layers:
                frame.layers.append(Layer.from_dict(l_data))
        else:
            frame.add_layer("Background")
        frame.active_layer_index = max(0, min(int(data.get("active_layer", 0)), len(frame.layers) - 1))
        return frame


class Animation:
    """Represents a named distinct animation sequence containing frames."""

    def __init__(self, name: str = "new-animation", fps: int = 10):
        self.name = name
        self.fps = fps
        self.frames: List[AnimationFrame] = []
        self.active_frame_index: int = 0
        # Initialize with default frame
        self.frames.append(AnimationFrame("Frame 1"))

    @property
    def active_frame(self) -> AnimationFrame:
        if 0 <= self.active_frame_index < len(self.frames):
            return self.frames[self.active_frame_index]
        return self.frames[0]

    def add_frame(self, name: Optional[str] = None) -> AnimationFrame:
        if name is None:
            name = f"Frame {len(self.frames) + 1}"
        frame = AnimationFrame(name=name)
        insert_idx = self.active_frame_index + 1
        self.frames.insert(insert_idx, frame)
        self.active_frame_index = insert_idx
        return frame

    def duplicate_frame(self, index: int) -> Optional[AnimationFrame]:
        if 0 <= index < len(self.frames):
            cloned = self.frames[index].clone()
            self.frames.insert(index + 1, cloned)
            self.active_frame_index = index + 1
            return cloned
        return None

    def delete_frame(self, index: int) -> bool:
        if len(self.frames) <= 1:
            return False  # Minimum 1 frame rule
        if 0 <= index < len(self.frames):
            del self.frames[index]
            if self.active_frame_index >= len(self.frames):
                self.active_frame_index = len(self.frames) - 1
            return True
        return False

    def select_frame(self, index: int) -> bool:
        if 0 <= index < len(self.frames):
            self.active_frame_index = index
            return True
        return False

    def move_frame_left(self, index: int) -> bool:
        if 0 < index < len(self.frames):
            self.frames[index], self.frames[index - 1] = self.frames[index - 1], self.frames[index]
            if self.active_frame_index == index:
                self.active_frame_index = index - 1
            elif self.active_frame_index == index - 1:
                self.active_frame_index = index
            return True
        return False

    def move_frame_right(self, index: int) -> bool:
        if 0 <= index < len(self.frames) - 1:
            self.frames[index], self.frames[index + 1] = self.frames[index + 1], self.frames[index]
            if self.active_frame_index == index:
                self.active_frame_index = index + 1
            elif self.active_frame_index == index + 1:
                self.active_frame_index = index
            return True
        return False

    def clone(self) -> "Animation":
        anim = Animation(name=f"{self.name} Copy", fps=self.fps)
        anim.frames = [f.clone() for f in self.frames]
        anim.active_frame_index = min(self.active_frame_index, max(0, len(anim.frames) - 1))
        return anim

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "fps": self.fps,
            "active_frame": self.active_frame_index,
            "frames": [f.to_dict() for f in self.frames],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Animation":
        anim = cls(
            name=data.get("name", "new-animation"),
            fps=int(data.get("fps", 10))
        )
        anim.frames.clear()
        raw_frames = data.get("frames", [])
        if raw_frames:
            for f_data in raw_frames:
                anim.frames.append(AnimationFrame.from_dict(f_data))
        else:
            anim.frames.append(AnimationFrame("Frame 1"))
        anim.active_frame_index = max(0, min(int(data.get("active_frame", 0)), len(anim.frames) - 1))
        return anim


class PixelDocument:
    """Represents a multi-layer, multi-frame, multi-animation pixel art document."""

    def __init__(self, width: int = 32, height: int = 32, filepath: Optional[str] = None):
        self.width = max(1, width)
        self.height = max(1, height)
        self.filepath = filepath
        self.animations: List[Animation] = []
        self.active_animation_index: int = 0
        self.paths: List[VectorPath] = []
        self.active_path_index: Optional[int] = None
        self.primary_color: str = "#F97316FF"


        # Every new file MUST have at least one animation named "new-animation"
        self.animations.append(Animation("new-animation"))

    @property
    def active_path(self) -> Optional[VectorPath]:
        if self.active_path_index is not None and 0 <= self.active_path_index < len(self.paths):
            return self.paths[self.active_path_index]
        return None

    def add_path(
        self,
        name: Optional[str] = None,
        layer_id: str = "",
        frame_index: Optional[int] = None,
        stroke_color: Optional[str] = None,
        fill_color: Optional[str] = None,
    ) -> VectorPath:
        if name is None:
            name = f"Path {len(self.paths) + 1}"
        if not layer_id and self.active_layer:
            layer_id = self.active_layer.name
        if frame_index is None:
            frame_index = getattr(self, "active_frame_index", 0)

        primary = getattr(self, "primary_color", "#F97316FF")
        if stroke_color is None:
            stroke_color = primary
        if fill_color is None:
            fill_color = primary

        vp = VectorPath(
            name=name,
            layer_id=layer_id,
            frame_index=frame_index,
            stroke_color=stroke_color,
            fill_color=fill_color,
        )
        self.paths.append(vp)
        self.active_path_index = len(self.paths) - 1
        return vp



    def remove_path(self, index: int) -> bool:
        if 0 <= index < len(self.paths):
            del self.paths[index]
            if not self.paths:
                self.active_path_index = None
            elif self.active_path_index is not None and self.active_path_index >= len(self.paths):
                self.active_path_index = len(self.paths) - 1
            return True
        return False

    def stroke_path(self, path: VectorPath, color: str, size: int = 1) -> int:
        """Rasterizes the path outline onto the active layer using QPainter."""
        active = self.active_layer
        if not active or not path.anchors:
            return 0

        qpath = path.to_qpainterpath()
        img = QImage(self.width, self.height, QImage.Format_ARGB32)
        img.fill(QColor(0, 0, 0, 0))

        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing, False)
        pen = QPen(hex_to_qcolor(color), max(1, size))
        painter.setPen(pen)
        painter.drawPath(qpath)
        painter.end()

        count = 0
        for y in range(self.height):
            for x in range(self.width):
                col = img.pixelColor(x, y)
                if col.alpha() > 0:
                    active.set_pixel(x, y, qcolor_to_hex(col))
                    count += 1
        return count

    def fill_path(self, path: VectorPath, color: str) -> int:
        """Rasterizes the filled path interior onto the active layer using QPainter."""
        active = self.active_layer
        if not active or not path.anchors:
            return 0

        qpath = path.to_qpainterpath()
        img = QImage(self.width, self.height, QImage.Format_ARGB32)
        img.fill(QColor(0, 0, 0, 0))

        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing, False)
        qcol = hex_to_qcolor(color)
        painter.setBrush(QBrush(qcol))
        painter.setPen(QPen(qcol, 1))
        painter.drawPath(qpath)
        painter.end()

        count = 0
        for y in range(self.height):
            for x in range(self.width):
                col = img.pixelColor(x, y)
                if col.alpha() > 0:
                    active.set_pixel(x, y, qcolor_to_hex(col))
                    count += 1
        return count


    @property
    def active_animation(self) -> Animation:
        if 0 <= self.active_animation_index < len(self.animations):
            return self.animations[self.active_animation_index]
        return self.animations[0]

    # Delegates animation properties to active animation
    @property
    def frames(self) -> List[AnimationFrame]:
        return self.active_animation.frames

    @frames.setter
    def frames(self, new_frames: List[AnimationFrame]) -> None:
        self.active_animation.frames = new_frames

    @property
    def active_frame_index(self) -> int:
        return self.active_animation.active_frame_index

    @active_frame_index.setter
    def active_frame_index(self, idx: int) -> None:
        self.active_animation.active_frame_index = idx

    @property
    def fps(self) -> int:
        return self.active_animation.fps

    @fps.setter
    def fps(self, val: int) -> None:
        self.active_animation.fps = val

    @property
    def active_frame(self) -> AnimationFrame:
        return self.active_animation.active_frame

    # Delegates layer properties to active frame
    @property
    def layers(self) -> List[Layer]:
        return self.active_frame.layers

    @layers.setter
    def layers(self, new_layers: List[Layer]) -> None:
        self.active_frame.layers = new_layers

    @property
    def active_layer_index(self) -> int:
        return self.active_frame.active_layer_index

    @active_layer_index.setter
    def active_layer_index(self, idx: int) -> None:
        self.active_frame.active_layer_index = idx

    @property
    def active_layer(self) -> Optional[Layer]:
        return self.active_frame.active_layer

    # Animation Management API
    def add_animation(self, name: Optional[str] = None) -> Animation:
        if name is None:
            name = f"new-animation-{len(self.animations) + 1}"
        anim = Animation(name=name)
        self.animations.append(anim)
        self.active_animation_index = len(self.animations) - 1
        return anim

    def rename_animation(self, index: int, new_name: str) -> bool:
        if 0 <= index < len(self.animations) and new_name.strip():
            self.animations[index].name = new_name.strip()
            return True
        return False

    def delete_animation(self, index: int) -> bool:
        if len(self.animations) <= 1:
            return False  # Minimum 1 animation rule
        if 0 <= index < len(self.animations):
            del self.animations[index]
            if self.active_animation_index >= len(self.animations):
                self.active_animation_index = len(self.animations) - 1
            return True
        return False

    def select_animation(self, index: int) -> bool:
        if 0 <= index < len(self.animations):
            self.active_animation_index = index
            return True
        return False

    # Frame delegates
    def add_frame(self, name: Optional[str] = None) -> AnimationFrame:
        return self.active_animation.add_frame(name)

    def duplicate_frame(self, index: int) -> Optional[AnimationFrame]:
        return self.active_animation.duplicate_frame(index)

    def delete_frame(self, index: int) -> bool:
        return self.active_animation.delete_frame(index)

    def select_frame(self, index: int) -> bool:
        return self.active_animation.select_frame(index)

    def move_frame_left(self, index: int) -> bool:
        return self.active_animation.move_frame_left(index)

    def move_frame_right(self, index: int) -> bool:
        return self.active_animation.move_frame_right(index)

    # Layer delegates
    def add_layer(self, name: Optional[str] = None) -> Layer:
        return self.active_frame.add_layer(name)

    def duplicate_layer(self, index: int) -> Optional[Layer]:
        return self.active_frame.duplicate_layer(index)

    def delete_layer(self, index: int) -> bool:
        return self.active_frame.delete_layer(index)

    def move_layer_up(self, index: int) -> bool:
        return self.active_frame.move_layer_up(index)

    def move_layer_down(self, index: int) -> bool:
        return self.active_frame.move_layer_down(index)

    def crop_active_layer_to_canvas(self) -> int:
        """Crops current active layer to canvas dimensions (0, 0, width, height)."""
        active = self.active_layer
        if active:
            return active.crop_to_bounds(self.width, self.height)
        return 0

    def is_valid_coord(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def resize_canvas(
        self,
        new_width: int,
        new_height: int,
        anchor: str = "top-left",
        offset_x: Optional[int] = None,
        offset_y: Optional[int] = None,
    ) -> None:
        """Resizes canvas to new_width x new_height using an anchor position or custom offsets.

        Anchor positions:
          'top-left', 'top-center', 'top-right',
          'middle-left', 'center', 'middle-right',
          'bottom-left', 'bottom-center', 'bottom-right'
        """
        new_width = max(1, int(new_width))
        new_height = max(1, int(new_height))

        if offset_x is None or offset_y is None:
            anchor = anchor.lower().strip()
            if anchor == "top-center":
                off_x = (new_width - self.width) // 2
                off_y = 0
            elif anchor == "top-right":
                off_x = new_width - self.width
                off_y = 0
            elif anchor == "middle-left":
                off_x = 0
                off_y = (new_height - self.height) // 2
            elif anchor == "center":
                off_x = (new_width - self.width) // 2
                off_y = (new_height - self.height) // 2
            elif anchor == "middle-right":
                off_x = new_width - self.width
                off_y = (new_height - self.height) // 2
            elif anchor == "bottom-left":
                off_x = 0
                off_y = new_height - self.height
            elif anchor == "bottom-center":
                off_x = (new_width - self.width) // 2
                off_y = new_height - self.height
            elif anchor == "bottom-right":
                off_x = new_width - self.width
                off_y = new_height - self.height
            else:  # top-left
                off_x = 0
                off_y = 0
        else:
            off_x = int(offset_x)
            off_y = int(offset_y)

        for anim in self.animations:
            for frame in anim.frames:
                for layer in frame.layers:
                    new_pixels: Dict[str, str] = {}
                    for coord_str, hex_str in layer.pixels.items():
                        parts = coord_str.split(",")
                        if len(parts) == 2:
                            px, py = int(parts[0]), int(parts[1])
                            nx, ny = px + off_x, py + off_y
                            if 0 <= nx < new_width and 0 <= ny < new_height:
                                new_pixels[f"{nx},{ny}"] = hex_str
                    layer.pixels = new_pixels

        self.width = new_width
        self.height = new_height

    def crop_canvas(self, x: int, y: int, width: int, height: int) -> None:
        """Crops canvas to bounding box (x, y, width, height)."""
        self.resize_canvas(new_width=width, new_height=height, offset_x=-x, offset_y=-y)

    def get_content_bbox(self, clip_to_doc: bool = False) -> Optional[Tuple[int, int, int, int]]:
        """Returns (x, y, width, height) bounding box of non-empty pixels across all layers/frames, or None if empty."""
        min_x, min_y = float("inf"), float("inf")
        max_x, max_y = float("-inf"), float("-inf")
        found = False

        for anim in self.animations:
            for frame in anim.frames:
                for layer in frame.layers:
                    for coord_str in layer.pixels.keys():
                        parts = coord_str.split(",")
                        if len(parts) == 2:
                            px, py = int(parts[0]), int(parts[1])
                            if clip_to_doc and not (0 <= px < self.width and 0 <= py < self.height):
                                continue
                            found = True
                            if px < min_x:
                                min_x = px
                            if px > max_x:
                                max_x = px
                            if py < min_y:
                                min_y = py
                            if py > max_y:
                                max_y = py

        if not found:
            return None
        return (int(min_x), int(min_y), int(max_x - min_x + 1), int(max_y - min_y + 1))

    def get_selection_bbox(self, selection_set) -> Optional[Tuple[int, int, int, int]]:
        """Returns (x, y, width, height) bounding box of selection coordinates, or None if empty."""
        if not selection_set:
            return None
        min_x = min(x for x, y in selection_set)
        max_x = max(x for x, y in selection_set)
        min_y = min(y for x, y in selection_set)
        max_y = max(y for x, y in selection_set)
        return (min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)

    def to_dict(self) -> dict:
        """Serializes document data into dictionary format suitable for pycaml encoding."""
        return {
            "format": "coopixel",
            "version": "1.0",
            "width": self.width,
            "height": self.height,
            "active_animation": self.active_animation_index,
            "animations": [anim.to_dict() for anim in self.animations],
            "paths": [p.to_dict() for p in self.paths],
            "active_path": self.active_path_index,
        }

    @classmethod
    def from_dict(cls, data: dict, filepath: Optional[str] = None) -> "PixelDocument":
        width = int(data.get("width", 32))
        height = int(data.get("height", 32))
        doc = cls(width=width, height=height, filepath=filepath)
        doc.animations.clear()

        raw_anims = data.get("animations", [])
        if raw_anims:
            for a_data in raw_anims:
                doc.animations.append(Animation.from_dict(a_data))
        else:
            # Single-animation legacy format
            anim = Animation("new-animation")
            anim.fps = int(data.get("fps", 10))
            anim.onion_skin = bool(data.get("onion_skin", False))
            anim.frames.clear()

            raw_frames = data.get("frames", [])
            if raw_frames:
                for f_data in raw_frames:
                    anim.frames.append(AnimationFrame.from_dict(f_data))
            else:
                frame = AnimationFrame("Frame 1")
                frame.layers.clear()
                raw_layers = data.get("layers", [])
                if raw_layers:
                    for l_data in raw_layers:
                        frame.layers.append(Layer.from_dict(l_data))
                else:
                    frame.add_layer("Background")
                frame.active_layer_index = max(0, min(int(data.get("active_layer", 0)), len(frame.layers) - 1))
                anim.frames.append(frame)

            if not anim.frames:
                anim.frames.append(AnimationFrame("Frame 1"))
            anim.active_frame_index = max(0, min(int(data.get("active_frame", 0)), len(anim.frames) - 1))
            doc.animations.append(anim)

        if not doc.animations:
            doc.animations.append(Animation("new-animation"))

        active_anim_idx = int(data.get("active_animation", 0))
        doc.active_animation_index = max(0, min(active_anim_idx, len(doc.animations) - 1))

        # Restore vector paths
        raw_paths = data.get("paths", [])
        doc.paths = [VectorPath.from_dict(p) for p in raw_paths]
        active_p = data.get("active_path", None)
        if active_p is not None and isinstance(active_p, int) and 0 <= active_p < len(doc.paths):
            doc.active_path_index = active_p
        elif doc.paths:
            doc.active_path_index = 0
        else:
            doc.active_path_index = None

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

    def render_frame_qimage(self, frame_index: int = 0) -> QImage:
        """Renders specified frame's layers into a single QImage with transparency and layer effects."""
        if not (0 <= frame_index < len(self.frames)):
            frame_index = self.active_frame_index
        target_frame = self.frames[frame_index]

        w, h = self.width, self.height
        image = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        image.fill(QColor(0, 0, 0, 0))  # Clear transparent

        painter = QPainter(image)
        for layer in target_frame.layers:
            if not layer.visible or layer.opacity <= 0:
                continue

            base_pixels = dict(layer.pixels)

            # Composite dynamic vector path pixels bound to this layer and frame
            for path in self.paths:
                if not path.visible or not path.anchors:
                    continue
                if path.layer_id and path.layer_id != layer.name:
                    continue
                if path.frame_index is not None and path.frame_index != frame_index:
                    continue
                if path.stroked or path.filled:
                    path_px = path.get_pixel_map(w, h)
                    if path_px:
                        base_pixels.update(path_px)


            if not base_pixels:
                continue

            # Compute layer effects if present
            below_map: Dict[str, str] = {}
            above_map: Dict[str, str] = {}
            for eff in layer.effects:
                if eff and eff.enabled:
                    if hasattr(eff, "process_pixels"):
                        base_pixels = eff.process_pixels(base_pixels)
                    b_dict, a_dict = eff.render_effect(base_pixels, w, h)
                    below_map.update(b_dict)
                    above_map.update(a_dict)


            # Build layer buffer for fast rendering — write directly into a bytearray
            # instead of calling setPixelColor() per pixel (O(n) Qt→Python overhead).
            # Format_ARGB32 byte order on LE: B, G, R, A.
            stride = w * 4
            buf = bytearray(stride * h)  # all-transparent initially

            def _write_pixels(pixel_map: Dict[str, str]) -> None:
                for coord, hex_str in pixel_map.items():
                    parts = coord.split(",")
                    if len(parts) == 2:
                        x, y = int(parts[0]), int(parts[1])
                        if 0 <= x < w and 0 <= y < h:
                            col = hex_to_qcolor(hex_str)
                            idx = y * stride + x * 4
                            buf[idx]     = col.blue()
                            buf[idx + 1] = col.green()
                            buf[idx + 2] = col.red()
                            buf[idx + 3] = col.alpha()

            # 1. Below-effect pixels (e.g. outside stroke)
            _write_pixels(below_map)
            # 2. Base layer pixels (with color modifications applied)
            _write_pixels(base_pixels)
            # 3. Above-effect pixels (e.g. inside stroke)
            _write_pixels(above_map)


            layer_img = QImage(bytes(buf), w, h, stride, QImage.Format_ARGB32)

            if layer.opacity < 1.0:
                painter.setOpacity(layer.opacity)
            else:
                painter.setOpacity(1.0)
            painter.drawImage(0, 0, layer_img)

        painter.end()
        return image

    def render_composite_qimage(self) -> QImage:
        """Renders active frame into composite QImage."""
        return self.render_frame_qimage(self.active_frame_index)

    def export_png(self, filepath: str) -> bool:
        """Exports active frame composite image to PNG format."""
        image = self.render_composite_qimage()
        return image.save(filepath, "PNG")

    def import_image_as_layer(
        self,
        filepath: str,
        name: Optional[str] = None,
        resize_canvas: bool = False,
        scale_to_canvas: bool = False,
    ) -> Optional[Layer]:
        """Imports an image file (PNG/JPG/BMP) as a new layer in the active frame."""
        image = QImage(filepath)
        if image.isNull():
            return None

        if resize_canvas:
            self.resize_canvas(image.width(), image.height(), anchor="top-left")
        elif scale_to_canvas and (image.width() != self.width or image.height() != self.height):
            image = image.scaled(self.width, self.height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        if name is None:
            basename = os.path.basename(filepath)
            name = os.path.splitext(basename)[0]

        layer = self.add_layer(name=name)
        w = image.width()
        h = image.height()

        # Convert to ARGB32 for predictable byte layout (B, G, R, A on LE),
        # then read the raw buffer directly — avoids O(w*h) pixelColor() calls.
        image = image.convertToFormat(QImage.Format_ARGB32)
        src_bits = image.bits()  # memoryview into the image buffer
        src_stride = image.bytesPerLine()
        new_pixels: Dict[str, str] = {}
        for y in range(h):
            row_base = y * src_stride
            for x in range(w):
                idx = row_base + x * 4
                b = src_bits[idx]
                g = src_bits[idx + 1]
                r = src_bits[idx + 2]
                a = src_bits[idx + 3]
                if a > 0:
                    new_pixels[f"{x},{y}"] = f"#{r:02X}{g:02X}{b:02X}{a:02X}"
        layer.pixels = new_pixels

        return layer

    # ------------------------------------------------------------------
    # Tag Management Across Frames & Animations
    # ------------------------------------------------------------------

    def get_all_tags(self) -> List[str]:
        """Returns a sorted list of all unique non-empty tags across all frames and animations."""
        tags = set()
        for anim in self.animations:
            for frame in anim.frames:
                for layer in frame.layers:
                    if layer.tag and layer.tag.strip():
                        tags.add(layer.tag.strip())
        return sorted(list(tags))

    def get_layers_by_tag(self, tag: str) -> List[Layer]:
        """Returns all layers with the given tag across all frames and animations."""
        target = tag.strip().lower()
        matched = []
        for anim in self.animations:
            for frame in anim.frames:
                for layer in frame.layers:
                    if layer.tag.strip().lower() == target:
                        matched.append(layer)
        return matched

    def is_tag_visible(self, tag: str) -> bool:
        """Returns True if any layer with the specified tag is visible."""
        layers = self.get_layers_by_tag(tag)
        if not layers:
            return False
        return any(l.visible for l in layers)

    def set_tag_visibility(self, tag: str, visible: bool) -> None:
        """Sets visibility for all layers across all frames and animations with the specified tag."""
        target = tag.strip().lower()
        for anim in self.animations:
            for frame in anim.frames:
                for layer in frame.layers:
                    if layer.tag.strip().lower() == target:
                        layer.visible = visible


