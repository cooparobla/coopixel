"""
Color Palette Dock Panel for Coopixel.
Includes Primary / Secondary color swatches, custom color dialog picker, and standard pixel art swatches.
"""

from typing import Optional
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QDockWidget,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def _qcolor_from_hex(hex_str: str) -> QColor:
    """Parse a #RRGGBBAA string into a QColor. Handles both 6-char and 8-char forms."""
    s = hex_str.lstrip("#")
    if len(s) == 8:
        r, g, b, a = int(s[0:2],16), int(s[2:4],16), int(s[4:6],16), int(s[6:8],16)
        return QColor(r, g, b, a)
    elif len(s) == 6:
        r, g, b = int(s[0:2],16), int(s[2:4],16), int(s[4:6],16)
        return QColor(r, g, b, 255)
    return QColor(hex_str)


def _hex_from_qcolor(col: QColor) -> str:
    """Produce a #RRGGBBAA string from a QColor (consistent with document model)."""
    return f"#{col.red():02X}{col.green():02X}{col.blue():02X}{col.alpha():02X}"


def _to_css_rgba(hex_rrggbbaa: str) -> str:
    """Convert #RRGGBBAA to 'rgba(r,g,b,a)' for Qt stylesheets.
    Qt QSS parses 8-digit #hex as #AARRGGBB, which is the OPPOSITE of our internal format.
    Using rgba() is unambiguous.
    """
    s = hex_rrggbbaa.lstrip("#")
    if len(s) == 8:
        r, g, b, a = int(s[0:2],16), int(s[2:4],16), int(s[4:6],16), int(s[6:8],16)
        return f"rgba({r},{g},{b},{round(a/255.0, 4)})"
    elif len(s) == 6:
        r, g, b = int(s[0:2],16), int(s[2:4],16), int(s[4:6],16)
        return f"rgba({r},{g},{b},1.0)"
    return hex_rrggbbaa


DEFAULT_SWATCHES = [
    # Row 1: Grayscale
    "#000000FF", "#1D2B53FF", "#7E2553FF", "#008751FF", "#AB5236FF", "#5F574FFF", "#C2C3C7FF", "#FFF1E8FF",
    # Row 2: Standard PICO-8 / Pixel Art Colors
    "#FF004DFF", "#FFA300FF", "#FFEC27FF", "#00E436FF", "#29ADFFFF", "#83769CFF", "#FF77A8FF", "#FFCCAAFF",
    # Row 3: Extended Vibrants
    "#264653FF", "#2A9D8FFF", "#E9C46AFF", "#F4A261FF", "#E76F51FF", "#8D99AEFF", "#2B2D42FF", "#D90429FF",
    # Row 4: Pastels & Accents
    "#B5E2FAFF", "#F9F7F3FF", "#EDEEC4FF", "#F7D6E0FF", "#F2B5D4FF", "#70C1B3FF", "#247BA0FF", "#FFE066FF",
]


