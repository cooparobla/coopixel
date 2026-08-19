"""
Animation Panel Widget for managing animation sequences, frames, and playback in Coopixel.
"""

from typing import Optional
from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from coopixel.models.document import PixelDocument


class FrameCardWidget(QFrame):
    """Widget representing a single frame thumbnail card in the animation timeline."""

    def __init__(self, index: int, frame_name: str, thumbnail: QImage, is_active: bool, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.index = index
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedWidth(72)
        self.setFixedHeight(84)

        bg_color = "#2563EB" if is_active else "#1E232A"
        border_color = "#3B82F6" if is_active else "#2D3748"
        self.setStyleSheet(
            f"FrameCardWidget {{ background-color: {bg_color}; border: 2px solid {border_color}; border-radius: 6px; }}"
            f"QLabel {{ color: #F1F5F9; border: none; font-size: 11px; font-weight: bold; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        # Thumbnail Image Label
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(48, 48)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        pix = QPixmap.fromImage(thumbnail).scaled(48, 48, Qt.KeepAspectRatio, Qt.FastTransformation)
        self.thumb_label.setPixmap(pix)
        self.thumb_label.setStyleSheet("background-color: #121417; border: 1px solid #333B4D; border-radius: 4px;")

        # Title Label
        self.title_label = QLabel(f"#{index + 1}")
        self.title_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.thumb_label, alignment=Qt.AlignCenter)
        layout.addWidget(self.title_label, alignment=Qt.AlignCenter)


class AnimationPanel(QDockWidget):
    # Emitted when animation list changes (add/rename/delete) -> triggers history push
    animation_structure_changed = Signal()
    # Emitted when frame structure changes (add/dup/delete/move) -> triggers history push
    frame_structure_changed = Signal()
    # Emitted when active frame or active animation changes -> repaints canvas & updates layer panel
    active_frame_changed = Signal()
    # Emitted when animation visual attributes change (FPS/onion skin) -> repaints
    animation_visual_changed = Signal()

    def __init__(self, doc: Optional[PixelDocument] = None, parent: Optional[QWidget] = None):
        super().__init__("Animation Timeline", parent)
        self.doc: PixelDocument = doc if doc is not None else PixelDocument()
        self.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)

        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self._on_play_step)
        self.is_playing = False

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # 0. Top Animation Selector Bar
        anim_bar_layout = QHBoxLayout()
        anim_bar_layout.setSpacing(6)

        anim_lbl = QLabel("Animation:")
        anim_lbl.setStyleSheet("color: #94A3B8; font-weight: bold; font-size: 12px;")

        self.anim_combo = QComboBox()
        self.anim_combo.setToolTip("Select Active Animation Sequence")
        self.anim_combo.setMinimumWidth(160)
        self.anim_combo.setStyleSheet(
            "QComboBox { background-color: #1E232A; color: #F1F5F9; border: 1px solid #2D3748; border-radius: 4px; padding: 3px 8px; font-weight: 500; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background-color: #1A1D24; color: #F1F5F9; selection-background-color: #2563EB; }"
        )
        self.anim_combo.currentIndexChanged.connect(self.on_animation_selected)

        self.rename_anim_btn = QPushButton("✏️ Rename")
        self.rename_anim_btn.setToolTip("Rename Active Animation")
        self.rename_anim_btn.setObjectName("secondaryButton")
        self.rename_anim_btn.clicked.connect(self.on_rename_animation)

        self.add_anim_btn = QPushButton("+ Animation")
        self.add_anim_btn.setToolTip("Create New Distinct Animation Sequence")
        self.add_anim_btn.clicked.connect(self.on_add_animation)

        self.del_anim_btn = QPushButton("🗑️ Delete Anim")
        self.del_anim_btn.setToolTip("Delete Active Animation Sequence")
        self.del_anim_btn.setObjectName("secondaryButton")
        self.del_anim_btn.clicked.connect(self.on_delete_animation)

        anim_bar_layout.addWidget(anim_lbl)
        anim_bar_layout.addWidget(self.anim_combo)
        anim_bar_layout.addWidget(self.rename_anim_btn)
        anim_bar_layout.addWidget(self.add_anim_btn)
        anim_bar_layout.addWidget(self.del_anim_btn)
        anim_bar_layout.addStretch(1)

        layout.addLayout(anim_bar_layout)

        # 1. Controls Bar
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(6)

        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setToolTip("Play / Pause Animation")
        self.play_btn.clicked.connect(self.toggle_play)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setToolTip("Stop Animation & Return to Frame 1")
        self.stop_btn.setObjectName("secondaryButton")
        self.stop_btn.clicked.connect(self.stop_playback)

        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setToolTip("Previous Frame")
        self.prev_btn.setObjectName("secondaryButton")
        self.prev_btn.clicked.connect(self.on_prev_frame)

        self.next_btn = QPushButton("⏭")
        self.next_btn.setToolTip("Next Frame")
        self.next_btn.setObjectName("secondaryButton")
        self.next_btn.clicked.connect(self.on_next_frame)

        ctrl_layout.addWidget(self.play_btn)
        ctrl_layout.addWidget(self.stop_btn)
        ctrl_layout.addWidget(self.prev_btn)
        ctrl_layout.addWidget(self.next_btn)

        # Separator line
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet("color: #2D3748;")
        ctrl_layout.addWidget(sep1)

        self.add_btn = QPushButton("+ Frame")
        self.add_btn.setToolTip("Add New Blank Frame")
        self.add_btn.clicked.connect(self.on_add_frame)

        self.dup_btn = QPushButton("📋 Dup")
        self.dup_btn.setToolTip("Duplicate Active Frame")
        self.dup_btn.setObjectName("secondaryButton")
        self.dup_btn.clicked.connect(self.on_duplicate_frame)

        self.del_btn = QPushButton("🗑️ Delete")
        self.del_btn.setToolTip("Delete Active Frame")
        self.del_btn.setObjectName("secondaryButton")
        self.del_btn.clicked.connect(self.on_delete_frame)

        self.move_left_btn = QPushButton("◀")
        self.move_left_btn.setToolTip("Move Frame Left")
        self.move_left_btn.setObjectName("secondaryButton")
        self.move_left_btn.clicked.connect(self.on_move_frame_left)

        self.move_right_btn = QPushButton("▶")
        self.move_right_btn.setToolTip("Move Frame Right")
        self.move_right_btn.setObjectName("secondaryButton")
        self.move_right_btn.clicked.connect(self.on_move_frame_right)

        ctrl_layout.addWidget(self.add_btn)
        ctrl_layout.addWidget(self.dup_btn)
        ctrl_layout.addWidget(self.del_btn)
        ctrl_layout.addWidget(self.move_left_btn)
        ctrl_layout.addWidget(self.move_right_btn)

        # Separator line
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet("color: #2D3748;")
        ctrl_layout.addWidget(sep2)

        # FPS Box
        fps_label = QLabel("FPS:")
        fps_label.setStyleSheet("color: #94A3B8; font-weight: bold;")
        self.fps_box = QSpinBox()
        self.fps_box.setRange(1, 60)
        self.fps_box.setValue(self.doc.fps)
        self.fps_box.setFixedWidth(54)
        self.fps_box.setToolTip("Frames Per Second")
        self.fps_box.valueChanged.connect(self.on_fps_changed)

        ctrl_layout.addWidget(fps_label)
        ctrl_layout.addWidget(self.fps_box)

        ctrl_layout.addStretch(1)

        # Counter Label
        self.counter_label = QLabel("Frame 1 / 1")
        self.counter_label.setStyleSheet("color: #94A3B8; font-weight: bold; font-size: 12px;")
        ctrl_layout.addWidget(self.counter_label)

        layout.addLayout(ctrl_layout)

        # 2. Timeline Scroll Area for Frame Cards
        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setWidgetResizable(True)
        self.timeline_scroll.setFixedHeight(104)
        self.timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.timeline_scroll.setStyleSheet(
            "QScrollArea { background-color: #121417; border: 1px solid #2D3748; border-radius: 6px; }"
        )

        self.strip_widget = QWidget()
        self.strip_layout = QHBoxLayout(self.strip_widget)
        self.strip_layout.setContentsMargins(6, 6, 6, 6)
        self.strip_layout.setSpacing(8)
        self.strip_layout.setAlignment(Qt.AlignLeft)
        self.timeline_scroll.setWidget(self.strip_widget)

        layout.addWidget(self.timeline_scroll)
        self.setWidget(main_widget)

        self.refresh_animation_combo()
        self.refresh_timeline()

    def set_document(self, doc: PixelDocument) -> None:
        self.stop_playback()
        self.doc = doc
        self.fps_box.setValue(self.doc.fps)
        self.refresh_animation_combo()
        self.refresh_timeline()

    def refresh_animation_combo(self) -> None:
        self.anim_combo.blockSignals(True)
        self.anim_combo.clear()
        for anim in self.doc.animations:
            self.anim_combo.addItem(anim.name)
        self.anim_combo.setCurrentIndex(self.doc.active_animation_index)
        self.anim_combo.blockSignals(False)
        self.del_anim_btn.setEnabled(len(self.doc.animations) > 1)

    def on_animation_selected(self, index: int) -> None:
        if index >= 0 and self.doc.select_animation(index):
            self.stop_playback()
            self.fps_box.setValue(self.doc.fps)
            self.refresh_timeline()
            self.active_frame_changed.emit()

    def on_add_animation(self) -> None:
        name, ok = QInputDialog.getText(self, "New Animation", "Animation Name:", text="new-animation")
        if ok and name.strip():
            self.doc.add_animation(name.strip())
            self.refresh_animation_combo()
            self.refresh_timeline()
            self.animation_structure_changed.emit()
            self.active_frame_changed.emit()

    def on_rename_animation(self) -> None:
        current_name = self.doc.active_animation.name
        name, ok = QInputDialog.getText(self, "Rename Animation", "New Animation Name:", text=current_name)
        if ok and name.strip() and name.strip() != current_name:
            self.doc.rename_animation(self.doc.active_animation_index, name.strip())
            self.refresh_animation_combo()
            self.animation_structure_changed.emit()

    def on_delete_animation(self) -> None:
        if len(self.doc.animations) <= 1:
            return  # Must keep at least 1 animation
        if self.doc.delete_animation(self.doc.active_animation_index):
            self.refresh_animation_combo()
            self.refresh_timeline()
            self.animation_structure_changed.emit()
            self.active_frame_changed.emit()

    def refresh_timeline(self) -> None:
        """Rebuilds frame strip thumbnail cards to reflect current document frames state."""
        # Clear existing widgets
        while self.strip_layout.count():
            item = self.strip_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        frames_cnt = len(self.doc.frames)
        # Enable or disable delete button: CANNOT delete if only 1 frame exists
        self.del_btn.setEnabled(frames_cnt > 1)
        self.counter_label.setText(f"Frame {self.doc.active_frame_index + 1} / {frames_cnt}")

        for i in range(frames_cnt):
            thumb = self.doc.render_frame_qimage(i)
            card = FrameCardWidget(
                index=i,
                frame_name=self.doc.frames[i].name,
                thumbnail=thumb,
                is_active=(i == self.doc.active_frame_index),
                parent=self.strip_widget,
            )
            card.mousePressEvent = lambda evt, idx=i: self.on_select_frame(idx)
            self.strip_layout.addWidget(card)

    def on_select_frame(self, index: int) -> None:
        if self.doc.select_frame(index):
            self.refresh_timeline()
            self.active_frame_changed.emit()

    def toggle_play(self) -> None:
        if self.is_playing:
            self.pause_playback()
        else:
            self.start_playback()

    def start_playback(self) -> None:
        self.is_playing = True
        self.play_btn.setText("⏸ Pause")
        interval = max(10, 1000 // max(1, self.doc.fps))
        self.play_timer.start(interval)

    def pause_playback(self) -> None:
        self.is_playing = False
        self.play_btn.setText("▶ Play")
        self.play_timer.stop()

    def stop_playback(self) -> None:
        self.pause_playback()
        self.doc.select_frame(0)
        self.refresh_timeline()
        self.active_frame_changed.emit()

    def _on_play_step(self) -> None:
        if not self.doc.frames:
            return
        next_idx = (self.doc.active_frame_index + 1) % len(self.doc.frames)
        self.doc.select_frame(next_idx)
        self.refresh_timeline()
        self.active_frame_changed.emit()

    def on_prev_frame(self) -> None:
        if not self.doc.frames:
            return
        prev_idx = (self.doc.active_frame_index - 1) % len(self.doc.frames)
        self.on_select_frame(prev_idx)

    def on_next_frame(self) -> None:
        if not self.doc.frames:
            return
        next_idx = (self.doc.active_frame_index + 1) % len(self.doc.frames)
        self.on_select_frame(next_idx)

    def on_add_frame(self) -> None:
        self.doc.add_frame()
        self.refresh_timeline()
        self.frame_structure_changed.emit()
        self.active_frame_changed.emit()

    def on_duplicate_frame(self) -> None:
        self.doc.duplicate_frame(self.doc.active_frame_index)
        self.refresh_timeline()
        self.frame_structure_changed.emit()
        self.active_frame_changed.emit()

    def on_delete_frame(self) -> None:
        if len(self.doc.frames) <= 1:
            return  # Must have at least 1 frame
        if self.doc.delete_frame(self.doc.active_frame_index):
            self.refresh_timeline()
            self.frame_structure_changed.emit()
            self.active_frame_changed.emit()

    def on_move_frame_left(self) -> None:
        if self.doc.move_frame_left(self.doc.active_frame_index):
            self.refresh_timeline()
            self.frame_structure_changed.emit()
            self.active_frame_changed.emit()

    def on_move_frame_right(self) -> None:
        if self.doc.move_frame_right(self.doc.active_frame_index):
            self.refresh_timeline()
            self.frame_structure_changed.emit()
            self.active_frame_changed.emit()

    def on_fps_changed(self, value: int) -> None:
        self.doc.fps = max(1, min(60, value))
        if self.is_playing:
            self.play_timer.setInterval(1000 // self.doc.fps)
        self.animation_visual_changed.emit()
