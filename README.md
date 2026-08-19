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
