"""
Custom Color Selection Dialog for Coopixel.
Features Palette and Wheel tabs with full RGB and Alpha (transparency) controls.
"""

import math
from typing import List, Optional
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


def _qcolor_from_hex(hex_str: str) -> QColor:
    """Parse a #RRGGBBAA or #RRGGBB string into a QColor."""
    s = hex_str.lstrip("#")
    if len(s) == 8:
        r, g, b, a = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16)
        return QColor(r, g, b, a)
    elif len(s) == 6:
        r, g, b = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
        return QColor(r, g, b, 255)
    return QColor(hex_str)


def _hex_from_qcolor(col: QColor) -> str:
    """Produce a #RRGGBBAA string from a QColor."""
    return f"#{col.red():02X}{col.green():02X}{col.blue():02X}{col.alpha():02X}"


def _make_checkerboard_pixmap(tile_size: int = 6) -> QPixmap:
    """Creates a small 2x2 checkerboard tile pixmap for transparency preview."""
    pm = QPixmap(tile_size * 2, tile_size * 2)
    p = QPainter(pm)
    p.fillRect(0, 0, tile_size * 2, tile_size * 2, QColor("#1E293B"))
    light = QColor("#334155")
    p.fillRect(0, 0, tile_size, tile_size, light)
    p.fillRect(tile_size, tile_size, tile_size, tile_size, light)
    p.end()
    return pm


