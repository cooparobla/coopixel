"""
Actions Panel Widget for recording and re-running recent document actions in Coopixel.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


@dataclass
class ActionRecord:
    """Represents a recorded action that can be re-run on demand."""
    action_type: str  # "import_layer", "crop_canvas", "crop_layer"
    display_name: str
    details: str
    params: Dict[str, Any] = field(default_factory=dict)


class ActionsPanel(QDockWidget):
    """Dock panel widget for displaying action history log (up to 10) and re-running actions."""

    MAX_ACTIONS = 10

    # Signal emitted when user requests re-running an action
    run_action_requested = Signal(object)  # Emits ActionRecord

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Actions", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.actions: List[ActionRecord] = []

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # Header Info
        header_lbl = QLabel("Action History (Max 10)")
        header_lbl.setStyleSheet("color: #F97316; font-weight: bold; font-size: 11px;")
        main_layout.addWidget(header_lbl)

        sub_lbl = QLabel("Select an action and click 'Run Action' to repeat it.")
        sub_lbl.setStyleSheet("color: #94A3B8; font-size: 10px;")
        sub_lbl.setWordWrap(True)
        main_layout.addWidget(sub_lbl)

        # Action List Widget
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "QListWidget { background-color: #242424; border: 1px solid #333333; border-radius: 4px; padding: 2px; color: #F1F5F9; }"
            "QListWidget::item { padding: 6px; border-bottom: 1px solid #2D2D2D; border-radius: 3px; }"
            "QListWidget::item:hover { background-color: #332B25; }"
            "QListWidget::item:selected { background-color: #3F2D20; border: 1px solid #F97316; color: #F97316; font-weight: bold; }"
        )
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        main_layout.addWidget(self.list_widget, stretch=1)

        # Bottom Button Bar
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(6)

        self.run_btn = QPushButton("⚡ Run Action")
        self.run_btn.setToolTip("Re-run selected action with recorded preferences")
        self.run_btn.setStyleSheet(
            "QPushButton { background-color: #EA580C; color: #FFFFFF; font-weight: bold; border: 1px solid #F97316; border-radius: 4px; padding: 6px 10px; font-size: 11px; }"
            "QPushButton:hover { background-color: #F97316; }"
            "QPushButton:disabled { background-color: #282828; color: #64748B; border-color: #333333; }"
        )
        self.run_btn.setEnabled(False)
        self.run_btn.clicked.connect(self._on_run_clicked)

        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.setToolTip("Clear action history")
        self.clear_btn.setObjectName("secondaryButton")
        self.clear_btn.setStyleSheet(
            "QPushButton#secondaryButton { background-color: #282828; color: #94A3B8; border: 1px solid #333333; border-radius: 4px; padding: 6px 10px; font-size: 11px; }"
            "QPushButton#secondaryButton:hover { background-color: #333333; color: #F1F5F9; }"
        )
        self.clear_btn.clicked.connect(self.clear_actions)

        btn_bar.addWidget(self.run_btn, stretch=2)
        btn_bar.addWidget(self.clear_btn, stretch=1)
        main_layout.addLayout(btn_bar)

        self.setWidget(main_widget)

    def record_action(
        self, action_type: str, params: Dict[str, Any], display_name: str, details: str
    ) -> ActionRecord:
        """Records a new action into the history log (up to 10 max)."""
        rec = ActionRecord(
            action_type=action_type,
            display_name=display_name,
            details=details,
            params=params,
        )

        self.actions.append(rec)
        if len(self.actions) > self.MAX_ACTIONS:
            self.actions.pop(0)

        self._refresh_list_ui()

        # Select the newly recorded action
        if self.actions:
            self.list_widget.setCurrentRow(len(self.actions) - 1)

        return rec

    def clear_actions(self) -> None:
        """Clears all recorded actions."""
        self.actions.clear()
        self._refresh_list_ui()

    def _refresh_list_ui(self) -> None:
        self.list_widget.clear()
        for idx, rec in enumerate(self.actions, start=1):
            text = f"{idx}. {rec.display_name}\n   {rec.details}"
            item = QListWidgetItem(text)
            self.list_widget.addItem(item)
        self._on_selection_changed()

    def _on_selection_changed(self) -> None:
        row = self.list_widget.currentRow()
        self.run_btn.setEnabled(0 <= row < len(self.actions))

    def _on_run_clicked(self) -> None:
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.actions):
            self.run_action_requested.emit(self.actions[row])

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        self._on_run_clicked()
