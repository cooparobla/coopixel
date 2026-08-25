"""
Align Panel Dock Widget for Coopixel.
Provides interactive alignment of active layer pixel content relative to canvas boundaries.
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDockWidget,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from coopixel.models.document import PixelDocument


class AlignPanel(QDockWidget):
    """Dock widget for aligning active layer content relative to canvas bounds."""

    # Emitted when an alignment action alters the active layer pixels
    align_committed = Signal(str)

    def __init__(self, doc: Optional[PixelDocument] = None, parent: Optional[QWidget] = None):
        super().__init__("Align", parent)
        self.doc: Optional[PixelDocument] = doc

        self.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.setStyleSheet(
            "QDockWidget { color: #F1F5F9; font-weight: bold; titlebar-close-icon: url(none); titlebar-normal-icon: url(none); }"
            "QDockWidget::title { background: #1E1E1E; padding: 6px; border-bottom: 1px solid #333333; }"
        )

        container = QWidget()
        container.setStyleSheet("background-color: #1A1A1A; color: #F1F5F9;")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(12)

        # ---- Group: Align to Canvas ----
        align_group = QGroupBox("Align to Canvas")
        align_group.setStyleSheet(
            "QGroupBox { font-size: 11px; font-weight: bold; color: #94A3B8; border: 1px solid #333333; border-radius: 6px; margin-top: 10px; padding-top: 12px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; background-color: #1A1A1A; }"
        )
        group_layout = QVBoxLayout(align_group)
        group_layout.setContentsMargins(8, 10, 8, 10)
        group_layout.setSpacing(8)

        # Horizontal alignment buttons row
        h_row = QHBoxLayout()
        h_row.setSpacing(6)

        self.btn_left = QPushButton("⬅️ Left")
        self.btn_left.setToolTip("Align active layer content to left canvas edge")

        self.btn_center_h = QPushButton("↔️ Center H")
        self.btn_center_h.setToolTip("Center active layer content horizontally")

        self.btn_right = QPushButton("➡️ Right")
        self.btn_right.setToolTip("Align active layer content to right canvas edge")

        for btn in (self.btn_left, self.btn_center_h, self.btn_right):
            btn.setStyleSheet(
                "QPushButton { background-color: #282828; border: 1px solid #333333; border-radius: 4px; padding: 6px; font-size: 11px; color: #F1F5F9; font-weight: 600; }"
                "QPushButton:hover { background-color: #332B25; border-color: #F97316; color: #FFFFFF; }"
            )
            h_row.addWidget(btn)

        group_layout.addLayout(h_row)

        # Vertical alignment buttons row
        v_row = QHBoxLayout()
        v_row.setSpacing(6)

        self.btn_top = QPushButton("⬆️ Top")
        self.btn_top.setToolTip("Align active layer content to top canvas edge")

        self.btn_center_v = QPushButton("↕️ Center V")
        self.btn_center_v.setToolTip("Center active layer content vertically")

        self.btn_bottom = QPushButton("⬇️ Bottom")
        self.btn_bottom.setToolTip("Align active layer content to bottom canvas edge")

        for btn in (self.btn_top, self.btn_center_v, self.btn_bottom):
            btn.setStyleSheet(
                "QPushButton { background-color: #282828; border: 1px solid #333333; border-radius: 4px; padding: 6px; font-size: 11px; color: #F1F5F9; font-weight: 600; }"
                "QPushButton:hover { background-color: #332B25; border-color: #F97316; color: #FFFFFF; }"
            )
            v_row.addWidget(btn)

        group_layout.addLayout(v_row)

        # Center both button
        self.btn_center_both = QPushButton("🎯 Center Both (H & V)")
        self.btn_center_both.setToolTip("Center active layer content both horizontally and vertically")
        self.btn_center_both.setStyleSheet(
            "QPushButton { background-color: #2E2620; border: 1px solid #F97316; border-radius: 4px; padding: 7px; font-size: 11px; color: #F97316; font-weight: bold; }"
            "QPushButton:hover { background-color: #F97316; color: #FFFFFF; }"
        )
        group_layout.addWidget(self.btn_center_both)

        main_layout.addWidget(align_group)
        main_layout.addStretch(1)

        # Wire click handlers
        self.btn_left.clicked.connect(lambda: self.align_active_layer("left"))
        self.btn_center_h.clicked.connect(lambda: self.align_active_layer("center_h"))
        self.btn_right.clicked.connect(lambda: self.align_active_layer("right"))
        self.btn_top.clicked.connect(lambda: self.align_active_layer("top"))
        self.btn_center_v.clicked.connect(lambda: self.align_active_layer("center_v"))
        self.btn_bottom.clicked.connect(lambda: self.align_active_layer("bottom"))
        self.btn_center_both.clicked.connect(lambda: self.align_active_layer("center_both"))

        self.setWidget(container)

    def set_document(self, doc: PixelDocument) -> None:
        self.doc = doc

    def align_active_layer(self, mode: str) -> None:
        """Aligns active layer content relative to canvas boundaries."""
        if not self.doc:
            return
        active = self.doc.active_layer
        if not active or active.locked or not active.visible or not active.pixels:
            return

        bbox = active.get_content_bbox()
        if not bbox:
            return

        bx, by, bw, bh = bbox
        doc_w, doc_h = self.doc.width, self.doc.height

        target_bx, target_by = bx, by

        if mode == "left":
            target_bx = 0
            desc = "Aligned layer to Left"
        elif mode == "center_h":
            target_bx = (doc_w - bw) // 2
            desc = "Centered layer horizontally"
        elif mode == "right":
            target_bx = doc_w - bw
            desc = "Aligned layer to Right"
        elif mode == "top":
            target_by = 0
            desc = "Aligned layer to Top"
        elif mode == "center_v":
            target_by = (doc_h - bh) // 2
            desc = "Centered layer vertically"
        elif mode == "bottom":
            target_by = doc_h - bh
            desc = "Aligned layer to Bottom"
        elif mode == "center_both":
            target_bx = (doc_w - bw) // 2
            target_by = (doc_h - bh) // 2
            desc = "Centered layer horizontally and vertically"
        else:
            return

        dx = target_bx - bx
        dy = target_by - by

        if dx == 0 and dy == 0:
            return

        # Shift layer pixels by (dx, dy)
        new_pixels = {}
        for coord_str, color_hex in active.pixels.items():
            parts = coord_str.split(",")
            if len(parts) == 2:
                px, py = int(parts[0]), int(parts[1])
                new_pixels[f"{px + dx},{py + dy}"] = color_hex
        active.pixels = new_pixels

        self.align_committed.emit(desc)