class CheckerboardSwatch(QFrame):
    """A swatch frame displaying a color with a checkerboard background for alpha transparency."""

    def __init__(self, color: QColor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.color = QColor(color)
        self.checker_pm = _make_checkerboard_pixmap()

    def set_color(self, color: QColor) -> None:
        self.color = QColor(color)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        # Draw background checkerboard
        painter.drawTiledPixmap(rect, self.checker_pm)

        # Draw color on top
        painter.fillRect(rect, self.color)

        # Draw border
        painter.setPen(QPen(QColor("#475569"), 1))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
        painter.end()


class ColorWheelWidget(QWidget):
    """
    Interactive HSV Color Wheel widget.
    Angle = Hue (0..360 deg), Radius = Saturation (0..1.0).
    """

    color_changed = Signal(QColor)

    def __init__(self, color: QColor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(190, 190)

        # Store HSV values
        self._hue: float = max(0.0, color.hueF()) if color.hueF() >= 0 else 0.0
        self._sat: float = color.saturationF()
        self._val: float = color.valueF()
        self._alpha: int = color.alpha()

        self._wheel_img: Optional[QImage] = None
        self._cached_val: float = -1.0
        self.dragging = False

    def get_color(self) -> QColor:
        c = QColor.fromHsvF(self._hue, self._sat, self._val)
        c.setAlpha(self._alpha)
        return c

    def set_color(self, color: QColor, block_signal: bool = False) -> None:
        new_hue = max(0.0, color.hueF()) if color.hueF() >= 0 else 0.0
        new_sat = color.saturationF()
        new_val = color.valueF()
        new_alpha = color.alpha()

        val_changed = abs(self._val - new_val) > 0.001
        self._hue = new_hue
        self._sat = new_sat
        self._val = new_val
        self._alpha = new_alpha

        if val_changed:
            self._wheel_img = None

        self.update()

        if not block_signal:
            self.color_changed.emit(self.get_color())

    def _render_wheel_image(self) -> None:
        w = self.width()
        h = self.height()
        cx, cy = w / 2.0, h / 2.0
        radius = min(cx, cy) - 6.0

        img = QImage(w, h, QImage.Format_ARGB32)
        img.fill(Qt.transparent)

        for y in range(h):
            dy = y - cy
            for x in range(w):
                dx = x - cx
                dist = math.hypot(dx, dy)
                if dist <= radius:
                    angle = math.atan2(-dy, dx)
                    if angle < 0:
                        angle += 2 * math.pi
                    hue = angle / (2 * math.pi)
                    sat = dist / radius
                    col = QColor.fromHsvF(hue, sat, self._val)
                    img.setPixelColor(x, y, col)

        self._wheel_img = img
        self._cached_val = self._val

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._wheel_img is None or abs(self._cached_val - self._val) > 0.001:
            self._render_wheel_image()

        if self._wheel_img:
            painter.drawImage(0, 0, self._wheel_img)

        # Draw outer ring border
        w = self.width()
        h = self.height()
        cx, cy = w / 2.0, h / 2.0
        radius = min(cx, cy) - 6.0

        painter.setPen(QPen(QColor("#475569"), 1.5))
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # Draw cursor marker for current (Hue, Saturation)
        angle = self._hue * 2 * math.pi
        marker_dist = self._sat * radius
        marker_x = cx + marker_dist * math.cos(angle)
        marker_y = cy - marker_dist * math.sin(angle)

        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.drawEllipse(QPointF(marker_x, marker_y), 5, 5)
        painter.setPen(QPen(QColor("#000000"), 1))
        painter.drawEllipse(QPointF(marker_x, marker_y), 6, 6)
        painter.end()

    def _update_from_mouse(self, pos: QPointF) -> None:
        w = self.width()
        h = self.height()
        cx, cy = w / 2.0, h / 2.0
        radius = min(cx, cy) - 6.0

        dx = pos.x() - cx
        dy = pos.y() - cy
        dist = math.hypot(dx, dy)

        angle = math.atan2(-dy, dx)
        if angle < 0:
            angle += 2 * math.pi

        self._hue = angle / (2 * math.pi)
        self._sat = min(1.0, max(0.0, dist / radius))

        self.update()
        self.color_changed.emit(self.get_color())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self._update_from_mouse(event.position())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.dragging:
            self._update_from_mouse(event.position())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.dragging = False


class ColorPickerDialog(QDialog):
    """
    Modal color selection dialog featuring Palette and Wheel tabs
    with complete RGB and Alpha (transparency) channel controls.
    """

    def __init__(self, initial_color: str, swatches: List[str], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Select Color")
        self.setMinimumSize(420, 480)
        self.resize(440, 500)

        self.initial_color = _qcolor_from_hex(initial_color)
        self.current_color = QColor(self.initial_color)
        self.swatches = swatches
        self._updating_controls = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self._create_palette_tab(), "🎨 Palette")
        self.tab_widget.addTab(self._create_wheel_tab(), "🌈 Wheel")
        layout.addWidget(self.tab_widget, stretch=1)

        # Bottom Preview and OK/Cancel bar
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(12)

        # Old vs New Preview Box
        prev_container = QVBoxLayout()
        prev_lbl = QLabel("Color Preview")
        prev_lbl.setStyleSheet("font-size: 10px; color: #94A3B8; font-weight: bold;")
        prev_container.addWidget(prev_lbl)

        preview_box = QHBoxLayout()
        preview_box.setSpacing(0)

        self.old_swatch = CheckerboardSwatch(self.initial_color)
        self.old_swatch.setFixedSize(50, 28)
        self.old_swatch.setToolTip("Original Color")

        self.new_swatch = CheckerboardSwatch(self.current_color)
        self.new_swatch.setFixedSize(50, 28)
        self.new_swatch.setToolTip("New Selected Color")

        preview_box.addWidget(self.old_swatch)
        preview_box.addWidget(self.new_swatch)
        prev_container.addLayout(preview_box)
        bottom_layout.addLayout(prev_container)

        bottom_layout.addStretch()

        # Dialog Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        bottom_layout.addWidget(buttons)

        layout.addLayout(bottom_layout)

        # Initialize control states
        self.update_controls_from_color(self.current_color)

    def _create_palette_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        lbl = QLabel("Select a color from the active project palette:")
        lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(lbl)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: 1px solid #334155; background: #0F172A; border-radius: 4px; }")

        grid_container = QWidget()
        grid_layout = QGridLayout(grid_container)
        grid_layout.setContentsMargins(8, 8, 8, 8)
        grid_layout.setSpacing(6)

        cols = 8
        for idx, hex_col in enumerate(self.swatches):
            r = idx // cols
            c = idx % cols
            qcol = _qcolor_from_hex(hex_col)
            btn = QPushButton()
            btn.setFixedSize(32, 32)
            css_rgba = f"rgba({qcol.red()},{qcol.green()},{qcol.blue()},{round(qcol.alpha()/255.0, 3)})"
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {css_rgba}; border: 1px solid #475569; border-radius: 4px; }}"
                f"QPushButton:hover {{ border: 2px solid #F97316; }}"
            )
            btn.setToolTip(f"{hex_col}")
            btn.clicked.connect(lambda _, col=qcol: self._on_palette_swatch_clicked(col))
            grid_layout.addWidget(btn, r, c)

        scroll_area.setWidget(grid_container)
        layout.addWidget(scroll_area, stretch=1)
        return widget

    def _create_wheel_tab(self) -> QWidget:
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(12)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(16)

        # Color Wheel Widget
        self.wheel_widget = ColorWheelWidget(self.current_color)
        self.wheel_widget.color_changed.connect(self._on_wheel_color_changed)
        top_layout.addWidget(self.wheel_widget, alignment=Qt.AlignCenter)

        # Right sliders layout (Value & Alpha)
        slider_layout = QFormLayout()
        slider_layout.setSpacing(8)

        # Value Slider
        self.val_slider = QSlider(Qt.Vertical)
        self.val_slider.setRange(0, 255)
        self.val_slider.setToolTip("Brightness / Value (0 - 255)")
        self.val_slider.setFixedHeight(170)
        self.val_slider.valueChanged.connect(self._on_value_slider_changed)

        # Alpha Slider
        self.alpha_slider = QSlider(Qt.Vertical)
        self.alpha_slider.setRange(0, 255)
        self.alpha_slider.setToolTip("Alpha / Opacity (0 - 255)")
        self.alpha_slider.setFixedHeight(170)
        self.alpha_slider.valueChanged.connect(self._on_alpha_slider_changed)

        sliders_box = QHBoxLayout()
        sliders_box.setSpacing(12)

        v_box = QVBoxLayout()
        v_box.addWidget(QLabel("Val", alignment=Qt.AlignCenter))
        v_box.addWidget(self.val_slider, alignment=Qt.AlignCenter)
        sliders_box.addLayout(v_box)

        a_box = QVBoxLayout()
        a_box.addWidget(QLabel("Alpha", alignment=Qt.AlignCenter))
        a_box.addWidget(self.alpha_slider, alignment=Qt.AlignCenter)
        sliders_box.addLayout(a_box)

        top_layout.addLayout(sliders_box)
        main_layout.addLayout(top_layout)

        # Numerical Spinboxes & Hex Edit
        controls_group = QFrame()
        controls_group.setStyleSheet("QFrame { background: #1E293B; border-radius: 6px; padding: 6px; }")
        grid = QGridLayout(controls_group)
        grid.setSpacing(8)

        # RGB SpinBoxes
        self.r_spin = QSpinBox()
        self.r_spin.setRange(0, 255)
        self.g_spin = QSpinBox()
        self.g_spin.setRange(0, 255)
        self.b_spin = QSpinBox()
        self.b_spin.setRange(0, 255)
        self.a_spin = QSpinBox()
        self.a_spin.setRange(0, 255)

        for spin in (self.r_spin, self.g_spin, self.b_spin, self.a_spin):
            spin.valueChanged.connect(self._on_rgba_spin_changed)

        grid.addWidget(QLabel("R:"), 0, 0)
        grid.addWidget(self.r_spin, 0, 1)
        grid.addWidget(QLabel("G:"), 0, 2)
        grid.addWidget(self.g_spin, 0, 3)

        grid.addWidget(QLabel("B:"), 1, 0)
        grid.addWidget(self.b_spin, 1, 1)
        grid.addWidget(QLabel("Alpha:"), 1, 2)
        grid.addWidget(self.a_spin, 1, 3)

        # Hex Edit Field
        grid.addWidget(QLabel("Hex:"), 2, 0)
        self.hex_edit = QLineEdit()
        self.hex_edit.setMaxLength(9)
        self.hex_edit.setPlaceholderText("#RRGGBBAA")
        self.hex_edit.textEdited.connect(self._on_hex_edited)
        grid.addWidget(self.hex_edit, 2, 1, 1, 3)

        main_layout.addWidget(controls_group)
        return widget

    def _on_palette_swatch_clicked(self, color: QColor) -> None:
        self.update_controls_from_color(color)

    def _on_wheel_color_changed(self, color: QColor) -> None:
        if self._updating_controls:
            return
        self.update_controls_from_color(color, source="wheel")

    def _on_value_slider_changed(self, val: int) -> None:
        if self._updating_controls:
            return
        col = QColor(self.current_color)
        h, s, v, a = col.hueF(), col.saturationF(), col.valueF(), col.alpha()
        col.setHsvF(max(0.0, h) if h >= 0 else 0.0, s, val / 255.0, a / 255.0)
        self.update_controls_from_color(col, source="val_slider")

    def _on_alpha_slider_changed(self, alpha: int) -> None:
        if self._updating_controls:
            return
        col = QColor(self.current_color)
        col.setAlpha(alpha)
        self.update_controls_from_color(col, source="alpha_slider")

    def _on_rgba_spin_changed(self) -> None:
        if self._updating_controls:
            return
        r = self.r_spin.value()
        g = self.g_spin.value()
        b = self.b_spin.value()
        a = self.a_spin.value()
        col = QColor(r, g, b, a)
        self.update_controls_from_color(col, source="rgba_spins")

    def _on_hex_edited(self, text: str) -> None:
        if self._updating_controls:
            return
        hex_clean = text.strip()
        if len(hex_clean) in (7, 9) and hex_clean.startswith("#"):
            try:
                col = _qcolor_from_hex(hex_clean)
                self.update_controls_from_color(col, source="hex_edit")
            except ValueError:
                pass

    def update_controls_from_color(self, color: QColor, source: str = "") -> None:
        """Updates all controls and preview swatch to reflect the specified QColor."""
        self._updating_controls = True
        self.current_color = QColor(color)

        if source != "wheel":
            self.wheel_widget.set_color(color, block_signal=True)

        if source != "val_slider":
            self.val_slider.setValue(color.value())

        if source != "alpha_slider":
            self.alpha_slider.setValue(color.alpha())

        if source != "rgba_spins":
            self.r_spin.setValue(color.red())
            self.g_spin.setValue(color.green())
            self.b_spin.setValue(color.blue())
            self.a_spin.setValue(color.alpha())

        if source != "hex_edit":
            self.hex_edit.setText(_hex_from_qcolor(color))

        self.new_swatch.set_color(color)
        self._updating_controls = False

    def get_selected_color_hex(self) -> str:
        """Returns the final selected color as a #RRGGBBAA hex string."""
        return _hex_from_qcolor(self.current_color)
