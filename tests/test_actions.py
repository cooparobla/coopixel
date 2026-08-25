"""
Tests for Actions Panel and recorded action history in Coopixel.
"""

import os
import tempfile
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from coopixel.ui.actions_panel import ActionRecord, ActionsPanel
from coopixel.ui.dialogs import ImportImageDialog
from coopixel.ui.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_import_image_dialog_default_setting(qapp, tmp_path):
    """Verify ImportImageDialog defaults resize_canvas to False."""
    img_path = str(tmp_path / "test_import.png")
    test_img = QImage(32, 32, QImage.Format_ARGB32)
    test_img.fill(QColor(255, 0, 0, 255))
    test_img.save(img_path)

    dlg = ImportImageDialog(
        filepath=img_path,
        img_width=32,
        img_height=32,
        canvas_width=16,
        canvas_height=16,
    )
    name, resize_canvas, scale_to_canvas = dlg.get_values()
    assert name == "test_import"
    assert resize_canvas is False
    assert scale_to_canvas is False
    dlg.close()


def test_actions_panel_queue_limit(qapp):
    """Verify ActionsPanel maintains a maximum of 10 items."""
    panel = ActionsPanel()

    for i in range(15):
        panel.record_action(
            action_type="crop_canvas",
            params={"x": 0, "y": 0, "width": i + 1, "height": i + 1},
            display_name=f"Crop Canvas {i+1}",
            details=f"Bounds: {i+1}x{i+1}",
        )

    assert len(panel.actions) == 10
    assert panel.list_widget.count() == 10
    assert panel.actions[0].display_name == "Crop Canvas 6"
    assert panel.actions[-1].display_name == "Crop Canvas 15"


def test_actions_panel_run_signal(qapp):
    """Verify selecting an action and clicking Run emits run_action_requested."""
    panel = ActionsPanel()
    received = []
    panel.run_action_requested.connect(lambda rec: received.append(rec))

    rec = panel.record_action(
        action_type="crop_layer",
        params={},
        display_name="Crop Layer",
        details="Crop active layer",
    )

    panel.list_widget.setCurrentRow(0)
    assert panel.run_btn.isEnabled()
    panel.run_btn.click()

    assert len(received) == 1
    assert received[0] == rec


def test_mainwindow_action_recording_and_rerun(qapp, tmp_path):
    """Verify MainWindow records crop canvas, crop layer, and image import actions and can re-run them."""
    mw = MainWindow()
    mw.show()

    # 1. Test crop canvas recording
    mw.on_crop_committed(0, 0, 20, 20)
    assert len(mw.actions_panel.actions) == 1
    last_act = mw.actions_panel.actions[-1]
    assert last_act.action_type == "crop_canvas"
    assert last_act.params == {"x": 0, "y": 0, "width": 20, "height": 20}
    assert mw.doc.width == 20
    assert mw.doc.height == 20

    # 2. Test crop layer recording
    mw.layer_panel.on_crop_layer_to_canvas()
    assert len(mw.actions_panel.actions) == 2
    last_act = mw.actions_panel.actions[-1]
    assert last_act.action_type == "crop_layer"

    # 3. Test import layer recording & rerun
    img_path = str(tmp_path / "action_layer.png")
    img = QImage(10, 10, QImage.Format_ARGB32)
    img.fill(QColor(0, 0, 255, 255))
    img.save(img_path)

    # Record synthetic import action
    import_rec = mw.actions_panel.record_action(
        action_type="import_layer",
        params={
            "filepath": img_path,
            "filetype": "PNG",
            "layer_name": "ActionImported",
            "resize_canvas": False,
            "scale_to_canvas": False,
        },
        display_name="Import Image (action_layer.png)",
        details="Format: PNG | Layer: 'ActionImported'",
    )

    initial_layer_count = len(mw.doc.layers)
    mw.on_run_action(import_rec)
    assert len(mw.doc.layers) == initial_layer_count + 1
    assert mw.doc.active_layer.name == "ActionImported"

    # 4. Test rerun crop canvas
    crop_rec = ActionRecord(
        action_type="crop_canvas",
        display_name="Crop Canvas",
        details="Bounds: 15x15",
        params={"x": 0, "y": 0, "width": 15, "height": 15},
    )
    mw.on_run_action(crop_rec)
    assert mw.doc.width == 15
    assert mw.doc.height == 15

    mw.close()