class ColorSwatchButton(QPushButton):
    color_clicked = Signal(str, Qt.MouseButton)

    def __init__(self, hex_color: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.hex_color = hex_color
        self.setFixedSize(22, 22)
        self.setToolTip(f"Color: {hex_color}")
        self.update_style()

    def update_style(self) -> None:
        css_col = _to_css_rgba(self.hex_color)
        self.setStyleSheet(
            f"QPushButton {{ background-color: {css_col}; border: 1px solid #333B4D; border-radius: 4px; }}"
            f"QPushButton:hover {{ border: 2px solid #3B82F6; }}"
        )

    def mousePressEvent(self, event) -> None:
        self.color_clicked.emit(self.hex_color, event.button())


class ColorPanel(QDockWidget):
    primary_color_changed = Signal(str)
    secondary_color_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Colors", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.primary_color: str = "#FF004DFF"
        self.secondary_color: str = "#00000000"

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # 1. Active Swatches Display
        swatch_layout = QHBoxLayout()
        swatch_layout.setSpacing(12)

        # Primary Swatch Box
        pri_box = QVBoxLayout()
        pri_box.setAlignment(Qt.AlignCenter)
        pri_lbl = QLabel("Primary")
        pri_lbl.setStyleSheet("font-size: 11px; color: #94A3B8;")
        self.pri_swatch = QFrame()
        self.pri_swatch.setFixedSize(40, 40)
        self.pri_swatch.setCursor(Qt.PointingHandCursor)
        self.pri_swatch.mousePressEvent = lambda e: self.pick_custom_color(True)
        pri_box.addWidget(pri_lbl)
        pri_box.addWidget(self.pri_swatch)

        # Swap Button
        self.swap_btn = QPushButton("⇄")
        self.swap_btn.setFixedSize(28, 28)
        self.swap_btn.setToolTip("Swap Primary / Secondary Colors")
        self.swap_btn.setObjectName("secondaryButton")
        self.swap_btn.clicked.connect(self.swap_colors)

        # Secondary Swatch Box
        sec_box = QVBoxLayout()
        sec_box.setAlignment(Qt.AlignCenter)
        sec_lbl = QLabel("Secondary")
        sec_lbl.setStyleSheet("font-size: 11px; color: #94A3B8;")
        self.sec_swatch = QFrame()
        self.sec_swatch.setFixedSize(40, 40)
        self.sec_swatch.setCursor(Qt.PointingHandCursor)
        self.sec_swatch.mousePressEvent = lambda e: self.pick_custom_color(False)
        sec_box.addWidget(sec_lbl)
        sec_box.addWidget(self.sec_swatch)

        swatch_layout.addLayout(pri_box)
        swatch_layout.addWidget(self.swap_btn)
        swatch_layout.addLayout(sec_box)
        layout.addLayout(swatch_layout)

        # 2. Pick Custom Color Button
        self.custom_btn = QPushButton("Custom Color Picker...")
        self.custom_btn.setObjectName("secondaryButton")
        self.custom_btn.clicked.connect(lambda: self.pick_custom_color(True))
        layout.addWidget(self.custom_btn)

        # 3. Swatch Grid
        palette_lbl = QLabel("Pixel Art Palette")
        palette_lbl.setStyleSheet("font-weight: 600; color: #94A3B8;")
        layout.addWidget(palette_lbl)

        grid = QGridLayout()
        grid.setSpacing(4)
        cols = 8
        for idx, hex_col in enumerate(DEFAULT_SWATCHES):
            r = idx // cols
            c = idx % cols
            btn = ColorSwatchButton(hex_col)
            btn.color_clicked.connect(self.on_swatch_clicked)
            grid.addWidget(btn, r, c)

        layout.addLayout(grid)
        layout.addStretch(1)

        self.setWidget(main_widget)
        self.update_swatch_displays()

    def update_swatch_displays(self) -> None:
        pri_css = _to_css_rgba(self.primary_color)
        sec_css = _to_css_rgba(self.secondary_color)
        self.pri_swatch.setStyleSheet(
            f"background-color: {pri_css}; border: 2px solid #E2E8F0; border-radius: 6px;"
        )
        self.sec_swatch.setStyleSheet(
            f"background-color: {sec_css}; border: 2px solid #64748B; border-radius: 6px;"
        )

    def set_primary_color(self, hex_color: str) -> None:
        self.primary_color = hex_color
        self.update_swatch_displays()
        self.primary_color_changed.emit(self.primary_color)

    def set_secondary_color(self, hex_color: str) -> None:
        self.secondary_color = hex_color
        self.update_swatch_displays()
        self.secondary_color_changed.emit(self.secondary_color)

    def swap_colors(self) -> None:
        self.primary_color, self.secondary_color = self.secondary_color, self.primary_color
        self.update_swatch_displays()
        self.primary_color_changed.emit(self.primary_color)
        self.secondary_color_changed.emit(self.secondary_color)

    def on_swatch_clicked(self, hex_col: str, button: Qt.MouseButton) -> None:
        if button == Qt.RightButton:
            self.set_secondary_color(hex_col)
        else:
            self.set_primary_color(hex_col)

    def pick_custom_color(self, is_primary: bool) -> None:
        current = self.primary_color if is_primary else self.secondary_color
        initial = _qcolor_from_hex(current)
        col = QColorDialog.getColor(initial, self, "Select Color", QColorDialog.ShowAlphaChannel)
        if col.isValid():
            hex_str = _hex_from_qcolor(col)   # always #RRGGBBAA
            if is_primary:
                self.set_primary_color(hex_str)
            else:
                self.set_secondary_color(hex_str)

