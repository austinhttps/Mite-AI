# 🤖 Private Local AI Desktop Assistant

An intelligent, completely private, and on-device local desktop assistant built using the **Google Antigravity SDK** and the **LiteRT** local execution engine.

---

## 🌟 Key Features

- **100% On-Device & Private**: Zero external API calls, zero telemetry, and no cloud dependencies. All model inference and data storage remain exclusively on your local machine.
- **Native Graphical User Interface (PyQt6 & qasync)**: A modern, dark-themed desktop window with 4 interactive tabs:
  - 💬 **AI Chat**: Interactive assistant dialogue with real-time token streaming, message bubbles, and quick action suggestion pills.
  - 🎯 **Habit Tracker**: Visual cards for active habits, streak badges (🔥 Current & 🏆 Best), one-click "Mark Done" buttons, and custom habit logging form.
  - 📝 **Notes Notebook**: Formatted Markdown notes viewer, live keyword search, category filter dropdown (`All`, `Work`, `Ideas`, `Todo`), and quick note append form.
  - ⚙️ **Model & Cache**: Local cache directory scanner, active model diagnostics, `.litertlm` file picker, and one-click import command reference.
- **Powered by Google Antigravity SDK**: Leverages `LiteRTAgentConfig` and `Agent` with native hardware acceleration, automatic context compaction, and seamless tool execution.
- **Automatic LiteRT Model Cache Discovery**: Automatically scans your standard LiteRT model cache (`~/.litert-lm/models`), custom environment paths (`LITERT_CACHE_DIR`, `LITERT_MODEL_PATH`), and local project folders for `.litertlm` model weights.
- **Daily Habit Tracking Tool**:
  - `track_habit`: Log completed, skipped, or in-progress habits with dates, metrics (e.g. 5 km, 20 pages), and notes.
  - Automatically calculates and updates **current streaks** and **longest streaks**.
  - Stores habit history persistently in [data/habits.json](file:///c:/Users/Austi/OneDrive/CodingProjects/AGY/Mite%20AI/data/habits.json).
  - `get_habit_stats` & `list_habits`: Provides statistical summaries and completion rates over customized time windows.
- **Local Markdown Note Appending Tool**:
  - `append_note`: Safely appends notes, thoughts, tasks, and ideas with timestamps, category tags (`[Work]`, `[Ideas]`, `[Todo]`, etc.), and titles.
  - Stores notes in human-readable Markdown format in [data/notes.md](file:///c:/Users/Austi/OneDrive/CodingProjects/AGY/Mite%20AI/data/notes.md).
  - `read_notes` & `list_note_categories`: Search and filter notes by category or keyword.
- **Interactive Execution Loop**:
  - Multi-turn conversational REPL with real-time token streaming.
  - Built-in slash command shortcuts:
    - `/habits` — Instant habit dashboard and streak report.
    - `/notes` — Instant preview of recent notes.
    - `/cache` — Live scan of detected `.litertlm` models.
    - `/model` — Active model diagnostics and backend status.
    - `/clear` — Clear console screen.
    - `/reset` — Reset conversation turn context.
    - `/exit` — Clean shutdown.

---

## 📁 Project Structure

```
Mite AI/
├── desktop_assistant.py  # Main assistant entry point and interactive execution loop
├── cache_manager.py      # LiteRT model cache scanner, resolver, and diagnostics
├── test_tools.py         # Complete unit tests for custom tools and cache resolver
├── requirements.txt      # Python dependencies
├── README.md             # Project documentation
├── tools/
│   ├── __init__.py       # Package exports
│   ├── habits.py         # Habit tracking tool implementation and streak engine
│   └── notes.py          # Note appending and query tool implementation
└── data/
    ├── habits.json       # Local persistent habit database (JSON)
    └── notes.md          # Local persistent notes notebook (Markdown)
```

---

## 🚀 Quick Start

### 1. Set Up Virtual Environment

This project utilizes a dedicated virtual environment with `google-antigravity` and `litert-lm`:

```bash
# Activate the existing virtual environment:
.venv\Scripts\activate   # Windows PowerShell / CMD
```

Or re-install using `uv` or `pip`:
```bash
pip install -r requirements.txt
```

---

### 2. Configure Your Local LiteRT Model Cache

The assistant automatically detects models cached in any of the following locations (checked in order):

1. Explicit CLI argument: `--model-path "C:/path/to/model.litertlm"`
2. Environment variable: `LITERT_MODEL_PATH`
3. Custom cache directory: `--cache-dir "C:/path/to/cache"` or `LITERT_CACHE_DIR`
4. Standard `litert-lm` cache: `~/.litert-lm/models/` (e.g., `C:\Users\<User>\.litert-lm\models\`)
5. Local workspace directory: `./models/`

#### Importing a Model into Cache

To download and register a model checkpoint into your LiteRT cache, use the `litert-lm` CLI:

- **Gemma 4 26B** (Recommended for workstations with 24GB+ VRAM or Unified Memory):
  ```bash
  litert-lm import \
    --from-huggingface-repo=litert-community/gemma-4-26B-A4B-it-litert-lm \
    gemma-4-26B-A4B-it-web.litertlm \
    gemma4-26b
  ```
  _Registers model at: `~/.litert-lm/models/gemma4-26b/model.litertlm`_

- **Gemma 2 2B / 9B** (Lightweight for fast laptops and CPU execution):
  ```bash
  litert-lm import \
    --from-huggingface-repo=litert-community/gemma-2-2b-it-litert-lm \
    gemma-2-2b-it-cpu.litertlm \
    gemma-2b
  ```
  _Registers model at: `~/.litert-lm/models/gemma-2b/model.litertlm`_

---

### 3. Running the Assistant

#### Launch the Native Desktop GUI (Recommended)
```bash
python gui_assistant.py
# or:
python desktop_assistant.py --gui
```

#### Run in Interactive CLI Mode (Terminal)
```bash
python desktop_assistant.py
```

#### Specify a Particular Model from Cache
```bash
python gui_assistant.py --model-name gemma4-26b
# or CLI:
python desktop_assistant.py --model-name gemma4-26b
```

#### Force Hardware Backend (GPU, CPU, or NPU)
```bash
python desktop_assistant.py --gui --backend gpu
# or for CPU fallback:
python desktop_assistant.py --gui --backend cpu
```

#### Test / Simulation Mode (No Weights Required)
To test and interact with the GUI and custom tools immediately without waiting for a large model download:
```bash
python gui_assistant.py
# (Automatically defaults to simulation mode if no weights are cached, or toggle via settings tab)
```

---

## 🛠️ Custom Python Tools Reference

### Habit Tracking Tools ([tools/habits.py](file:///c:/Users/Austi/OneDrive/CodingProjects/AGY/Mite%20AI/tools/habits.py))

```python
def track_habit(
    habit_name: str,
    status: str = "completed",
    date: str = "",
    metric_value: float = 0.0,
    metric_unit: str = "",
    notes: str = ""
) -> str
```
- **Example Usage in Prompt**: *"I ran 5km this morning in 25 minutes, record that!"*
- **Action**: Updates [data/habits.json](file:///c:/Users/Austi/OneDrive/CodingProjects/AGY/Mite%20AI/data/habits.json), increments consecutive streak counter, and returns streak stats.

```python
def get_habit_stats(habit_name: str = "", days: int = 7) -> str
```
- **Example Usage in Prompt**: *"How have my habits been this past week?"*

```python
def list_habits() -> str
```
- **Example Usage in Prompt**: *"What habits am I tracking today?"*

---

### Personal Notes Tools ([tools/notes.py](file:///c:/Users/Austi/OneDrive/CodingProjects/AGY/Mite%20AI/tools/notes.py))

```python
def append_note(
    content: str,
    category: str = "General",
    title: str = "",
    timestamp: bool = True
) -> str
```
- **Example Usage in Prompt**: *"Note down an idea under 'Projects': Create a local vector store with SQLite"*
- **Action**: Formats and appends a structured entry to [data/notes.md](file:///c:/Users/Austi/OneDrive/CodingProjects/AGY/Mite%20AI/data/notes.md):
  ```markdown
  ### [2026-10-08 00:45:00] [Projects]: Local Vector Store
  
  Create a local vector store with SQLite
  
  ---
  ```

```python
def read_notes(category: str = "", limit: int = 5, search_query: str = "") -> str
```
- **Example Usage in Prompt**: *"Find my notes about vector store"* or *"Show recent Work notes"*

---

## 🧪 Running Unit Tests

Run the test suite to verify habit streak calculations, note file updates, and model cache discovery:

```bash
python test_tools.py
```
Expected output:
```
.......
----------------------------------------------------------------------
Ran 7 tests in 0.115s

OK
```
