"""
Tag Panel Widget for managing layer tags and global tag visibility in Coopixel.
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDockWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from coopixel.models.document import PixelDocument


class TagItemWidget(QFrame):
    """Row widget representing a single unique tag with eye toggle button."""

    visibility_toggled = Signal(str, bool)

    def __init__(self, tag: str, is_visible: bool, layer_count: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.tag = tag
        self.is_visible = is_visible

        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(
            "TagItemWidget { background-color: #242424; border: 1px solid #333333; border-radius: 4px; padding: 2px; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)

        # Eye Toggle Button
        self.eye_btn = QPushButton("👁️" if is_visible else "🙈")
        self.eye_btn.setToolTip(f"Toggle visibility for all '{tag}' layers across all frames & animations")
        self.eye_btn.setObjectName("secondaryButton")
        self.eye_btn.setFixedWidth(36)
        self.eye_btn.clicked.connect(self._on_eye_clicked)

        # Tag Label
        self.tag_label = QLabel(f"🏷️ {tag}")
        self.tag_label.setStyleSheet("font-weight: bold; color: #F1F5F9; font-size: 11px;")

        # Layer Count Badge
        count_str = f"({layer_count} layer)" if layer_count == 1 else f"({layer_count} layers)"
        self.count_label = QLabel(count_str)
        self.count_label.setStyleSheet("color: #94A3B8; font-size: 10px;")

        layout.addWidget(self.eye_btn)
        layout.addWidget(self.tag_label)
        layout.addWidget(self.count_label, stretch=1)

    def _on_eye_clicked(self) -> None:
        self.is_visible = not self.is_visible
        self.eye_btn.setText("👁️" if self.is_visible else "🙈")
        self.visibility_toggled.emit(self.tag, self.is_visible)


class TagPanel(QDockWidget):
    """Dock widget for inspecting and toggling visibility for layer tags across the entire file."""

    # Emitted when tag visibility changes -> repaints canvas, refreshes layer panel, and pushes history
    tag_visibility_changed = Signal()

    def __init__(self, doc: Optional[PixelDocument] = None, parent: Optional[QWidget] = None):
        super().__init__("Tag Manager", parent)
        self.doc: PixelDocument = doc if doc is not None else PixelDocument()
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # Instruction Header
        info_lbl = QLabel("Global Tag Visibility")
        info_lbl.setStyleSheet("color: #D97706; font-weight: bold; font-size: 11px;")
        main_layout.addWidget(info_lbl)

        # Scrollable Tag Container
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(4)
        self.container_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.container)
        main_layout.addWidget(self.scroll_area, stretch=1)

        self.setWidget(main_widget)
        self.refresh_tags()

    def set_document(self, doc: PixelDocument) -> None:
        self.doc = doc
        self.refresh_tags()

    def refresh_tags(self) -> None:
        """Rebuilds the list of tags from all frames and animations in the document."""
        # Clear container layout
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tags = self.doc.get_all_tags()
        if not tags:
            empty_lbl = QLabel("No layer tags in file.\n\nRight-click any layer to set a tag!")
            empty_lbl.setWordWrap(True)
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("color: #64748B; font-style: italic; padding: 20px 8px; font-size: 10px;")
            self.container_layout.addWidget(empty_lbl)
            return

        for tag in tags:
            layer_cnt = self.doc.get_tag_layer_count(tag)
            is_vis = self.doc.is_tag_visible(tag)
            item_widget = TagItemWidget(tag, is_vis, layer_cnt)
            item_widget.visibility_toggled.connect(self._on_tag_visibility_toggled)
            self.container_layout.addWidget(item_widget)

    def _on_tag_visibility_toggled(self, tag: str, visible: bool) -> None:
        self.doc.set_tag_visibility(tag, visible)
        self.tag_visibility_changed.emit()
