"""
Appearance & Layer Effects Dock Panel for Coopixel.
Allows adding, configuring, toggling, and removing layer effects (e.g. Stroke) on the active layer.
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDockWidget,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from coopixel.models.document import PixelDocument
from coopixel.models.effects import HueSaturationContrastEffect, StrokeEffect



def _qcolor_from_hex(hex_str: str) -> QColor:
    s = hex_str.lstrip("#")
    if len(s) == 8:
        return QColor(int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16))
    elif len(s) == 6:
        return QColor(int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255)
    return QColor(hex_str)


def _hex_from_qcolor(col: QColor) -> str:
    return f"#{col.red():02X}{col.green():02X}{col.blue():02X}{col.alpha():02X}"


def _to_css_rgba(hex_rrggbbaa: str) -> str:
    s = hex_rrggbbaa.lstrip("#")
    if len(s) == 8:
        r, g, b, a = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16)
        return f"rgba({r},{g},{b},{round(a/255.0, 4)})"
    return hex_rrggbbaa


class StrokeEffectWidget(QFrame):
    """Widget control box for configuring a single StrokeEffect instance."""

    changed = Signal()
    delete_requested = Signal()

    def __init__(self, stroke: StrokeEffect, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.stroke = stroke
        self.setStyleSheet("QFrame { background: #282828; border: 1px solid #333333; border-radius: 6px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # ---- Title bar with Enable Checkbox and Delete Button ----
        header = QHBoxLayout()
        header.setSpacing(6)

        self.enable_cb = QCheckBox("Stroke")
        self.enable_cb.setChecked(stroke.enabled)
        self.enable_cb.setStyleSheet("font-weight: 600; color: #F1F5F9;")
        self.enable_cb.toggled.connect(self._on_enable_toggled)

        self.del_btn = QPushButton("🗑️ Remove")
        self.del_btn.setToolTip("Remove Effect from Active Layer")
        self.del_btn.setObjectName("secondaryButton")
        self.del_btn.setStyleSheet(
            "QPushButton#secondaryButton { background-color: #282828; color: #EF4444; border: 1px solid #333333; padding: 2px 8px; font-size: 10px; font-weight: bold; }"
            "QPushButton#secondaryButton:hover { background-color: #3F1D1D; border-color: #EF4444; color: #FFFFFF; }"
        )
        self.del_btn.clicked.connect(self.delete_requested.emit)

        header.addWidget(self.enable_cb)
        header.addStretch(1)
        header.addWidget(self.del_btn)
        layout.addLayout(header)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

        # ---- Controls Grid ----
        props_widget = QWidget()
        props_layout = QVBoxLayout(props_widget)
        props_layout.setContentsMargins(4, 0, 4, 2)
        props_layout.setSpacing(6)

        # 1. Color Picker Row
        col_row = QHBoxLayout()
        col_row.setSpacing(6)
        col_lbl = QLabel("Color:")
        col_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")

        self.color_swatch = QFrame()
        self.color_swatch.setFixedSize(36, 22)
        self.color_swatch.setCursor(Qt.PointingHandCursor)
        self.color_swatch.setToolTip("Click to change stroke color")
        self.color_swatch.mousePressEvent = lambda e: self._pick_color()

        col_row.addWidget(col_lbl)
        col_row.addWidget(self.color_swatch)
        col_row.addStretch(1)
        props_layout.addLayout(col_row)

        # 2. Size & Position Row
        size_row = QHBoxLayout()
        size_row.setSpacing(6)

        size_lbl = QLabel("Size:")
        size_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 10)
        self.size_spin.setValue(stroke.size)
        self.size_spin.setSuffix(" px")
        self.size_spin.valueChanged.connect(self._on_size_changed)

        pos_lbl = QLabel("Pos:")
        pos_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.pos_combo = QComboBox()
        self.pos_combo.addItems(["outside", "inside", "center"])
        self.pos_combo.setCurrentText(stroke.position)
        self.pos_combo.currentTextChanged.connect(self._on_pos_changed)

        size_row.addWidget(size_lbl)
        size_row.addWidget(self.size_spin)
        size_row.addWidget(pos_lbl)
        size_row.addWidget(self.pos_combo)
        props_layout.addLayout(size_row)

        layout.addWidget(props_widget)
        self._update_swatch()

    def _update_swatch(self) -> None:
        css = _to_css_rgba(self.stroke.color)
        self.color_swatch.setStyleSheet(
            f"background-color: {css}; border: 1px solid #64748B; border-radius: 4px;"
        )

    def _pick_color(self) -> None:
        initial = _qcolor_from_hex(self.stroke.color)
        col = QColorDialog.getColor(initial, self, "Select Stroke Color", QColorDialog.ShowAlphaChannel)
        if col.isValid():
            self.stroke.color = _hex_from_qcolor(col)
            self._update_swatch()
            self.changed.emit()

    def _on_enable_toggled(self, checked: bool) -> None:
        self.stroke.enabled = checked
        self.changed.emit()

    def _on_size_changed(self, val: int) -> None:
        self.stroke.size = val
        self.changed.emit()

    def _on_pos_changed(self, pos_str: str) -> None:
        self.stroke.position = pos_str
        self.changed.emit()

    def _on_context_menu(self, pos) -> None:
        menu = QMenu(self)
        del_act = menu.addAction("🗑️ Remove Effect")
        action = menu.exec_(self.mapToGlobal(pos)) if hasattr(menu, 'exec_') else menu.exec(self.mapToGlobal(pos))
        if action == del_act:
            self.delete_requested.emit()


class HueSatContrastEffectWidget(QFrame):
    """Widget control box for configuring a HueSaturationContrastEffect instance."""

    changed = Signal()
    delete_requested = Signal()

    def __init__(self, effect: HueSaturationContrastEffect, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.effect = effect
        self.setStyleSheet("QFrame { background: #282828; border: 1px solid #333333; border-radius: 6px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # Header with Enable Checkbox, Reset Button, Delete Button
        header = QHBoxLayout()
        header.setSpacing(4)

        self.enable_cb = QCheckBox("Hue / Sat / Contrast")
        self.enable_cb.setChecked(effect.enabled)
        self.enable_cb.setStyleSheet("font-weight: 600; color: #F1F5F9;")
        self.enable_cb.toggled.connect(self._on_enable_toggled)

        self.reset_btn = QPushButton("↺")
        self.reset_btn.setToolTip("Reset modifier sliders to 0")
        self.reset_btn.setFixedSize(22, 22)
        self.reset_btn.setObjectName("secondaryButton")
        self.reset_btn.clicked.connect(self._reset_values)

        self.del_btn = QPushButton("🗑️ Remove")
        self.del_btn.setToolTip("Remove Effect from Active Layer")
        self.del_btn.setObjectName("secondaryButton")
        self.del_btn.setStyleSheet(
            "QPushButton#secondaryButton { background-color: #282828; color: #EF4444; border: 1px solid #333333; padding: 2px 8px; font-size: 10px; font-weight: bold; }"
            "QPushButton#secondaryButton:hover { background-color: #3F1D1D; border-color: #EF4444; color: #FFFFFF; }"
        )
        self.del_btn.clicked.connect(self.delete_requested.emit)

        header.addWidget(self.enable_cb)
        header.addStretch(1)
        header.addWidget(self.reset_btn)
        header.addWidget(self.del_btn)
        layout.addLayout(header)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

        # Controls Grid
        props_widget = QWidget()
        props_layout = QFormLayout(props_widget)
        props_layout.setContentsMargins(4, 0, 4, 2)
        props_layout.setSpacing(6)

        # 1. Hue SpinBox (-180 to +180 deg)
        self.hue_spin = QSpinBox()
        self.hue_spin.setRange(-180, 180)
        self.hue_spin.setValue(effect.hue)
        self.hue_spin.setSuffix("°")
        self.hue_spin.valueChanged.connect(self._on_hue_changed)

        # 2. Saturation SpinBox (-100 to +100 %)
        self.sat_spin = QSpinBox()
        self.sat_spin.setRange(-100, 100)
        self.sat_spin.setValue(effect.saturation)
        self.sat_spin.setSuffix("%")
        self.sat_spin.valueChanged.connect(self._on_sat_changed)

        # 3. Contrast SpinBox (-100 to +100 %)
        self.contrast_spin = QSpinBox()
        self.contrast_spin.setRange(-100, 100)
        self.contrast_spin.setValue(effect.contrast)
        self.contrast_spin.setSuffix("%")
        self.contrast_spin.valueChanged.connect(self._on_contrast_changed)

        props_layout.addRow("Hue:", self.hue_spin)
        props_layout.addRow("Saturation:", self.sat_spin)
        props_layout.addRow("Contrast:", self.contrast_spin)
        layout.addWidget(props_widget)

    def _on_enable_toggled(self, checked: bool) -> None:
        self.effect.enabled = checked
        self.changed.emit()

    def _on_hue_changed(self, val: int) -> None:
        self.effect.hue = val
        self.changed.emit()

    def _on_sat_changed(self, val: int) -> None:
        self.effect.saturation = val
        self.changed.emit()

    def _on_contrast_changed(self, val: int) -> None:
        self.effect.contrast = val
        self.changed.emit()

    def _reset_values(self) -> None:
        self.hue_spin.setValue(0)
        self.sat_spin.setValue(0)
        self.contrast_spin.setValue(0)

    def _on_context_menu(self, pos) -> None:
        menu = QMenu(self)
        del_act = menu.addAction("🗑️ Remove Effect")
        action = menu.exec_(self.mapToGlobal(pos)) if hasattr(menu, 'exec_') else menu.exec(self.mapToGlobal(pos))
        if action == del_act:
            self.delete_requested.emit()


class AppearancePanel(QDockWidget):
    """Dock panel for managing active layer effects."""

    effect_changed = Signal()

    def __init__(self, doc: Optional[PixelDocument] = None, parent: Optional[QWidget] = None):
        super().__init__("Appearance", parent)
        self.doc: PixelDocument = doc if doc is not None else PixelDocument()
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # 1. Layer Name Indicator
        self.layer_name_lbl = QLabel("Target: None")
        self.layer_name_lbl.setStyleSheet("font-weight: 600; color: #94A3B8; font-size: 11px;")
        main_layout.addWidget(self.layer_name_lbl)

        # 2. Add Effect Action Button
        self.add_btn = QPushButton("+ Add Layer Effect")
        self.add_btn.setToolTip("Add new effect to active layer")
        self.add_btn.setStyleSheet(
            "QPushButton { background: #C25E00; color: #FFFFFF; font-weight: 600; border-radius: 4px; padding: 4px 8px; }"
            "QPushButton:hover { background: #D97706; }"
        )
        self.add_btn.clicked.connect(self._show_add_effect_menu)
        main_layout.addWidget(self.add_btn)

        # 3. Scrollable Effects Container
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.effects_container = QWidget()
        self.effects_layout = QVBoxLayout(self.effects_container)
        self.effects_layout.setContentsMargins(0, 0, 0, 0)
        self.effects_layout.setSpacing(6)
        self.effects_layout.addStretch(1)

        self.scroll_area.setWidget(self.effects_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

        self.setWidget(main_widget)
        self.refresh_panel()

    def set_document(self, doc: PixelDocument) -> None:
        self.doc = doc
        self.refresh_panel()

    def refresh_panel(self) -> None:
        """Rebuild the effects list from the active layer."""
        # Clear existing effect widgets
        while self.effects_layout.count() > 0:
            item = self.effects_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        active = self.doc.active_layer
        if not active:
            self.layer_name_lbl.setText("Target: None")
            self.add_btn.setEnabled(False)
            return

        self.layer_name_lbl.setText(f"Layer: {active.name}")
        self.add_btn.setEnabled(True)

        # Add widget for each effect on active layer
        for effect in list(active.effects):
            if isinstance(effect, StrokeEffect):
                w = StrokeEffectWidget(effect, self)
                w.changed.connect(self.effect_changed.emit)
                w.delete_requested.connect(lambda *args, eff=effect: self.remove_effect_object(eff))
                self.effects_layout.addWidget(w)
            elif isinstance(effect, HueSaturationContrastEffect):
                w = HueSatContrastEffectWidget(effect, self)
                w.changed.connect(self.effect_changed.emit)
                w.delete_requested.connect(lambda *args, eff=effect: self.remove_effect_object(eff))
                self.effects_layout.addWidget(w)

        self.effects_layout.addStretch(1)

    def _show_add_effect_menu(self) -> None:
        menu = QMenu(self)
        stroke_action = menu.addAction("🎨 Stroke (Outline)")
        hsc_action = menu.addAction("🌈 Hue / Saturation / Contrast")
        action = menu.exec(self.add_btn.mapToGlobal(self.add_btn.rect().bottomLeft()))
        if action == stroke_action:
            self.add_stroke_effect()
        elif action == hsc_action:
            self.add_hue_sat_contrast_effect()

    def add_stroke_effect(self) -> None:
        active = self.doc.active_layer
        if active:
            active.effects.append(StrokeEffect(enabled=True, size=1, color="#000000FF", position="outside"))
            self.refresh_panel()
            self.effect_changed.emit()

    def add_hue_sat_contrast_effect(self) -> None:
        active = self.doc.active_layer
        if active:
            active.effects.append(HueSaturationContrastEffect(enabled=True, hue=0, saturation=0, contrast=0))
            self.refresh_panel()
            self.effect_changed.emit()

    def remove_effect_object(self, effect) -> None:
        """Removes a specific layer effect instance from the active layer."""
        active = self.doc.active_layer
        if active and effect in active.effects:
            active.effects.remove(effect)
            self.refresh_panel()
            self.effect_changed.emit()

