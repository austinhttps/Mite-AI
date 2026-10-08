"""Habit tracking tool module for the Private Local AI Desktop Assistant.

Maintains habit logs, status tracking, and streak analytics stored in a
private local JSON file on-device.
"""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Default path for habits database
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_HABITS_FILE = DATA_DIR / "habits.json"


def _ensure_data_file(file_path: Path = DEFAULT_HABITS_FILE) -> Path:
    """Ensure data directory and file exist."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if not file_path.exists():
        initial_data = {"version": "1.0", "habits": {}}
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, indent=2)
    return file_path


def _load_habits(file_path: Path = DEFAULT_HABITS_FILE) -> Dict[str, Any]:
    """Load habit data from disk."""
    _ensure_data_file(file_path)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"version": "1.0", "habits": {}}
            if "habits" not in data:
                data["habits"] = {}
            return data
    except (json.JSONDecodeError, OSError):
        return {"version": "1.0", "habits": {}}


def _save_habits(data: Dict[str, Any], file_path: Path = DEFAULT_HABITS_FILE) -> None:
    """Save habit data atomically to disk."""
    _ensure_data_file(file_path)
    temp_file = file_path.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    temp_file.replace(file_path)


def _compute_streaks(logs: Dict[str, Any], today_str: Optional[str] = None) -> tuple[int, int]:
    """Compute (current_streak, longest_streak) in days for completed logs."""
    if not logs:
        return 0, 0

    if today_str is None:
        today_str = datetime.date.today().isoformat()

    today_date = datetime.date.fromisoformat(today_str)

    # Extract all dates where status is completed
    completed_dates = set()
    for d_str, entry in logs.items():
        if entry.get("status") == "completed":
            try:
                completed_dates.add(datetime.date.fromisoformat(d_str))
            except ValueError:
                continue

    if not completed_dates:
        return 0, 0

    sorted_dates = sorted(completed_dates)

    # Calculate longest streak across all history
    longest_streak = 0
    curr_run = 0
    prev_date = None

    for d in sorted_dates:
        if prev_date is None or d == prev_date + datetime.timedelta(days=1):
            curr_run += 1
        elif d > prev_date + datetime.timedelta(days=1):
            curr_run = 1
        if curr_run > longest_streak:
            longest_streak = curr_run
        prev_date = d

    # Calculate current streak up to today or yesterday
    current_streak = 0
    check_date = today_date
    # If today is not completed, check if yesterday was completed to keep streak alive
    if check_date not in completed_dates:
        check_date = today_date - datetime.timedelta(days=1)

    while check_date in completed_dates:
        current_streak += 1
        check_date -= datetime.timedelta(days=1)

    return current_streak, longest_streak


def track_habit(
    habit_name: str,
    status: str = "completed",
    date: str = "",
    metric_value: float = 0.0,
    metric_unit: str = "",
    notes: str = "",
) -> str:
    """Records or updates daily habit execution and calculates current streaks.

    Use this tool whenever the user reports completing, starting, skipping, or
    logging progress on a daily habit (e.g., exercise, reading, meditation, coding).

    Args:
        habit_name: Name of the habit (e.g. 'Read 20 pages', 'Morning Workout', 'Drink Water').
        status: Execution status ('completed', 'skipped', 'in_progress', 'failed'). Defaults to 'completed'.
        date: Date in YYYY-MM-DD format. Leave empty or pass 'today' for the current date.
        metric_value: Optional numeric measure associated with the habit (e.g. 5.0 for 5km, 20 for pages).
        metric_unit: Unit for metric_value (e.g. 'km', 'pages', 'minutes', 'glasses').
        notes: Optional reflection, notes, or details about the habit execution.

    Returns:
        A human-readable confirmation message with updated streak statistics.
    """
    clean_name = habit_name.strip()
    if not clean_name:
        return "Error: Habit name cannot be empty."

    # Normalize date
    if not date or date.lower() == "today":
        target_date = datetime.date.today().isoformat()
    elif date.lower() == "yesterday":
        target_date = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    else:
        try:
            # Validate format
            target_date = datetime.date.fromisoformat(date.strip()).isoformat()
        except ValueError:
            target_date = datetime.date.today().isoformat()

    status = status.lower().strip()
    valid_statuses = {"completed", "skipped", "in_progress", "failed"}
    if status not in valid_statuses:
        status = "completed"

    data = _load_habits()
    habits = data.setdefault("habits", {})

    if clean_name not in habits:
        habits[clean_name] = {
            "created_at": datetime.date.today().isoformat(),
            "logs": {},
        }

    habit_entry = habits[clean_name]
    logs = habit_entry.setdefault("logs", {})

    log_record: Dict[str, Any] = {
        "status": status,
        "updated_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    if metric_value > 0:
        log_record["metric_value"] = metric_value
        log_record["metric_unit"] = metric_unit.strip()
    if notes.strip():
        log_record["notes"] = notes.strip()

    logs[target_date] = log_record
    _save_habits(data)

    current_streak, longest_streak = _compute_streaks(logs)

    metric_str = f" ({metric_value} {metric_unit.strip()})" if metric_value > 0 else ""
    notes_str = f" | Notes: '{notes.strip()}'" if notes.strip() else ""

    status_icon = "✅" if status == "completed" else "⏭️" if status == "skipped" else "⏳"
    return (
        f"{status_icon} Habit '{clean_name}' recorded as '{status}' for {target_date}{metric_str}{notes_str}. "
        f"🔥 Current Streak: {current_streak} day(s) | 🏆 Best Streak: {longest_streak} day(s)."
    )


def get_habit_stats(habit_name: str = "", days: int = 7) -> str:
    """Retrieves habit completion statistics, streaks, and history over the last N days.

    Args:
        habit_name: Optional specific habit name. If empty, provides stats for all tracked habits.
        days: Number of past days to inspect (default is 7 days).

    Returns:
        Formatted summary of habit performance, completion rate, streaks, and recent entries.
    """
    data = _load_habits()
    habits = data.get("habits", {})

    if not habits:
        return "No habits are currently being tracked. Log your first habit using track_habit!"

    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=days - 1)

    target_habits = {habit_name.strip(): habits[habit_name.strip()]} if habit_name.strip() in habits else habits

    if habit_name.strip() and habit_name.strip() not in habits:
        return f"Habit '{habit_name}' not found. Available habits: {', '.join(habits.keys())}"

    lines = [f"📊 Habit Performance Report (Past {days} Days: {start_date} to {today})"]
    lines.append("-" * 60)

    for name, habit_data in target_habits.items():
        logs = habit_data.get("logs", {})
        current_streak, longest_streak = _compute_streaks(logs)

        # Count completed in window
        completed_in_window = 0
        window_logs = []
        for d_offset in range(days):
            d = (start_date + datetime.timedelta(days=d_offset)).isoformat()
            if d in logs:
                entry = logs[d]
                st = entry.get("status", "unknown")
                if st == "completed":
                    completed_in_window += 1
                metric = f" ({entry['metric_value']} {entry.get('metric_unit', '')})" if "metric_value" in entry else ""
                note = f" - {entry['notes']}" if "notes" in entry else ""
                window_logs.append(f"  • {d}: {st.upper()}{metric}{note}")

        rate = (completed_in_window / days) * 100
        lines.append(f"🎯 **{name}**")
        lines.append(f"   • Current Streak: {current_streak} days | Longest: {longest_streak} days")
        lines.append(f"   • {days}-day completion: {completed_in_window}/{days} ({rate:.1f}%)")
        if window_logs:
            lines.append("   • Recent activity:")
            lines.extend(window_logs[-5:])  # Show last 5 entries
        else:
            lines.append("   • No activity recorded in this period.")
        lines.append("")

    return "\n".join(lines).strip()


def list_habits() -> str:
    """Lists all tracked habits with their current streak and today's status.

    Returns:
        A list of habits and their completion status for today.
    """
    data = _load_habits()
    habits = data.get("habits", {})

    if not habits:
        return "No habits registered yet."

    today = datetime.date.today().isoformat()
    lines = ["📋 **Your Tracked Daily Habits:**"]

    for name, habit_data in habits.items():
        logs = habit_data.get("logs", {})
        current_streak, _ = _compute_streaks(logs)
        today_log = logs.get(today)
        if today_log:
            today_status = f"✅ Done ({today_log.get('status')})"
        else:
            today_status = "⭕ Pending for today"
        lines.append(f"- **{name}**: {today_status} | Streak: {current_streak} days")

    return "\n".join(lines)
