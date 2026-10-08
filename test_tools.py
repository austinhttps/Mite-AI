"""Unit tests for the Local AI Desktop Assistant tools and cache manager."""

import datetime
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.habits import (
    track_habit,
    get_habit_stats,
    list_habits,
    _compute_streaks,
    _load_habits,
    _save_habits,
    DEFAULT_HABITS_FILE,
)
from tools.notes import (
    append_note,
    read_notes,
    list_note_categories,
    DEFAULT_NOTES_FILE,
)
from cache_manager import (
    find_cached_models,
    get_default_cache_dirs,
    resolve_model_path,
)


class TestHabitTracker(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_habits_file = Path(self.test_dir) / "test_habits.json"
        
        # Patch the file path in tools.habits temporarily
        import tools.habits
        self.original_file = tools.habits.DEFAULT_HABITS_FILE
        tools.habits.DEFAULT_HABITS_FILE = self.test_habits_file

    def tearDown(self):
        import tools.habits
        tools.habits.DEFAULT_HABITS_FILE = self.original_file
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_track_habit_single(self):
        msg = track_habit("Morning Jog", status="completed", metric_value=5.0, metric_unit="km")
        self.assertIn("Morning Jog", msg)
        self.assertIn("completed", msg)
        self.assertIn("5.0 km", msg)
        self.assertIn("Current Streak: 1 day(s)", msg)

    def test_streak_calculation(self):
        today = datetime.date.today()
        d1 = (today - datetime.timedelta(days=2)).isoformat()
        d2 = (today - datetime.timedelta(days=1)).isoformat()
        d3 = today.isoformat()

        track_habit("Reading", status="completed", date=d1)
        track_habit("Reading", status="completed", date=d2)
        msg = track_habit("Reading", status="completed", date=d3)

        self.assertIn("Current Streak: 3 day(s)", msg)
        self.assertIn("Best Streak: 3 day(s)", msg)

    def test_get_habit_stats_and_list(self):
        track_habit("Meditation", status="completed", notes="10 min mindfulness")
        stats = get_habit_stats("Meditation", days=7)
        self.assertIn("Meditation", stats)
        self.assertIn("10 min mindfulness", stats)

        listing = list_habits()
        self.assertIn("Meditation", listing)
        self.assertIn("Done", listing)


class TestNoteTaker(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_notes_file = Path(self.test_dir) / "test_notes.md"
        
        import tools.notes
        self.original_notes_file = tools.notes.DEFAULT_NOTES_FILE
        tools.notes.DEFAULT_NOTES_FILE = self.test_notes_file

    def tearDown(self):
        import tools.notes
        tools.notes.DEFAULT_NOTES_FILE = self.original_notes_file
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_append_and_read_note(self):
        msg = append_note("Remember to buy coffee beans", category="Todo", title="Groceries")
        self.assertIn("Note successfully appended", msg)
        self.assertIn("Todo", msg)

        read_res = read_notes(category="Todo")
        self.assertIn("Groceries", read_res)
        self.assertIn("Remember to buy coffee beans", read_res)

    def test_filter_and_search_notes(self):
        append_note("Idea 1: Build local LLM agent", category="Ideas")
        append_note("Meeting with Alice regarding UI", category="Work")

        ideas = read_notes(category="Ideas")
        self.assertIn("Idea 1", ideas)
        self.assertNotIn("Meeting with Alice", ideas)

        work = read_notes(search_query="Alice")
        self.assertIn("Meeting with Alice", work)

        cats = list_note_categories()
        self.assertIn("Ideas", cats)
        self.assertIn("Work", cats)


class TestCacheManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.test_dir) / "models"
        self.cache_dir.mkdir()

        # Create a mock .litertlm file
        self.model_subdir = self.cache_dir / "gemma4-26b"
        self.model_subdir.mkdir()
        self.model_file = self.model_subdir / "model.litertlm"
        self.model_file.write_bytes(b"\x00" * 1024)  # 1 KB dummy

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_find_cached_models(self):
        models = find_cached_models([self.cache_dir])
        self.assertEqual(len(models), 1)
        self.assertEqual(models[0].name, "gemma4-26b")
        self.assertEqual(models[0].path, self.model_file.resolve())

    def test_resolve_model_path(self):
        resolved = resolve_model_path(custom_cache_dir=str(self.cache_dir))
        self.assertEqual(resolved, self.model_file.resolve())

        # Test preferred model name
        resolved_pref = resolve_model_path(
            preferred_model_name="gemma4",
            custom_cache_dir=str(self.cache_dir),
        )
        self.assertEqual(resolved_pref, self.model_file.resolve())


if __name__ == "__main__":
    unittest.main()
