"""Private Local AI Desktop Assistant - Native GUI.

Built with PyQt6, qasync, Google Antigravity SDK, and LiteRT.
Provides an interactive multi-tab desktop application for on-device AI chat,
visual habit tracking, and markdown note management.
"""

from __future__ import annotations

import asyncio
import datetime
import os
import sys
from pathlib import Path
from typing import Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Automatically ensure execution inside project's .venv if launched via global python
_venv_python = (PROJECT_ROOT / ".venv" / "Scripts" / "python.exe") if sys.platform == "win32" else (PROJECT_ROOT / ".venv" / "bin" / "python")
if _venv_python.exists():
    try:
        if Path(sys.executable).resolve() != _venv_python.resolve():
            import subprocess
            sys.exit(subprocess.call([str(_venv_python), *sys.argv]))
    except Exception:
        pass

# Safe Windows encoding
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from PyQt6.QtCore import QSize, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QFont, QIcon, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
import qasync

from cache_manager import (
    CachedModel,
    find_cached_models,
    get_default_cache_dirs,
    get_import_instructions,
    resolve_model_path,
)
from tools.habits import (
    _compute_streaks,
    _load_habits,
    get_habit_stats,
    list_habits,
    track_habit,
)
from tools.notes import (
    _ensure_notes_file,
    append_note,
    list_note_categories,
    read_notes,
)

# Antigravity SDK imports
try:
    from google.antigravity import Agent, LiteRTAgentConfig
    from google.antigravity.hooks import policy
    AGY_AVAILABLE = True
except ImportError:
    AGY_AVAILABLE = False


