import os
from typing import List, Optional
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import (
    QDialog,
    QDockWidget,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from .color_dialog import ColorPickerDialog



def _qcolor_from_hex(hex_str: str) -> QColor:
    """Parse a #RRGGBBAA string into a QColor. Handles both 6-char and 8-char forms."""
    s = hex_str.lstrip("#")
    if len(s) == 8:
        r, g, b, a = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16)
        return QColor(r, g, b, a)
    elif len(s) == 6:
        r, g, b = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
        return QColor(r, g, b, 255)
    return QColor(hex_str)


def _hex_from_qcolor(col: QColor) -> str:
    """Produce a #RRGGBBAA string from a QColor (consistent with document model)."""
    return f"#{col.red():02X}{col.green():02X}{col.blue():02X}{col.alpha():02X}"


def _to_css_rgba(hex_rrggbbaa: str) -> str:
    """Convert #RRGGBBAA to 'rgba(r,g,b,a)' for Qt stylesheets."""
    s = hex_rrggbbaa.lstrip("#")
    if len(s) == 8:
        r, g, b, a = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16)
        return f"rgba({r},{g},{b},{round(a/255.0, 4)})"
    elif len(s) == 6:
        r, g, b = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
        return f"rgba({r},{g},{b},1.0)"
    return hex_rrggbbaa


def extract_palette_from_image(filepath: str) -> List[str]:
    """Extracts unique non-transparent colors from a palette PNG (e.g. Lospec palettes)."""
    image = QImage(filepath)
    if image.isNull():
        return []

    colors = []
    seen = set()
    w = image.width()
    h = image.height()

    for y in range(h):
        for x in range(w):
            qcol = image.pixelColor(x, y)
            if qcol.alpha() > 0:
                hex_str = f"#{qcol.red():02X}{qcol.green():02X}{qcol.blue():02X}{qcol.alpha():02X}"
                if hex_str not in seen:
                    seen.add(hex_str)
                    colors.append(hex_str)

    return colors


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


DEFAULT_PALETTE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "default-palette.png")


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
            f"QPushButton:hover {{ border: 2px solid #F97316; }}"
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
        self.current_swatches: List[str] = list(DEFAULT_SWATCHES)

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignTop)

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

        # 2. Pick Custom Color & Load Palette Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        self.custom_btn = QPushButton("Picker...")
        self.custom_btn.setToolTip("Open Custom Color Dialog")
        self.custom_btn.setObjectName("secondaryButton")
        self.custom_btn.clicked.connect(lambda: self.pick_custom_color(True))

        self.load_pal_btn = QPushButton("📥 Palette")
        self.load_pal_btn.setToolTip("Upload Palette PNG Image (e.g. from Lospec)")
        self.load_pal_btn.setObjectName("secondaryButton")
        self.load_pal_btn.clicked.connect(self.on_load_palette_png)

        self.reset_pal_btn = QPushButton("↺")
        self.reset_pal_btn.setToolTip("Reset to Default Palette")
        self.reset_pal_btn.setFixedWidth(28)
        self.reset_pal_btn.setObjectName("secondaryButton")
        self.reset_pal_btn.clicked.connect(self.reset_to_default_palette)

        btn_layout.addWidget(self.custom_btn)
        btn_layout.addWidget(self.load_pal_btn)
        btn_layout.addWidget(self.reset_pal_btn)
        layout.addLayout(btn_layout)

        # 3. Palette Header with Minimize / Expand Toggle Button
        header_layout = QHBoxLayout()
        header_layout.setSpacing(4)

        self.toggle_pal_btn = QPushButton("▶")
        self.toggle_pal_btn.setFixedSize(20, 20)
        self.toggle_pal_btn.setToolTip("Minimize / Expand Palette Display")
        self.toggle_pal_btn.setObjectName("secondaryButton")
        self.toggle_pal_btn.setStyleSheet("QPushButton { font-size: 9px; padding: 0px; border-radius: 3px; }")
        self.toggle_pal_btn.clicked.connect(self.toggle_palette_visibility)

        self.palette_header = QLabel("Pixel Art Palette")
        self.palette_header.setStyleSheet("font-weight: 600; color: #94A3B8; font-size: 11px;")
        self.palette_header.setCursor(Qt.PointingHandCursor)
        self.palette_header.mousePressEvent = lambda e: self.toggle_palette_visibility()

        header_layout.addWidget(self.toggle_pal_btn)
        header_layout.addWidget(self.palette_header)
        header_layout.addStretch(1)
        layout.addLayout(header_layout)

        # 4. Scrollable Swatch Grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(4)

        self.scroll_area.setWidget(self.grid_container)
        layout.addWidget(self.scroll_area, stretch=1)
        layout.addStretch(1)

        # Default state: minimized
        self._palette_expanded = False
        self.scroll_area.hide()

        self.setWidget(main_widget)
        self.reset_to_default_palette()
        self.update_swatch_displays()

    def toggle_palette_visibility(self) -> None:
        """Toggles visibility of the scrollable palette swatch grid."""
        self._palette_expanded = not self._palette_expanded
        self.scroll_area.setVisible(self._palette_expanded)
        self.toggle_pal_btn.setText("▼" if self._palette_expanded else "▶")




    def set_swatches(self, swatches: List[str], palette_name: Optional[str] = None) -> None:
        """Rebuilds the color swatch grid from a list of hex color strings."""
        # Clear existing grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.current_swatches = list(swatches) if swatches else list(DEFAULT_SWATCHES)
        count = len(self.current_swatches)

        if palette_name:
            self.palette_header.setText(f"Palette: {palette_name} ({count})")
        else:
            self.palette_header.setText(f"Pixel Art Palette ({count} colors)")

        cols = 8
        for idx, hex_col in enumerate(self.current_swatches):
            r = idx // cols
            c = idx % cols
            btn = ColorSwatchButton(hex_col)
            btn.color_clicked.connect(self.on_swatch_clicked)
            self.grid_layout.addWidget(btn, r, c)

        if self.current_swatches:
            self.set_primary_color(self.current_swatches[0])

    def load_palette_from_image(self, filepath: str) -> bool:
        """Loads palette colors from a PNG image file (such as a Lospec palette)."""
        colors = extract_palette_from_image(filepath)
        if not colors:
            QMessageBox.warning(self, "Invalid Palette Image", "Could not extract colors from image.")
            return False

        name = os.path.splitext(os.path.basename(filepath))[0]
        self.set_swatches(colors, palette_name=name)
        return True

    def on_load_palette_png(self) -> None:
        """Opens file dialog to select a Palette PNG file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Load Palette PNG Image", "", "PNG Images (*.png);;Image Files (*.png *.jpg *.bmp);;All Files (*)"
        )
        if filepath:
            self.load_palette_from_image(filepath)

    def reset_to_default_palette(self) -> None:
        """Resets the palette back to default palette PNG image or fallback swatches."""
        if os.path.exists(DEFAULT_PALETTE_PATH):
            if self.load_palette_from_image(DEFAULT_PALETTE_PATH):
                return
        self.set_swatches(DEFAULT_SWATCHES, palette_name="Default")

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
        dialog = ColorPickerDialog(
            initial_color=current,
            swatches=self.current_swatches,
            parent=self,
        )
        if dialog.exec() == QDialog.Accepted:
            hex_str = dialog.get_selected_color_hex()
            if is_primary:
                self.set_primary_color(hex_str)
            else:
                self.set_secondary_color(hex_str)



