"""Custom Python tools for the Local AI Desktop Assistant."""

from .habits import track_habit, get_habit_stats, list_habits
from .notes import append_note, read_notes, list_note_categories

__all__ = [
    "track_habit",
    "get_habit_stats",
    "list_habits",
    "append_note",
    "read_notes",
    "list_note_categories",
]
