"""
Spritesheet configuration model, YAML load/save (.pixpref files), and slicing utilities.
Supports global frame dimensions, per-animation layer naming, layer tags, non-contiguous frame cell sequences (Ctrl+Click), frame pivot points, and default 'Background' cleanup.
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from PySide6.QtGui import QColor, QImage
from coopixel.models.document import Animation, AnimationFrame, Layer, PixelDocument

DEFAULT_CONFIG_DIR = os.path.expanduser("~/.coopixel")


@dataclass
class SpritesheetAnimationConfig:
    """Configuration for an animation sequence on a spritesheet."""

    name: str = "new-animation"
    layer_name: str = "Layer 1"
    tag: str = "default"
    start_x: int = 0
    start_y: int = 0
    num_frames: int = 1
    fps: int = 10
    pivot_x: Optional[int] = None
    pivot_y: Optional[int] = None
    frame_cells: Optional[List[Tuple[int, int]]] = None

    def get_pivot(self, global_fw: int, global_fh: int) -> Tuple[int, int]:
        """Returns the frame pivot coordinates (px, py), defaulting to global frame center."""
        px = self.pivot_x if self.pivot_x is not None else global_fw // 2
        py = self.pivot_y if self.pivot_y is not None else global_fh // 2
        return (px, py)

    def get_frame_positions(self, global_fw: int, global_fh: int, img_w: int = 8192) -> List[Tuple[int, int]]:
        """Returns top-left (x, y) pixel coordinates for each frame in sequence."""
        if self.frame_cells and len(self.frame_cells) > 0:
            return list(self.frame_cells)
        positions = []
        fw = max(1, global_fw)
        fh = max(1, global_fh)
        cols_count = max(1, img_w // fw)
        start_col = self.start_x // fw
        start_row = self.start_y // fh
        for i in range(max(1, self.num_frames)):
            c = (start_col + i) % cols_count
            r = start_row + (start_col + i) // cols_count
            positions.append((c * fw, r * fh))
        return positions

    def to_dict(self, global_fw: int = 32, global_fh: int = 32) -> dict:
        px, py = self.get_pivot(global_fw, global_fh)
        d = {
            "name": self.name.strip() or "new-animation",
            "layer_name": self.layer_name.strip() or "Layer 1",
            "tag": self.tag.strip() or "default",
            "start_x": int(self.start_x),
            "start_y": int(self.start_y),
            "num_frames": max(1, int(self.num_frames)),
            "fps": max(1, int(self.fps)),
            "pivot_x": int(px),
            "pivot_y": int(py),
        }
        if self.frame_cells:
            d["frame_cells"] = [{"x": int(cx), "y": int(cy)} for cx, cy in self.frame_cells]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "SpritesheetAnimationConfig":
        start_x = data.get("start_x", data.get("x", 0))
        start_y = data.get("start_y", data.get("y", 0))
        name_val = str(data.get("name", "new-animation")).strip() or "new-animation"
        layer_val = str(data.get("layer_name", "Layer 1")).strip() or "Layer 1"
        tag_val = str(data.get("tag", "default")).strip() or "default"
        px = data.get("pivot_x", None)
        py = data.get("pivot_y", None)
        raw_cells = data.get("frame_cells", None)
        frame_cells = None
        if isinstance(raw_cells, list):
            frame_cells = []
            for item in raw_cells:
                if isinstance(item, dict):
                    frame_cells.append((int(item.get("x", 0)), int(item.get("y", 0))))
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    frame_cells.append((int(item[0]), int(item[1])))
        return cls(
            name=name_val,
            layer_name=layer_val,
            tag=tag_val,
            start_x=int(start_x),
            start_y=int(start_y),
            num_frames=max(1, int(data.get("num_frames", 1))),
            fps=max(1, int(data.get("fps", 10))),
            pivot_x=int(px) if px is not None else None,
            pivot_y=int(py) if py is not None else None,
            frame_cells=frame_cells,
        )


def save_spritesheet_configs(
    filepath: str,
    configs: List[SpritesheetAnimationConfig],
    global_frame_width: int = 32,
    global_frame_height: int = 32,
) -> None:
    """Saves global frame size and animation configs (including layer tags and pivot points) to a YAML .pixpref file."""
    dir_path = os.path.dirname(filepath)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    data = {
        "version": 1,
        "global_frame_width": max(1, int(global_frame_width)),
        "global_frame_height": max(1, int(global_frame_height)),
        "animations": [c.to_dict(global_frame_width, global_frame_height) for c in configs],
    }

    try:
        import yaml
        yaml_str = yaml.dump(data, sort_keys=False, default_flow_style=False)
    except ImportError:
        # Fallback YAML dumper
        lines = [
            "version: 1",
            f"global_frame_width: {global_frame_width}",
            f"global_frame_height: {global_frame_height}",
            "animations:",
        ]
        for c in configs:
            px, py = c.get_pivot(global_frame_width, global_frame_height)
            lines.append(f"  - name: {c.name}")
            lines.append(f"    layer_name: {c.layer_name}")
            lines.append(f"    tag: {c.tag}")
            lines.append(f"    start_x: {c.start_x}")
            lines.append(f"    start_y: {c.start_y}")
            lines.append(f"    num_frames: {c.num_frames}")
            lines.append(f"    fps: {c.fps}")
            lines.append(f"    pivot_x: {px}")
            lines.append(f"    pivot_y: {py}")
            if c.frame_cells:
                lines.append("    frame_cells:")
                for cx, cy in c.frame_cells:
                    lines.append(f"      - x: {cx}")
                    lines.append(f"        y: {cy}")
        yaml_str = "\n".join(lines) + "\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(yaml_str)


def load_spritesheet_configs(filepath: str) -> Tuple[List[SpritesheetAnimationConfig], int, int]:
    """Loads animation configs and global frame dimensions from a YAML .pixpref file."""
    if not os.path.exists(filepath):
        return [], 32, 32

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    configs: List[SpritesheetAnimationConfig] = []
    global_fw = 32
    global_fh = 32

    try:
        import yaml
        data = yaml.safe_load(content)
        if isinstance(data, dict):
            global_fw = max(1, int(data.get("global_frame_width", 32)))
            global_fh = max(1, int(data.get("global_frame_height", 32)))
            raw_anims = data.get("animations", [])
            if isinstance(raw_anims, list):
                for item in raw_anims:
                    if isinstance(item, dict):
                        configs.append(SpritesheetAnimationConfig.from_dict(item))
    except Exception:
        current_dict = None
        for line in content.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue
            if line_str.startswith("global_frame_width:"):
                try:
                    global_fw = max(1, int(line_str.split(":", 1)[1].strip()))
                except ValueError:
                    pass
            elif line_str.startswith("global_frame_height:"):
                try:
                    global_fh = max(1, int(line_str.split(":", 1)[1].strip()))
                except ValueError:
                    pass
            elif line_str.startswith("- name:") or line_str.startswith("name:"):
                if current_dict:
                    configs.append(SpritesheetAnimationConfig.from_dict(current_dict))
                val = line_str.split(":", 1)[1].strip().strip("\"'")
                current_dict = {"name": val}
            elif current_dict is not None and ":" in line_str:
                k, v = line_str.split(":", 1)
                k = k.strip().lstrip("- ")
                v = v.strip().strip("\"'")
                current_dict[k] = v
        if current_dict:
            configs.append(SpritesheetAnimationConfig.from_dict(current_dict))

    return configs, global_fw, global_fh


def slice_image_to_sparse_pixels(img: QImage, x: int, y: int, width: int, height: int) -> Dict[str, str]:
    """Extracts pixel region from QImage and converts non-transparent pixels to sparse format."""
    pixels: Dict[str, str] = {}
    if img is None or img.isNull():
        return pixels

    fmt_img = img.convertToFormat(QImage.Format_ARGB32)
    img_w = fmt_img.width()
    img_h = fmt_img.height()
    src_bits = fmt_img.bits()
    stride = fmt_img.bytesPerLine()

    for py in range(height):
        sy = y + py
        if sy < 0 or sy >= img_h:
            continue
        row_base = sy * stride
        for px in range(width):
            sx = x + px
            if sx < 0 or sx >= img_w:
                continue
            idx = row_base + sx * 4
            b = src_bits[idx]
            g = src_bits[idx + 1]
            r = src_bits[idx + 2]
            a = src_bits[idx + 3]
            if a > 0:
                pixels[f"{px},{py}"] = f"#{r:02X}{g:02X}{b:02X}{a:02X}"

    return pixels


def build_document_from_spritesheet(
    img: QImage,
    configs: List[SpritesheetAnimationConfig],
    global_frame_width: int = 32,
    global_frame_height: int = 32,
    override_layer_name: Optional[str] = None,
    override_tag: Optional[str] = None,
) -> PixelDocument:
    """Builds a new PixelDocument with animations, frames, layer tags, and pivot points."""
    fw = max(1, global_frame_width)
    fh = max(1, global_frame_height)
    img_w = img.width() if img and not img.isNull() else 8192

    doc = PixelDocument(width=fw, height=fh)
    doc.animations.clear()

    if not configs:
        configs = [SpritesheetAnimationConfig(name="idle", start_x=0, start_y=0, num_frames=1)]

    for cfg in configs:
        anim_name = cfg.name.strip() or "new-animation"
        target_layer_name = (override_layer_name.strip() if override_layer_name and override_layer_name.strip() else cfg.layer_name.strip()) or "Layer 1"
        target_tag = (override_tag.strip() if override_tag and override_tag.strip() else cfg.tag.strip()) or "default"

        px, py = cfg.get_pivot(fw, fh)
        anim = Animation(name=anim_name, fps=cfg.fps, pivot_x=px, pivot_y=py)
        anim.frames.clear()

        frame_positions = cfg.get_frame_positions(fw, fh, img_w=img_w)

        for f_idx, (frame_x, frame_y) in enumerate(frame_positions):
            sparse_pixels = slice_image_to_sparse_pixels(img, frame_x, frame_y, fw, fh)

            frame = AnimationFrame(name=f"Frame {f_idx + 1}")
            # Delete default 'Background' layer
            frame.layers = [l for l in frame.layers if l.name != "Background"]

            layer = Layer(name=target_layer_name, tag=target_tag)
            layer.pixels = sparse_pixels
            frame.layers.append(layer)
            frame.active_layer_index = 0
            anim.frames.append(frame)

        if not anim.frames:
            anim.frames.append(AnimationFrame("Frame 1"))

        anim.active_frame_index = 0
        doc.animations.append(anim)

    if not doc.animations:
        doc.animations.append(Animation("new-animation", pivot_x=fw // 2, pivot_y=fh // 2))

    doc.active_animation_index = 0
    return doc


def add_spritesheet_layers_to_document(
    doc: PixelDocument,
    img: QImage,
    configs: List[SpritesheetAnimationConfig],
    global_frame_width: int = 32,
    global_frame_height: int = 32,
    override_layer_name: Optional[str] = None,
    override_tag: Optional[str] = None,
) -> PixelDocument:
    """Appends sliced spritesheet frames as new layers with layer tags to an existing PixelDocument."""
    fw = max(1, global_frame_width)
    fh = max(1, global_frame_height)
    img_w = img.width() if img and not img.isNull() else 8192

    if doc.width != fw or doc.height != fh:
        doc.resize_canvas(fw, fh)

    default_single_anim = (
        len(doc.animations) == 1
        and doc.animations[0].name.strip().lower() in ("new-animation", "animation 1", "new animation")
    )

    for cfg_idx, cfg in enumerate(configs):
        cfg_name = cfg.name.strip() or "new-animation"
        target_layer_name = (override_layer_name.strip() if override_layer_name and override_layer_name.strip() else cfg.layer_name.strip()) or "Layer 1"
        target_tag = (override_tag.strip() if override_tag and override_tag.strip() else cfg.tag.strip()) or "default"

        target_anim = None

        if default_single_anim and cfg_idx == 0:
            target_anim = doc.animations[0]
            target_anim.name = cfg_name
            target_anim.fps = cfg.fps
        else:
            for anim in doc.animations:
                if anim.name.strip().lower() == cfg_name.lower():
                    target_anim = anim
                    break

        px, py = cfg.get_pivot(fw, fh)
        if target_anim is None:
            target_anim = doc.add_animation(cfg_name)
            target_anim.fps = cfg.fps

        target_anim.pivot_x = px
        target_anim.pivot_y = py

        frame_positions = cfg.get_frame_positions(fw, fh, img_w=img_w)

        for f_idx, (frame_x, frame_y) in enumerate(frame_positions):
            sparse_pixels = slice_image_to_sparse_pixels(img, frame_x, frame_y, fw, fh)

            while len(target_anim.frames) <= f_idx:
                new_f = AnimationFrame(name=f"Frame {len(target_anim.frames) + 1}")
                new_f.layers = [l for l in new_f.layers if l.name != "Background"]
                target_anim.frames.append(new_f)

            target_frame = target_anim.frames[f_idx]
            target_frame.layers = [l for l in target_frame.layers if l.name != "Background" or len(l.pixels) > 0]

            new_layer = Layer(name=target_layer_name, tag=target_tag)
            new_layer.pixels = sparse_pixels
            target_frame.layers.append(new_layer)
            target_frame.active_layer_index = len(target_frame.layers) - 1

    return doc
