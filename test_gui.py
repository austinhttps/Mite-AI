"""Unit tests for the Desktop Assistant PyQt6 GUI."""

import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# Automatically ensure execution inside project's .venv if launched via global python
_venv_python = (PROJECT_ROOT / ".venv" / "Scripts" / "python.exe") if sys.platform == "win32" else (PROJECT_ROOT / ".venv" / "bin" / "python")
if _venv_python.exists():
    try:
        if Path(sys.executable).resolve() != _venv_python.resolve():
            import subprocess
            sys.exit(subprocess.call([str(_venv_python), *sys.argv]))
    except Exception:
        pass

from PyQt6.QtWidgets import QApplication
from gui_assistant import DesktopAssistantMainWindow

# Ensure single QApplication instance
app = QApplication.instance() or QApplication([])


class TestAssistantGUI(unittest.TestCase):
    def setUp(self):
        self.window = DesktopAssistantMainWindow(test_mode=True)

    def tearDown(self):
        self.window.close()

    def test_window_initialization(self):
        self.assertEqual(self.window.windowTitle(), "Private Local AI Desktop Assistant")
        self.assertEqual(self.window.tab_widget.count(), 4)
        tab_names = [self.window.tab_widget.tabText(i) for i in range(4)]
        self.assertIn("💬 AI Chat", tab_names)
        self.assertIn("🎯 Habit Tracker", tab_names)
        self.assertIn("📝 Notes Notebook", tab_names)
        self.assertIn("⚙️ Model & Cache", tab_names)

    def test_chat_tab_elements(self):
        self.assertIsNotNone(self.window.chat_browser)
        self.assertIsNotNone(self.window.input_field)
        self.assertIsNotNone(self.window.btn_send)
        self.assertIn("Welcome", self.window.chat_browser.toPlainText())

    def test_habit_tab_elements(self):
        self.assertIsNotNone(self.window.habit_input_name)
        self.assertIsNotNone(self.window.habits_container)

    def test_notes_tab_elements(self):
        self.assertIsNotNone(self.window.note_input_content)
        self.assertIsNotNone(self.window.notes_browser)


if __name__ == "__main__":
    unittest.main()
