"""
Animation Panel Widget for managing animation sequences, frames, and playback in Coopixel.
"""

from typing import Optional
from PySide6.QtCore import QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QImage, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from coopixel.models.document import PixelDocument


class FrameCardWidget(QFrame):
    """Widget representing a single frame thumbnail card in the animation timeline."""

    rename_requested = Signal(int)

    def __init__(self, index: int, frame_name: str, thumbnail: QImage, is_active: bool, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.index = index
        self.frame_name = frame_name
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedWidth(86)
        self.setFixedHeight(88)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)

        # Thumbnail Image Label
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(48, 48)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.set_thumbnail(thumbnail)
        self.thumb_label.setStyleSheet("background-color: #181818; border: 1px solid #333333; border-radius: 4px;")

        # Title Label
        display_name = frame_name.strip() if frame_name and frame_name.strip() else f"Frame {index + 1}"
        short_title = display_name if len(display_name) <= 12 else display_name[:10] + "…"
        self.title_label = QLabel(short_title)
        self.title_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.thumb_label, alignment=Qt.AlignCenter)
        layout.addWidget(self.title_label, alignment=Qt.AlignCenter)

        self.set_active(is_active)

        tooltip_text = f"Frame #{index + 1}: {display_name}\n(Double-click or right-click to rename tile/frame)"
        self.setToolTip(tooltip_text)
        self.thumb_label.setToolTip(tooltip_text)
        self.title_label.setToolTip(tooltip_text)

    def set_active(self, is_active: bool) -> None:
        """Updates frame card styling in-place without rebuilding widgets."""
        bg_color = "#2E2620" if is_active else "#222222"
        border_color = "#F97316" if is_active else "#333333"
        self.setStyleSheet(
            f"FrameCardWidget {{ background-color: {bg_color}; border: 2px solid {border_color}; border-radius: 6px; }}"
            f"QLabel {{ color: #F1F5F9; border: none; font-size: 10px; font-weight: bold; }}"
        )

    def set_thumbnail(self, thumbnail: QImage) -> None:
        """Updates thumbnail pixmap in-place."""
        pix = QPixmap.fromImage(thumbnail).scaled(48, 48, Qt.KeepAspectRatio, Qt.FastTransformation)
        self.thumb_label.setPixmap(pix)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.rename_requested.emit(self.index)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class AnimationPanel(QDockWidget):
    # Emitted when animation list changes (add/rename/delete) -> triggers history push
    animation_structure_changed = Signal()
    # Emitted when frame structure changes (add/dup/delete/move/rename) -> triggers history push
    frame_structure_changed = Signal()
    # Emitted when active frame or active animation changes -> repaints canvas & updates layer panel
    active_frame_changed = Signal()
    # Emitted during active playback ticks for ultra-fast canvas-only refresh (bypasses heavy side-panel widget rebuilds)
    playback_frame_changed = Signal(int)
    # Emitted when animation visual attributes change (FPS/onion skin) -> repaints
    animation_visual_changed = Signal()

    def __init__(self, doc: Optional[PixelDocument] = None, parent: Optional[QWidget] = None):
        super().__init__("Animation Timeline", parent)
        self.doc: PixelDocument = doc if doc is not None else PixelDocument()
        self.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)

        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self._on_play_step)
        self.is_playing = False

        # Thumbnail cache keyed by (anim_index, frame_index)
        self._thumb_cache = {}
        self._cards = []

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
            "QComboBox { background-color: #242424; color: #F1F5F9; border: 1px solid #333333; border-radius: 4px; padding: 3px 8px; font-weight: 500; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background-color: #202020; color: #F1F5F9; selection-background-color: #2E2620; selection-color: #F97316; }"
        )
        self.anim_combo.currentIndexChanged.connect(self.on_animation_selected)

        self.rename_anim_btn = QPushButton("✏️ Rename")
        self.rename_anim_btn.setToolTip("Rename Active Animation Sequence")
        self.rename_anim_btn.setObjectName("secondaryButton")
        self.rename_anim_btn.clicked.connect(self.on_rename_animation)

        self.add_anim_btn = QPushButton("+ Animation")
        self.add_anim_btn.setToolTip("Create New Distinct Animation Sequence")
        self.add_anim_btn.clicked.connect(self.on_add_animation)

        self.del_anim_btn = QPushButton("🗑️ Delete Anim")
        self.del_anim_btn.setToolTip("Delete Active Animation Sequence")
        self.del_anim_btn.setObjectName("secondaryButton")
        self.del_anim_btn.clicked.connect(self.on_delete_animation)

        self.mirror_anim_btn = QPushButton("🪞 Mirror (.L/.R)")
        self.mirror_anim_btn.setToolTip("Duplicate animation and flip canvas horizontally with opposite suffix (.L / .R)")
        self.mirror_anim_btn.setObjectName("secondaryButton")
        self.mirror_anim_btn.clicked.connect(self.on_mirror_animation)

        anim_bar_layout.addWidget(anim_lbl)
        anim_bar_layout.addWidget(self.anim_combo)
        anim_bar_layout.addWidget(self.rename_anim_btn)
        anim_bar_layout.addWidget(self.add_anim_btn)
        anim_bar_layout.addWidget(self.del_anim_btn)
        anim_bar_layout.addWidget(self.mirror_anim_btn)
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

        self.rename_frame_btn = QPushButton("✏️ Rename Frame")
        self.rename_frame_btn.setToolTip("Rename Active Frame / Tile Name")
        self.rename_frame_btn.setObjectName("secondaryButton")
        self.rename_frame_btn.clicked.connect(self.on_rename_frame)

        self.del_btn = QPushButton("🗑️ Delete")
        self.del_btn.setToolTip("Delete Active Frame")
        self.del_btn.setObjectName("secondaryButton")
        self.del_btn.clicked.connect(self.on_delete_frame)

        self.move_left_btn = QPushButton("◀")
        self.move_left_btn.setToolTip("Move Frame Left")
        self.move_left_btn.setObjectName("secondaryButton")
        self.move_left_btn.clicked.connect(self.on_move_left)

        self.move_right_btn = QPushButton("▶")
        self.move_right_btn.setToolTip("Move Frame Right")
        self.move_right_btn.setObjectName("secondaryButton")
        self.move_right_btn.clicked.connect(self.on_move_right)

        ctrl_layout.addWidget(self.add_btn)
        ctrl_layout.addWidget(self.dup_btn)
        ctrl_layout.addWidget(self.rename_frame_btn)
        ctrl_layout.addWidget(self.del_btn)
        ctrl_layout.addWidget(self.move_left_btn)
        ctrl_layout.addWidget(self.move_right_btn)

        # Separator line
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet("color: #2D3748;")
        ctrl_layout.addWidget(sep2)

        # FPS SpinBox
        fps_lbl = QLabel("FPS:")
        fps_lbl.setStyleSheet("color: #94A3B8; font-weight: 500;")
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(10)
        self.fps_spin.setSuffix(" fps")
        self.fps_spin.valueChanged.connect(self.on_fps_changed)

        ctrl_layout.addWidget(fps_lbl)
        ctrl_layout.addWidget(self.fps_spin)

        # Frame counter label
        self.counter_label = QLabel("Frame 1 / 1")
        self.counter_label.setStyleSheet("color: #94A3B8; font-weight: 500; padding-left: 8px;")
        ctrl_layout.addWidget(self.counter_label)

        ctrl_layout.addStretch(1)
        layout.addLayout(ctrl_layout)

        # 2. Scrollable Frame Cards Strip
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(104)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.strip_widget = QWidget()
        self.strip_layout = QHBoxLayout(self.strip_widget)
        self.strip_layout.setContentsMargins(0, 0, 0, 0)
        self.strip_layout.setSpacing(6)
        self.strip_layout.setAlignment(Qt.AlignLeft)

        self.scroll_area.setWidget(self.strip_widget)
        layout.addWidget(self.scroll_area)

        self.setWidget(main_widget)
        self.refresh_animation_combo()
        self.refresh_timeline()

    def invalidate_thumbnail(self, frame_index: Optional[int] = None) -> None:
        """Invalidates thumbnail cache for a specific frame or all frames."""
        if self.doc:
            self.doc.invalidate_render_cache(frame_index)
        if frame_index is None:
            self._thumb_cache.clear()
        else:
            anim_idx = self.doc.active_animation_index if self.doc else 0
            self._thumb_cache.pop((anim_idx, frame_index), None)
            if 0 <= frame_index < len(self._cards):
                thumb = self.doc.render_frame_qimage(frame_index)
                self._thumb_cache[(anim_idx, frame_index)] = thumb
                self._cards[frame_index].set_thumbnail(thumb)

    def set_document(self, doc: PixelDocument) -> None:
        self.doc = doc
        self.invalidate_thumbnail()
        self.refresh_animation_combo()
        self.refresh_timeline()

    def refresh_animation_combo(self) -> None:
        self.anim_combo.blockSignals(True)
        self.anim_combo.clear()
        for i, anim in enumerate(self.doc.animations):
            fc = anim.frame_count
            self.anim_combo.addItem(f"🎬 {anim.name} ({fc}f)", i)
        self.anim_combo.setCurrentIndex(self.doc.active_animation_index)
        self.anim_combo.blockSignals(False)
        self.del_anim_btn.setEnabled(len(self.doc.animations) > 1)

    def on_animation_selected(self, index: int) -> None:
        if self.doc.select_animation(index):
            self.refresh_timeline()
            self.active_frame_changed.emit()

    def on_add_animation(self) -> None:
        self.doc.add_animation()
        self.refresh_animation_combo()
        self.refresh_timeline()
        self.animation_structure_changed.emit()
        self.active_frame_changed.emit()

    def on_rename_animation(self) -> None:
        current_name = self.doc.active_animation.name
        name, ok = QInputDialog.getText(self, "Rename Animation Sequence", "New Animation Name:", text=current_name)
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

    def on_mirror_animation(self) -> None:
        if self.doc:
            mirrored = self.doc.mirror_animation()
            if mirrored:
                self.refresh_animation_combo()
                self.refresh_timeline()
                self.animation_structure_changed.emit()
                self.active_frame_changed.emit()

    def on_rename_frame(self, index: Optional[int] = None) -> None:
        if index is None:
            index = self.doc.active_frame_index
        if not (0 <= index < len(self.doc.frames)):
            return

        current_name = self.doc.frames[index].name
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Frame / Tile",
            f"Frame #{index + 1} Name (e.g. 'stone_wall', 'grass_top'):",
            text=current_name,
        )
        if ok and new_name.strip() and new_name.strip() != current_name:
            self.doc.rename_frame(index, new_name.strip())
            self.refresh_timeline()
            self.frame_structure_changed.emit()

    def _on_card_context_menu(self, card_idx: int, pos: QPoint, source_widget: QWidget) -> None:
        menu = QMenu(self)
        rename_act = menu.addAction("✏️ Rename Frame / Tile...")
        dup_act = menu.addAction("📋 Duplicate Frame")
        left_act = menu.addAction("◀ Move Left")
        right_act = menu.addAction("▶ Move Right")
        del_act = menu.addAction("🗑️ Delete Frame")

        action = menu.exec_(source_widget.mapToGlobal(pos)) if hasattr(menu, "exec_") else menu.exec(source_widget.mapToGlobal(pos))
        if action == rename_act:
            self.on_rename_frame(card_idx)
        elif action == dup_act:
            self.doc.select_frame(card_idx)
            self.on_duplicate_frame()
        elif action == left_act:
            self.doc.select_frame(card_idx)
            self.on_move_left()
        elif action == right_act:
            self.doc.select_frame(card_idx)
            self.on_move_right()
        elif action == del_act:
            self.doc.select_frame(card_idx)
            self.on_delete_frame()

    def refresh_timeline(self, rebuild: bool = True) -> None:
        """Updates frame strip cards. If rebuild=False and card count matches, updates in-place for O(1) speed."""
        frames_cnt = len(self.doc.frames)
        self.counter_label.setText(f"Frame {self.doc.active_frame_index + 1} / {frames_cnt}")

        if not rebuild and len(self._cards) == frames_cnt:
            for idx, card in enumerate(self._cards):
                card.set_active(idx == self.doc.active_frame_index)
            return

        # Clear existing widgets
        while self.strip_layout.count():
            item = self.strip_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._cards.clear()

        # Update Mirror button visibility/enabled state based on .R or .L suffix
        anim_name = self.doc.active_animation.name.strip() if self.doc and self.doc.active_animation else ""
        has_lr = anim_name.upper().endswith(".R") or anim_name.upper().endswith(".L")
        self.mirror_anim_btn.setEnabled(has_lr)

        self.del_btn.setEnabled(frames_cnt > 1)

        if self.doc and self.doc.active_animation:
            self.fps_spin.blockSignals(True)
            self.fps_spin.setValue(self.doc.fps)
            self.fps_spin.blockSignals(False)

        anim_idx = self.doc.active_animation_index
        for i in range(frames_cnt):
            cache_key = (anim_idx, i)
            if cache_key in self._thumb_cache:
                thumb = self._thumb_cache[cache_key]
            else:
                thumb = self.doc.render_frame_qimage(i)
                self._thumb_cache[cache_key] = thumb

            card = FrameCardWidget(
                index=i,
                frame_name=self.doc.frames[i].name,
                thumbnail=thumb,
                is_active=(i == self.doc.active_frame_index),
                parent=self.strip_widget,
            )
            card.rename_requested.connect(self.on_rename_frame)
            card.setContextMenuPolicy(Qt.CustomContextMenu)
            card.customContextMenuRequested.connect(lambda pos, idx=i, c=card: self._on_card_context_menu(idx, pos, c))
            card.mousePressEvent = lambda evt, idx=i: self.on_select_frame(idx)
            self._cards.append(card)
            self.strip_layout.addWidget(card)

    def on_select_frame(self, index: int) -> None:
        if self.doc.select_frame(index):
            self.refresh_timeline(rebuild=False)
            self.active_frame_changed.emit()

    def on_prev_frame(self) -> None:
        if self.doc and len(self.doc.frames) > 0:
            prev_idx = (self.doc.active_frame_index - 1) % len(self.doc.frames)
            self.on_select_frame(prev_idx)

    def on_next_frame(self) -> None:
        if self.doc and len(self.doc.frames) > 0:
            next_idx = (self.doc.active_frame_index + 1) % len(self.doc.frames)
            self.on_select_frame(next_idx)

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
        was_playing = self.is_playing
        self.is_playing = False
        self.play_btn.setText("▶ Play")
        self.play_timer.stop()
        if was_playing:
            self.active_frame_changed.emit()

    def stop_playback(self) -> None:
        self.pause_playback()
        self.doc.select_frame(0)
        self.refresh_timeline(rebuild=False)
        self.active_frame_changed.emit()

    def _on_play_step(self) -> None:
        if not self.doc or len(self.doc.frames) <= 1:
            return
        next_idx = (self.doc.active_frame_index + 1) % len(self.doc.frames)
        self.doc.select_frame(next_idx)
        self.refresh_timeline(rebuild=False)
        self.playback_frame_changed.emit(next_idx)

    def on_fps_changed(self, fps: int) -> None:
        self.doc.fps = fps
        if self.is_playing:
            interval = max(10, 1000 // max(1, self.doc.fps))
            self.play_timer.setInterval(interval)
        self.animation_visual_changed.emit()

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
        if self.doc.delete_frame(self.doc.active_frame_index):
            self.refresh_timeline()
            self.frame_structure_changed.emit()
            self.active_frame_changed.emit()

    def on_move_left(self) -> None:
        if self.doc.move_frame_left(self.doc.active_frame_index):
            self.refresh_timeline()
            self.frame_structure_changed.emit()
            self.active_frame_changed.emit()

    def on_move_right(self) -> None:
        if self.doc.move_frame_right(self.doc.active_frame_index):
            self.refresh_timeline()
            self.frame_structure_changed.emit()
            self.active_frame_changed.emit()