DARK_THEME_QSS = """
QMainWindow, QWidget {
    background-color: #0b0f19;
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #1e293b;
    background-color: #0f172a;
    border-radius: 8px;
    top: -1px;
}

QTabBar::tab {
    background: #0b0f19;
    color: #94a3b8;
    padding: 10px 20px;
    font-weight: 600;
    font-size: 13px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    border: 1px solid transparent;
    margin-right: 4px;
}

QTabBar::tab:selected {
    background: #0f172a;
    color: #818cf8;
    border: 1px solid #1e293b;
    border-bottom: 2px solid #6366f1;
}

QTabBar::tab:hover:!selected {
    color: #f1f5f9;
    background: #131d31;
}

QFrame.card {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 12px;
}

QLineEdit, QTextEdit, QComboBox, QDateEdit, QDoubleSpinBox {
    background-color: #0f172a;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 10px;
    selection-background-color: #6366f1;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus, QDoubleSpinBox:focus {
    border: 1px solid #818cf8;
}

QPushButton.primary-btn {
    background-color: #6366f1;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton.primary-btn:hover {
    background-color: #4f46e5;
}

QPushButton.primary-btn:pressed {
    background-color: #4338ca;
}

QPushButton.secondary-btn {
    background-color: #1e293b;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 500;
}

QPushButton.secondary-btn:hover {
    background-color: #334155;
    color: #ffffff;
}

QPushButton.pill-btn {
    background-color: #1e293b;
    color: #cbd5e1;
    border: 1px solid #475569;
    border-radius: 12px;
    padding: 4px 10px;
    font-size: 11px;
}

QPushButton.pill-btn:hover {
    background-color: #334155;
    color: #818cf8;
    border-color: #818cf8;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    border: none;
    background: #0f172a;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #334155;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""


class DesktopAssistantMainWindow(QMainWindow):
    """Main window for the Private Local AI Desktop Assistant."""

    tools_updated_signal = pyqtSignal()

    def __init__(self, initial_model_path: Optional[Path] = None, test_mode: bool = False):
        super().__init__()
        self.setWindowTitle("Private Local AI Desktop Assistant")
        self.resize(1100, 780)
        self.setMinimumSize(900, 600)

        self.model_path: Optional[Path] = initial_model_path
        self.test_mode: bool = test_mode
        self.backend_str: str = "auto"
        self.agent_session: Optional[Agent] = None
        self.is_generating: bool = False

        # Detect active model if available
        if not self.model_path and not self.test_mode:
            self.model_path = resolve_model_path()
            if not self.model_path:
                self.test_mode = True  # Fallback to simulation mode if no weights found

        self._setup_ui()
        self._load_habits_dashboard()
        self._load_notes_list()
        self.tools_updated_signal.connect(self._on_tools_updated)

    def _setup_ui(self) -> None:
        """Constructs the application layout and tabs."""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 12, 16, 16)
        main_layout.setSpacing(12)

        # 1. Top Header Bar with Badges
        header_layout = QHBoxLayout()
        header_left = QVBoxLayout()
        title_label = QLabel("🤖 Private Local AI Desktop Assistant")
        title_label.setStyleSheet("font-size: 20px; font-weight: 700; color: #f8fafc;")
        subtitle_label = QLabel("Powered by Google Antigravity SDK & LiteRT • 100% On-Device & Offline")
        subtitle_label.setStyleSheet("font-size: 12px; color: #94a3b8;")
        header_left.addWidget(title_label)
        header_left.addWidget(subtitle_label)

        header_layout.addLayout(header_left)
        header_layout.addStretch()

        # Badges
        self.badge_privacy = QLabel("🔒 100% Offline")
        self.badge_privacy.setStyleSheet(
            "background-color: #064e3b; color: #34d399; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 11px;"
        )
        
        self.badge_model = QLabel()
        self._update_model_badge()

        header_layout.addWidget(self.badge_privacy)
        header_layout.addWidget(self.badge_model)
        main_layout.addLayout(header_layout)

        # 2. Main Tab Widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Create individual tabs
        self.tab_chat = QWidget()
        self.tab_habits = QWidget()
        self.tab_notes = QWidget()
        self.tab_settings = QWidget()

        self._build_chat_tab()
        self._build_habits_tab()
        self._build_notes_tab()
        self._build_settings_tab()

        self.tab_widget.addTab(self.tab_chat, "💬 AI Chat")
        self.tab_widget.addTab(self.tab_habits, "🎯 Habit Tracker")
        self.tab_widget.addTab(self.tab_notes, "📝 Notes Notebook")
        self.tab_widget.addTab(self.tab_settings, "⚙️ Model & Cache")

        # 3. Bottom Status Bar
        self.status_label = QLabel("Ready.")
        self.status_label.setStyleSheet("color: #64748b; font-size: 11px; padding: 2px 4px;")
        main_layout.addWidget(self.status_label)

    def _update_model_badge(self) -> None:
        """Updates the top right model indicator badge."""
        if self.test_mode or not self.model_path:
            self.badge_model.setText("🧪 Simulation Mode")
            self.badge_model.setStyleSheet(
                "background-color: #451a03; color: #fbbf24; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 11px;"
            )
        else:
            model_name = self.model_path.parent.name if self.model_path.name == "model.litertlm" else self.model_path.stem
            self.badge_model.setText(f"⚡ LiteRT: {model_name}")
            self.badge_model.setStyleSheet(
                "background-color: #312e81; color: #a5b4fc; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 11px;"
            )

    # --------------------------------------------------------------------------
    # TAB 1: AI CHAT
    # --------------------------------------------------------------------------
    def _build_chat_tab(self) -> None:
        layout = QVBoxLayout(self.tab_chat)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Quick Suggestion Pills
        pills_layout = QHBoxLayout()
        pills_layout.setSpacing(8)
        pills = [
            ("🏃 Log 5km Run", "I just finished a 5km run in 25 mins, record that!"),
            ("📖 Track Reading", "Log reading 20 pages completed today."),
            ("📊 Habit Summary", "Show me my habit summary and streaks."),
            ("💡 Note an Idea", "Save a note under Ideas: Local desktop AI automation pipeline"),
            ("📋 Recent Notes", "Show my recent notes."),
        ]
        pills_label = QLabel("Quick Actions:")
        pills_label.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600;")
        pills_layout.addWidget(pills_label)

        for label_text, prompt_text in pills:
            btn = QPushButton(label_text)
            btn.setProperty("class", "pill-btn")
            btn.clicked.connect(lambda _, p=prompt_text: self._send_quick_prompt(p))
            pills_layout.addWidget(btn)

        pills_layout.addStretch()
        layout.addLayout(pills_layout)

        # Chat Transcript Browser
        self.chat_browser = QTextBrowser()
        self.chat_browser.setOpenExternalLinks(True)
        self.chat_browser.setStyleSheet(
            "background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 8px; padding: 12px; font-size: 13px;"
        )
        layout.addWidget(self.chat_browser)

        # Initial Welcome Message
        welcome_html = (
            "<div style='margin-bottom: 16px; padding: 12px; background: #1e293b; border-radius: 8px; border-left: 4px solid #6366f1;'>"
            "<b style='color: #818cf8; font-size: 14px;'>🤖 Welcome to your Private Local AI Desktop Assistant!</b><br/>"
            "<span style='color: #cbd5e1;'>Everything runs entirely on-device with zero cloud telemetry. "
            "You can talk to me, log your daily habits (exercise, water, reading, coding), or append private thoughts and notes.</span>"
            "</div>"
        )
        self.chat_browser.setHtml(welcome_html)

        # Input Row
        input_container = QFrame()
        input_container.setStyleSheet("background-color: #0f172a; border-radius: 8px; border: 1px solid #334155;")
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(8, 6, 8, 6)
        input_layout.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask your assistant, log a habit, or save a note (e.g. 'I drank 8 glasses of water today')...")
        self.input_field.setStyleSheet("border: none; background: transparent; font-size: 13px; color: #f8fafc;")
        self.input_field.returnPressed.connect(self._on_send_clicked)
        input_layout.addWidget(self.input_field)

        self.btn_send = QPushButton("Send")
        self.btn_send.setProperty("class", "primary-btn")
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.clicked.connect(self._on_send_clicked)
        input_layout.addWidget(self.btn_send)

        layout.addWidget(input_container)

    def _append_chat_message(self, role: str, text: str) -> None:
        """Appends a styled bubble to the chat transcript."""
        if role == "user":
            bubble_html = (
                f"<div style='margin: 12px 0; text-align: right;'>"
                f"<div style='display: inline-block; background-color: #4f46e5; color: #ffffff; padding: 10px 14px; border-radius: 12px; max-width: 75%; text-align: left;'>"
                f"<b>You:</b><br/>{text}"
                f"</div></div>"
            )
        else:
            bubble_html = (
                f"<div style='margin: 12px 0; text-align: left;'>"
                f"<div style='display: inline-block; background-color: #1e293b; color: #f1f5f9; border: 1px solid #334155; padding: 10px 14px; border-radius: 12px; max-width: 85%;'>"
                f"<b style='color: #818cf8;'>Assistant:</b><br/>{text}"
                f"</div></div>"
            )
        self.chat_browser.append(bubble_html)
        self.chat_browser.moveCursor(QTextCursor.MoveOperation.End)

    def _send_quick_prompt(self, prompt: str) -> None:
        self.input_field.setText(prompt)
        self._on_send_clicked()

    def _on_send_clicked(self) -> None:
        text = self.input_field.text().strip()
        if not text or self.is_generating:
            return

        self.input_field.clear()
        self._append_chat_message("user", text)
        asyncio.create_task(self._process_user_message(text))

    async def _process_user_message(self, text: str) -> None:
        """Executes the prompt via Antigravity SDK or local tool dispatcher."""
        self.is_generating = True
        self.btn_send.setEnabled(False)
        self.status_label.setText("Processing with local assistant...")

        lower = text.lower()
        tool_executed = False

        # In Simulation Mode or if model weight is not loaded, direct tool dispatch:
        if self.test_mode or not self.model_path or not AGY_AVAILABLE:
            await asyncio.sleep(0.1)  # Yield to event loop

            if any(k in lower for k in ["habit", "run", "jog", "workout", "water", "read", "streak", "gym", "meditat"]):
                if any(q in lower for q in ["stat", "how", "report", "summary", "look"]):
                    res = get_habit_stats(days=7)
                elif any(q in lower for q in ["list", "what", "which"]):
                    res = list_habits()
                else:
                    # Parse habit name from prompt
                    habit_name = text
                    for prefix in ["i finished", "i ran", "i did", "log", "track", "i just"]:
                        if lower.startswith(prefix):
                            habit_name = text[len(prefix):].strip()
                            break
                    res = track_habit(habit_name=habit_name, status="completed", notes="Logged via Desktop GUI")
                    tool_executed = True

                self._append_chat_message("assistant", res)
            elif any(k in lower for k in ["note", "idea", "todo", "remember", "write down"]):
                if any(q in lower for q in ["read", "show", "recent", "find", "list"]):
                    res = read_notes(limit=5)
                else:
                    content = text
                    for prefix in ["note down", "save note", "save a note", "note:", "remember to", "idea:"]:
                        if lower.startswith(prefix):
                            content = text[len(prefix):].strip()
                            break
                    res = append_note(content=content, category="General", title="Desktop Note")
                    tool_executed = True

                self._append_chat_message("assistant", res)
            else:
                sim_reply = (
                    f"Received: \"{text}\".<br/>"
                    f"<i>(Operating in test simulation mode. When a .litertlm model is loaded, "
                    f"the on-device Gemma engine generates multi-turn natural language reasoning and tool calling.)</i>"
                )
                self._append_chat_message("assistant", sim_reply)
        else:
            # Full LiteRT On-Device Agent Chat
            try:
                if self.agent_session is None:
                    # Lazy init agent
                    config = LiteRTAgentConfig(
                        model_path=str(self.model_path),
                        backend="cpu" if self.backend_str == "cpu" else "gpu",
                        tools=[track_habit, get_habit_stats, list_habits, append_note, read_notes, list_note_categories],
                        policies=[policy.allow_all()],
                    )
                    self.agent_session = Agent(config=config)
                    await self.agent_session.__aenter__()

                response = await self.agent_session.chat(text)
                accumulated_text = ""
                # Stream tokens
                async for chunk in response:
                    accumulated_text += chunk
                    # Small yield for smooth UI update
                    await asyncio.sleep(0.001)

                self._append_chat_message("assistant", accumulated_text)
                tool_executed = True
            except Exception as e:
                self._append_chat_message("assistant", f"⚠️ Error during on-device execution: {e}")

        self.is_generating = False
        self.btn_send.setEnabled(True)
        self.status_label.setText("Ready.")

        if tool_executed:
            self.tools_updated_signal.emit()

    # --------------------------------------------------------------------------
    # TAB 2: HABIT TRACKER
    # --------------------------------------------------------------------------
    def _build_habits_tab(self) -> None:
        layout = QHBoxLayout(self.tab_habits)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Left Column: Habit Logging Form
        left_card = QFrame()
        left_card.setProperty("class", "card")
        left_card.setFixedWidth(360)
        left_layout = QVBoxLayout(left_card)
        left_layout.setSpacing(12)

        form_title = QLabel("🎯 Log Daily Habit")
        form_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #f8fafc;")
        left_layout.addWidget(form_title)

        left_layout.addWidget(QLabel("Habit Name:"))
        self.habit_input_name = QLineEdit()
        self.habit_input_name.setPlaceholderText("e.g., Morning Workout, Read 20 pages")
        left_layout.addWidget(self.habit_input_name)

        left_layout.addWidget(QLabel("Status:"))
        self.habit_input_status = QComboBox()
        self.habit_input_status.addItems(["completed", "skipped", "in_progress", "failed"])
        left_layout.addWidget(self.habit_input_status)

        left_layout.addWidget(QLabel("Metric (Optional):"))
        metric_layout = QHBoxLayout()
        self.habit_input_metric_val = QDoubleSpinBox()
        self.habit_input_metric_val.setRange(0.0, 9999.0)
        self.habit_input_metric_val.setSingleStep(1.0)
        self.habit_input_metric_unit = QLineEdit()
        self.habit_input_metric_unit.setPlaceholderText("unit (km, pages, min)")
        metric_layout.addWidget(self.habit_input_metric_val)
        metric_layout.addWidget(self.habit_input_metric_unit)
        left_layout.addLayout(metric_layout)

        left_layout.addWidget(QLabel("Date:"))
        self.habit_input_date = QDateEdit()
        self.habit_input_date.setCalendarPopup(True)
        self.habit_input_date.setDate(datetime.date.today())
        left_layout.addWidget(self.habit_input_date)

        left_layout.addWidget(QLabel("Reflection / Notes:"))
        self.habit_input_notes = QLineEdit()
        self.habit_input_notes.setPlaceholderText("e.g., Felt energetic, completed outdoors")
        left_layout.addWidget(self.habit_input_notes)

        btn_log_habit = QPushButton("Save Habit Entry")
        btn_log_habit.setProperty("class", "primary-btn")
        btn_log_habit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_log_habit.clicked.connect(self._on_log_habit_form)
        left_layout.addWidget(btn_log_habit)

        left_layout.addStretch()
        layout.addWidget(left_card)

        # Right Column: Visual Dashboard & Cards
        right_card = QFrame()
        right_card.setProperty("class", "card")
        right_layout = QVBoxLayout(right_card)
        right_layout.setSpacing(12)

        dash_header = QHBoxLayout()
        dash_title = QLabel("📊 Active Habit Streaks & Analytics")
        dash_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #f8fafc;")
        btn_refresh_habits = QPushButton("🔄 Refresh")
        btn_refresh_habits.setProperty("class", "secondary-btn")
        btn_refresh_habits.clicked.connect(self._load_habits_dashboard)
        dash_header.addWidget(dash_title)
        dash_header.addStretch()
        dash_header.addWidget(btn_refresh_habits)
        right_layout.addLayout(dash_header)

        # Scrollable Habit Cards
        self.habits_scroll_area = QScrollArea()
        self.habits_scroll_area.setWidgetResizable(True)
        self.habits_container = QWidget()
        self.habits_list_layout = QVBoxLayout(self.habits_container)
        self.habits_list_layout.setSpacing(10)
        self.habits_scroll_area.setWidget(self.habits_container)
        right_layout.addWidget(self.habits_scroll_area)

        layout.addWidget(right_card)

    def _on_log_habit_form(self) -> None:
        name = self.habit_input_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Name", "Please enter a habit name.")
            return

        status = self.habit_input_status.currentText()
        metric_val = self.habit_input_metric_val.value()
        metric_unit = self.habit_input_metric_unit.text().strip()
        date_str = self.habit_input_date.date().toString("yyyy-MM-dd")
        notes = self.habit_input_notes.text().strip()

        track_habit(
            habit_name=name,
            status=status,
            date=date_str,
            metric_value=metric_val,
            metric_unit=metric_unit,
            notes=notes,
        )

        self.habit_input_name.clear()
        self.habit_input_notes.clear()
        self.habit_input_metric_val.setValue(0.0)
        self.habit_input_metric_unit.clear()

        self._load_habits_dashboard()
        self.status_label.setText(f"Habit '{name}' successfully logged for {date_str}.")

    def _load_habits_dashboard(self) -> None:
        """Populates the habit cards dynamically."""
        # Clear existing items
        while self.habits_list_layout.count():
            item = self.habits_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        data = _load_habits()
        habits = data.get("habits", {})

        if not habits:
            empty_lbl = QLabel("No habits logged yet. Use the form on the left or ask the AI to log one!")
            empty_lbl.setStyleSheet("color: #94a3b8; font-style: italic; padding: 20px;")
            self.habits_list_layout.addWidget(empty_lbl)
            self.habits_list_layout.addStretch()
            return

        today_str = datetime.date.today().isoformat()

        for name, h_data in habits.items():
            logs = h_data.get("logs", {})
            curr_streak, best_streak = _compute_streaks(logs)
            is_done_today = today_str in logs and logs[today_str].get("status") == "completed"

            card = QFrame()
            card.setStyleSheet(
                "background-color: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 10px;"
            )
            card_layout = QHBoxLayout(card)

            # Left side: Name & today status
            info_layout = QVBoxLayout()
            name_label = QLabel(name)
            name_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #f8fafc;")
            
            status_text = "✅ Completed Today" if is_done_today else "⭕ Pending for Today"
            status_color = "#34d399" if is_done_today else "#fbbf24"
            status_label = QLabel(status_text)
            status_label.setStyleSheet(f"color: {status_color}; font-size: 12px; font-weight: 500;")
            
            info_layout.addWidget(name_label)
            info_layout.addWidget(status_label)
            card_layout.addLayout(info_layout)
            card_layout.addStretch()

            # Right side: Streak Badges
            streak_layout = QHBoxLayout()
            streak_layout.setSpacing(8)

            streak_badge = QLabel(f"🔥 {curr_streak} Day Streak")
            streak_badge.setStyleSheet(
                "background-color: #431407; color: #fb923c; border: 1px solid #9a3412; "
                "padding: 5px 12px; border-radius: 12px; font-weight: 600; font-size: 12px;"
            )
            best_badge = QLabel(f"🏆 Best: {best_streak}d")
            best_badge.setStyleSheet(
                "background-color: #1e293b; color: #94a3b8; border: 1px solid #475569; "
                "padding: 5px 10px; border-radius: 12px; font-size: 11px;"
            )

            # Quick Complete button for today
            btn_quick_done = QPushButton("Mark Done")
            btn_quick_done.setProperty("class", "primary-btn")
            btn_quick_done.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_quick_done.clicked.connect(lambda _, n=name: self._quick_mark_habit_done(n))

            streak_layout.addWidget(streak_badge)
            streak_layout.addWidget(best_badge)
            streak_layout.addWidget(btn_quick_done)
            card_layout.addLayout(streak_layout)

            self.habits_list_layout.addWidget(card)

        self.habits_list_layout.addStretch()

    def _quick_mark_habit_done(self, habit_name: str) -> None:
        track_habit(habit_name=habit_name, status="completed")
        self._load_habits_dashboard()
        self.status_label.setText(f"Habit '{habit_name}' marked completed for today!")

    # --------------------------------------------------------------------------
    # TAB 3: NOTES NOTEBOOK
    # --------------------------------------------------------------------------
    def _build_notes_tab(self) -> None:
        layout = QHBoxLayout(self.tab_notes)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Left Column: Append Note Form
        left_card = QFrame()
        left_card.setProperty("class", "card")
        left_card.setFixedWidth(360)
        left_layout = QVBoxLayout(left_card)
        left_layout.setSpacing(12)

        form_title = QLabel("📝 Append New Note")
        form_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #f8fafc;")
        left_layout.addWidget(form_title)

        left_layout.addWidget(QLabel("Category / Tag:"))
        self.note_input_category = QComboBox()
        self.note_input_category.setEditable(True)
        self.note_input_category.addItems(["General", "Work", "Ideas", "Todo", "Meeting", "Personal"])
        left_layout.addWidget(self.note_input_category)

        left_layout.addWidget(QLabel("Title (Optional):"))
        self.note_input_title = QLineEdit()
        self.note_input_title.setPlaceholderText("e.g. Architecture brainstorm")
        left_layout.addWidget(self.note_input_title)

        left_layout.addWidget(QLabel("Note Content:"))
        self.note_input_content = QTextEdit()
        self.note_input_content.setPlaceholderText("Enter your markdown note, bullet points, or idea...")
        left_layout.addWidget(self.note_input_content)

        btn_save_note = QPushButton("Append to Notes (Markdown)")
        btn_save_note.setProperty("class", "primary-btn")
        btn_save_note.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save_note.clicked.connect(self._on_save_note_form)
        left_layout.addWidget(btn_save_note)

        layout.addWidget(left_card)

        # Right Column: Notes Explorer & Search
        right_card = QFrame()
        right_card.setProperty("class", "card")
        right_layout = QVBoxLayout(right_card)
        right_layout.setSpacing(12)

        search_bar = QHBoxLayout()
        self.notes_search_input = QLineEdit()
        self.notes_search_input.setPlaceholderText("🔍 Search notes by keyword...")
        self.notes_search_input.textChanged.connect(self._load_notes_list)

        self.notes_cat_filter = QComboBox()
        self.notes_cat_filter.addItem("All Categories")
        self.notes_cat_filter.currentTextChanged.connect(self._load_notes_list)

        btn_refresh_notes = QPushButton("🔄 Refresh")
        btn_refresh_notes.setProperty("class", "secondary-btn")
        btn_refresh_notes.clicked.connect(self._load_notes_list)

        search_bar.addWidget(self.notes_search_input)
        search_bar.addWidget(self.notes_cat_filter)
        search_bar.addWidget(btn_refresh_notes)
        right_layout.addLayout(search_bar)

        # Notes Browser Area
        self.notes_browser = QTextBrowser()
        self.notes_browser.setOpenExternalLinks(True)
        self.notes_browser.setStyleSheet(
            "background-color: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 12px; font-size: 13px;"
        )
        right_layout.addWidget(self.notes_browser)

        layout.addWidget(right_card)

    def _on_save_note_form(self) -> None:
        content = self.note_input_content.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "Empty Note", "Please enter note content.")
            return

        cat = self.note_input_category.currentText().strip() or "General"
        title = self.note_input_title.text().strip()

        append_note(content=content, category=cat, title=title)
        self.note_input_content.clear()
        self.note_input_title.clear()

        self._load_notes_list()
        self.status_label.setText(f"Note successfully saved under [{cat}].")

    def _load_notes_list(self) -> None:
        """Reloads the notes browser with entries parsed from notes.md."""
        file_path = _ensure_notes_file()
        try:
            raw_text = file_path.read_text(encoding="utf-8")
        except OSError:
            raw_text = ""

        # Update categories dropdown
        import re
        categories = sorted(set(re.findall(r"###\s*\[[^\]]+\]\s*\[([^\]]+)\]", raw_text)))
        curr_selected = self.notes_cat_filter.currentText()
        self.notes_cat_filter.blockSignals(True)
        self.notes_cat_filter.clear()
        self.notes_cat_filter.addItem("All Categories")
        for c in categories:
            self.notes_cat_filter.addItem(c)
        if curr_selected in categories:
            self.notes_cat_filter.setCurrentText(curr_selected)
        self.notes_cat_filter.blockSignals(False)

        # Filter entries
        filter_cat = self.notes_cat_filter.currentText()
        search_kw = self.notes_search_input.text().strip().lower()

        raw_entries = [e.strip() for e in raw_text.split("---") if e.strip()]
        display_html_parts = []

        for entry in reversed(raw_entries):
            if entry.startswith("# Private Local Desktop Assistant Notes"):
                continue

            if filter_cat != "All Categories" and f"[{filter_cat.lower()}]" not in entry.lower():
                continue
            if search_kw and search_kw not in entry.lower():
                continue

            # Convert markdown entry to clean HTML card
            lines = entry.splitlines()
            header_line = lines[0] if lines else ""
            body = "<br/>".join(lines[1:]).strip()

            card_html = (
                f"<div style='margin-bottom: 14px; padding: 12px; background: #1e293b; border-radius: 8px; border: 1px solid #334155;'>"
                f"<div style='color: #818cf8; font-weight: 700; font-size: 13px; margin-bottom: 6px;'>{header_line}</div>"
                f"<div style='color: #f1f5f9; font-size: 13px;'>{body}</div>"
                f"</div>"
            )
            display_html_parts.append(card_html)

        if not display_html_parts:
            self.notes_browser.setHtml(
                "<div style='color: #94a3b8; font-style: italic; padding: 16px;'>No notes match the current filter or search criteria.</div>"
            )
        else:
            self.notes_browser.setHtml("".join(display_html_parts))

    # --------------------------------------------------------------------------
    # TAB 4: MODEL & SETTINGS
    # --------------------------------------------------------------------------
    def _build_settings_tab(self) -> None:
        layout = QVBoxLayout(self.tab_settings)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Active Model Info Card
        info_card = QFrame()
        info_card.setProperty("class", "card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(8)

        info_title = QLabel("⚙️ Active LiteRT Model Configuration")
        info_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #f8fafc;")
        info_layout.addWidget(info_title)

        self.model_status_desc = QLabel()
        self._refresh_model_desc()
        info_layout.addWidget(self.model_status_desc)

        btn_row = QHBoxLayout()
        btn_pick_model = QPushButton("📁 Browse .litertlm File...")
        btn_pick_model.setProperty("class", "secondary-btn")
        btn_pick_model.clicked.connect(self._on_browse_model)

        btn_toggle_sim = QPushButton("🧪 Toggle Simulation Mode")
        btn_toggle_sim.setProperty("class", "secondary-btn")
        btn_toggle_sim.clicked.connect(self._on_toggle_sim)

        btn_row.addWidget(btn_pick_model)
        btn_row.addWidget(btn_toggle_sim)
        btn_row.addStretch()
        info_layout.addLayout(btn_row)

        layout.addWidget(info_card)

        # Detected Cache Explorer Card
        cache_card = QFrame()
        cache_card.setProperty("class", "card")
        cache_layout = QVBoxLayout(cache_card)
        cache_layout.setSpacing(8)

        cache_title = QLabel("🔍 Local LiteRT Model Cache Explorer")
        cache_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #f8fafc;")
        cache_layout.addWidget(cache_title)

        self.cache_list_browser = QTextBrowser()
        self.cache_list_browser.setStyleSheet(
            "background-color: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 10px; font-family: monospace;"
        )
        cache_layout.addWidget(self.cache_list_browser)

        btn_scan_cache = QPushButton("Scan Local Caches")
        btn_scan_cache.setProperty("class", "primary-btn")
        btn_scan_cache.clicked.connect(self._scan_and_render_cache)
        cache_layout.addWidget(btn_scan_cache)

        layout.addWidget(cache_card)
        self._scan_and_render_cache()

    def _refresh_model_desc(self) -> None:
        if self.test_mode or not self.model_path:
            desc = (
                "<b>Status:</b> Simulation / Test Mode Active.<br/>"
                "All custom habit and note tools are fully operational and testable directly in the UI.<br/>"
                "To run on-device LLM reasoning, import a model using the commands below."
            )
        else:
            desc = (
                f"<b>Model Path:</b> <code>{self.model_path}</code><br/>"
                f"<b>Engine:</b> Google LiteRT On-Device Runtime<br/>"
                f"<b>Backend:</b> {self.backend_str.upper()}<br/>"
                f"<b>SDK:</b> Google Antigravity SDK (LiteRTAgentConfig)"
            )
        self.model_status_desc.setText(desc)
        self._update_model_badge()

    def _on_browse_model(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select LiteRT Model Checkpoint",
            str(Path.home() / ".litert-lm" / "models"),
            "LiteRT Models (*.litertlm);;All Files (*)",
        )
        if file_path:
            self.model_path = Path(file_path).resolve()
            self.test_mode = False
            self._refresh_model_desc()
            self.status_label.setText(f"Active model set to: {self.model_path.name}")

    def _on_toggle_sim(self) -> None:
        self.test_mode = not self.test_mode
        self._refresh_model_desc()
        self.status_label.setText("Switched mode.")

    def _scan_and_render_cache(self) -> None:
        models = find_cached_models()
        if not models:
            instructions = get_import_instructions()
            self.cache_list_browser.setText(
                "No .litertlm models found in standard cache locations.\n\n" + instructions
            )
        else:
            lines = [f"Found {len(models)} model(s) in local LiteRT cache:\n"]
            for m in models:
                lines.append(f"• {m.name} ({m.size_gb:.2f} GB) - {m.path}")
            self.cache_list_browser.setText("\n".join(lines))

    @pyqtSlot()
    def _on_tools_updated(self) -> None:
        """Called whenever a tool alters habit or note data."""
        self._load_habits_dashboard()
        self._load_notes_list()


def launch_gui(initial_model_path: Optional[Path] = None, test_mode: bool = False) -> None:
    """Launches the PyQt6 GUI application with qasync event loop."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME_QSS)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    main_win = DesktopAssistantMainWindow(
        initial_model_path=initial_model_path,
        test_mode=test_mode,
    )
    main_win.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    launch_gui()
