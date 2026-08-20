# 🎨 Coopixel

**Coopixel** is a dark-mode pixel art editor built with Python and **PySide6**. It features a multi-layer canvas, modular layer effects, selection tools, flood/global paint bucket filling, PNG export, and native binary `.pix` file encoding powered by **`pycaml`** (using Zstandard compression and AES-256-GCM encryption with sparse pixel storage).

---

## 🚀 Usage

Coopixel is managed using **`uv`**.

### Launch empty editor:

```bash
uv run coopixel
```

### Open a file directly:

```bash
uv run coopixel example.pix
```

---

## 📦 `.pix` File Format & Data Structure

The `.pix` (and `.caml`) file format is **Coopixel's** native binary storage format for multi-layer, multi-frame pixel art projects. It is powered by the **`pycaml`** library (`CAMLMap`), providing efficient sparse storage, high-ratio **Zstandard (zstd)** compression, and optional **AES-256-GCM** authenticated encryption.

### 🔒 Binary Container Architecture

When a document is saved to a `.pix` file:
1. **Serialization**: Document state (dimensions, animation sequences, frames, layers, sparse pixel maps, and layer effects) is serialized into an in-memory JSON object dictionary.
2. **Compression**: The JSON payload is compressed using **Zstandard (`zstd`)** for optimal compression ratio and blazingly fast decompaction.
3. **Encryption & Authentication**: The compressed data stream is wrapped in an **AES-256-GCM** container with a 12-byte IV and 16-byte authentication tag (using PBKDF2 with SHA-256 key derivation when optional passphrase encryption is enabled).
4. **Header Encoding**: Encoded with binary container metadata by `pycaml.CAMLMap`.

---

### 🎨 Data Structure & JSON Schema

Below is an annotated breakdown of the data hierarchy encoded inside a `.pix` file:

```json
{
  "format": "coopixel",
  "version": "1.0",
  "width": 32,
  "height": 32,
  "active_animation": 0,
  "animations": [
    {
      "name": "new-animation",
      "fps": 10,
      "active_frame": 0,
      "frames": [
        {
          "name": "Frame 1",
          "duration_ms": 100,
          "active_layer": 0,
          "layers": [
            {
              "name": "Background",
              "visible": true,
              "locked": false,
              "opacity": 1.0,
              "tag": "background",
              "pixels": {
                "0,0": "#FF004DFF",
                "15,20": "#29ADFFFF"
              },
              "effects": [
                {
                  "type": "stroke",
                  "enabled": true,
                  "size": 1,
                  "color": "#000000FF",
                  "position": "outside"
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

---

### 📑 Field Reference

| Level | Key Name | Type | Description |
|---|---|---|---|
| **Document** | `format` | `string` | File format magic identifier (`"coopixel"`). |
| | `version` | `string` | Format schema version (`"1.0"`). |
| | `width` | `integer` | Canvas width in pixels (e.g. `32`). |
| | `height` | `integer` | Canvas height in pixels (e.g. `32`). |
| | `active_animation` | `integer` | 0-based index of the currently active animation sequence. |
| | `animations` | `array[object]` | List of animation objects in the document. |
| **Animation** | `name` | `string` | Animation sequence name (e.g. `"walk-cycle"`, `"new-animation"`). |
| | `fps` | `integer` | Target playback speed in frames per second (e.g. `10`). |
| | `active_frame` | `integer` | 0-based index of the active frame in this animation. |
| | `frames` | `array[object]` | List of `AnimationFrame` objects. |
| **Frame** | `name` | `string` | Frame display label (e.g. `"Frame 1"`). |
| | `duration_ms` | `integer` | Frame display duration in milliseconds (default `100`). |
| | `active_layer` | `integer` | 0-based index of the active editing layer. |
| | `layers` | `array[object]` | List of `Layer` objects in stack order (bottom to top). |
| **Layer** | `name` | `string` | Layer label (e.g., `"Outline"`, `"Background"`). |
| | `visible` | `boolean` | Visibility toggle (`true` = visible, `false` = hidden). |
| | `locked` | `boolean` | Edit locking toggle (`true` = locked). |
| | `opacity` | `float` | Layer transparency scale from `0.0` (invisible) to `1.0` (opaque). |
| | `tag` | `string` | Optional tag string for cross-frame/animation layer grouping. |
| | `pixels` | `map[string, string]` | **Sparse Pixel Map**: Map of `"x,y"` coordinate strings to `"#RRGGBBAA"` 8-char hex color values. |
| | `effects` | `array[object]` | Extensible array of modular layer effect configurations. |
| **Effect (`stroke`)** | `type` | `string` | Discriminator type name (`"stroke"`). |
| | `enabled` | `boolean` | Effect active state (`true` / `false`). |
| | `size` | `integer` | Outline stroke width in pixels (`1` to `10`). |
| | `color` | `string` | Stroke color in `"#RRGGBBAA"` hex format. |
| | `position` | `string` | Placement mode (`"outside"`, `"inside"`, or `"center"`). |

---

### ⚡ Sparse Pixel Storage Model

Rather than storing a dense 2D grid array of size $\text{width} \times \text{height}$ for every layer, `.pix` uses **sparse coordinate dictionary mapping**:
- Only non-transparent pixels with $\text{Alpha} > 0$ are recorded in `"pixels"` as key-value pairs (e.g., `"x,y": "#RRGGBBAA"`).
- Empty/transparent canvas pixels consume zero bytes.
- This results in significantly smaller file sizes for pixel art with transparent backgrounds and multi-layer stacks.

---

### 🔄 Legacy Compatibility & Migration

The `.pix` parser automatically handles backward compatibility:
- Legacy single-animation files containing top-level `"frames"` or `"layers"` keys without an explicit `"animations"` wrapper are automatically migrated into a default `"new-animation"` container upon loading.

---

## 🌟 Key Features

- **Layer System & Layer Effects**: Multi-layer editing with visibility, locking, opacity controls, and modular layer effects (including customizable **Stroke** outlines).
- **Selection System**: Paint-draw, box, circle, contiguous flood, and global color selection modes. Supports `Shift` (add), `Alt` / right-click (subtract), and drawing mask protection.
- **Drawing Tools**: Pencil, Eraser, Eyedropper, Bucket Fill (Contiguous & Global modes), Line, Rectangle, and Circle tools.
- **Sparse `.pix` Storage**: Powered by `pycaml`. Only non-transparent pixels consume space in stored `.pix` / `.caml` files.
- **Dark Theme UI**: Left-side Layers & Color docks, central canvas viewport, top options toolbar, right-side Appearance sidebar, and status bar.

---

## ⌨️ Keyboard Shortcuts & Controls

| Shortcut / Action | Function |
|---|---|
| `P` / `E` / `I` / `F` | Pencil / Eraser / Color Picker / Bucket Fill |
| `S` / `L` / `R` / `C` | Selection / Line / Rectangle / Circle |
| `Ctrl + Z` / `Ctrl + Y` | Undo / Redo |
| `Ctrl + A` / `Escape` / `Ctrl + I` | Select All / Deselect / Invert Selection |
| `Shift` (while selecting) | Add to selection |
| `Alt` or Right-Click (selecting) | Subtract from selection |
| `Ctrl + G` | Toggle Pixel Grid |
| `Ctrl + 0` | Reset View (Zoom to 100% & Center Canvas) |
| Scroll Wheel | Zoom Canvas (1x to 128x) |
| Middle Mouse or `Alt + Drag` | Pan Canvas Viewport |
| `Ctrl + S` / `Ctrl + Shift + S` | Save / Save As (`.pix` / `.caml`) |
| `Ctrl + E` | Export PNG Image |

---

## 🧪 Running Tests

```bash
uv run pytest
```
