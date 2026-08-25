"""
Pytest configuration for Coopixel unit tests.
Forces Qt to run in offscreen headless mode so no GUI windows launch on the desktop screen.
"""

import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"
