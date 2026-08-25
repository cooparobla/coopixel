"""
Main entry point for Coopixel application.
Supports opening .pix / .caml files directly from command line arguments (e.g. `uv run coopixel example.pix`).
"""

import os
import sys
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from coopixel.ui.main_window import MainWindow
from coopixel.ui.theme import apply_dark_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Coopixel")
    app.setOrganizationName("Coopa")
    app.setDesktopFileName("coopixel")

    # Set application icon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Apply sleek dark palette & theme stylesheet
    apply_dark_theme(app)

    window = MainWindow()

    # Parse CLI positional arguments for input file path (e.g., `uv run coopixel example.pix`)
    cli_args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
    if cli_args:
        target_path = os.path.abspath(cli_args[0])
        window.open_file(target_path)

    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
