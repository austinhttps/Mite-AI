"""Note appending and management tool module for the Private Local AI Desktop Assistant.

Maintains notes in a private local Markdown file on-device, formatted with
timestamps, categories, and titles.
"""

from __future__ import annotations

import datetime
from pathlib import Path
import re
from typing import List, Optional

# Default path for notes file
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_NOTES_FILE = DATA_DIR / "notes.md"


def _ensure_notes_file(file_path: Path = DEFAULT_NOTES_FILE) -> Path:
    """Ensure the notes file exists with a markdown header."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if not file_path.exists():
        header = (
            "# Private Local Desktop Assistant Notes\n\n"
            "> All notes stored locally and privately on-device.\n\n"
            "---\n\n"
        )
        file_path.write_text(header, encoding="utf-8")
    return file_path


def append_note(
    content: str,
    category: str = "General",
    title: str = "",
    timestamp: bool = True,
) -> str:
    """Appends a new note, thought, todo, or reminder to the local markdown file.

    Use this tool whenever the user asks to save a note, record an idea, jot down
    a thought, save a task, or append information to their local notebook.

    Args:
        content: The text content of the note. Can be multiline or bullet points.
        category: A category or tag for the note (e.g., 'Work', 'Ideas', 'Todo', 'Personal', 'Meeting', 'General').
        title: An optional brief title or headline for the note.
        timestamp: Whether to prefix the note with the current timestamp (defaults to True).

    Returns:
        A confirmation message indicating that the note was safely appended to the local file.
    """
    clean_content = content.strip()
    if not clean_content:
        return "Error: Note content cannot be empty."

    category_clean = category.strip().capitalize() if category.strip() else "General"
    title_clean = title.strip()

    file_path = _ensure_notes_file()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    entry_parts = []
    if timestamp:
        header_title = f": {title_clean}" if title_clean else ""
        entry_parts.append(f"### [{now_str}] [{category_clean}]{header_title}")
    elif title_clean:
        entry_parts.append(f"### [{category_clean}] {title_clean}")
    else:
        entry_parts.append(f"### [{category_clean}]")

    entry_parts.append("")
    entry_parts.append(clean_content)
    entry_parts.append("")
    entry_parts.append("---")
    entry_parts.append("")

    formatted_entry = "\n".join(entry_parts)

    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(formatted_entry)
        
        preview = clean_content[:60] + ("..." if len(clean_content) > 60 else "")
        return (
            f"📝 Note successfully appended to local file '{file_path.name}' under [{category_clean}]:\n"
            f"   Preview: \"{preview}\""
        )
    except OSError as e:
        return f"Error appending note to disk: {e}"


def read_notes(
    category: str = "",
    limit: int = 5,
    search_query: str = "",
) -> str:
    """Reads recent notes from the local markdown notebook.

    Args:
        category: Optional category filter (e.g. 'Work', 'Ideas', 'Todo'). If omitted, reads all categories.
        limit: Maximum number of recent notes to return (default is 5).
        search_query: Optional keyword or phrase to search for within note contents.

    Returns:
        The matched notes formatted for reading, or a message if no notes were found.
    """
    file_path = _ensure_notes_file()
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except OSError as e:
        return f"Error reading notes file: {e}"

    # Split notes by horizontal rule separator
    raw_entries = [entry.strip() for entry in raw_text.split("---") if entry.strip()]

    # Skip top-level header entry
    parsed_entries = []
    for entry in raw_entries:
        if entry.startswith("# Private Local Desktop Assistant Notes"):
            continue
        parsed_entries.append(entry)

    if not parsed_entries:
        return "Your notebook is currently empty. Use append_note to save your first note!"

    # Filter by category and search query
    filtered = []
    cat_lower = category.strip().lower()
    query_lower = search_query.strip().lower()

    for entry in reversed(parsed_entries):  # Most recent first
        match_cat = True
        match_query = True

        if cat_lower:
            match_cat = f"[{cat_lower}]" in entry.lower()

        if query_lower:
            match_query = query_lower in entry.lower()

        if match_cat and match_query:
            filtered.append(entry)
            if len(filtered) >= limit:
                break

    if not filtered:
        criteria = []
        if category:
            criteria.append(f"category '{category}'")
        if search_query:
            criteria.append(f"query '{search_query}'")
        criteria_str = " and ".join(criteria)
        return f"No notes found matching {criteria_str}."

    result = [f"📖 Showing {len(filtered)} recent note(s) from local notebook:"]
    result.append("=" * 60)
    for entry in filtered:
        result.append(entry)
        result.append("-" * 40)

    return "\n".join(result).strip()


def list_note_categories() -> str:
    """Discovers all unique note categories recorded in the local notebook.

    Returns:
        A list of active note categories.
    """
    file_path = _ensure_notes_file()
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except OSError as e:
        return f"Error reading notes file: {e}"

    # Match [Category: ...] or [CategoryName] in headers
    categories = set(re.findall(r"###\s*\[[^\]]+\]\s*\[([^\]]+)\]", raw_text))
    # Also fallback for simple ### [Category]
    simple_cats = set(re.findall(r"###\s*\[([A-Za-z0-9_-]+)\]", raw_text))
    all_cats = sorted(categories.union(simple_cats))

    if not all_cats:
        return "No categorized notes found yet."

    return "🏷️ **Active Note Categories:** " + ", ".join(f"`{c}`" for c in all_cats)
