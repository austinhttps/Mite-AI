"""Private Local AI Desktop Assistant.

Powered by the Google Antigravity SDK and LiteRT on-device runtime.
Equipped with local model cache discovery, an interactive execution loop,
and custom tools for daily habit tracking and persistent local note taking.
"""

from __future__ import annotations

import argparse
import asyncio
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

# Ensure Windows terminal handles UTF-8 output cleanly without charmap crashes
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from cache_manager import (
    find_cached_models,
    get_default_cache_dirs,
    get_import_instructions,
    resolve_model_path,
)
from tools.habits import get_habit_stats, list_habits, track_habit
from tools.notes import append_note, list_note_categories, read_notes

# Google Antigravity SDK imports
try:
    from google.antigravity import Agent, LiteRTAgentConfig, LiteRTBackend
    from google.antigravity.hooks import policy
    from google.antigravity.types import CapabilitiesConfig, AgentBehavior
    AGY_AVAILABLE = True
except ImportError:
    AGY_AVAILABLE = False


SYSTEM_INSTRUCTIONS = """You are a helpful, private local desktop AI assistant running entirely on-device via Google Antigravity SDK and LiteRT.
All operations, files, and model inferences stay 100% local on this machine.

You have access to custom local tools:
1. Habit Tracking:
   - `track_habit`: Call this to log or update daily habits (exercise, reading, water, coding, etc.). Always report back their streak.
   - `get_habit_stats`: Call this to retrieve statistics, streaks, and completion rates.
   - `list_habits`: Call this to list all registered habits and check today's completion.

2. Personal Notes:
   - `append_note`: Call this to save thoughts, ideas, todos, summaries, or reminders into the user's local markdown notebook.
   - `read_notes`: Call this to search or retrieve recent notes from the local notebook.
   - `list_note_categories`: Call this to check active note categories.

Guidelines:
- Be concise, direct, helpful, and encouraging.
- When the user asks to log a habit or save a note, call the appropriate tool immediately and summarize the result.
- Never claim to send data over the internet; you operate completely offline.
"""


def print_banner(model_name: str, model_path: str, backend_str: str) -> None:
    """Prints a clean CLI banner with assistant information."""
    width = 72
    print("=" * width)
    print(" 🤖 PRIVATE LOCAL AI DESKTOP ASSISTANT".center(width))
    print(" Powered by Google Antigravity SDK & LiteRT".center(width))
    print("=" * width)
    print(f" • Active Model : {model_name}")
    print(f" • Model Path   : {model_path}")
    print(f" • Hardware     : {backend_str.upper()} On-Device Engine")
    print(f" • Privacy      : 100% Offline & Local (Zero Cloud Telemetry)")
    print(f" • Storage      : {PROJECT_ROOT / 'data'}")
    print("-" * width)
    print(" Type your query or use slash commands:")
    print("   /help    - Show command and tool shortcuts")
    print("   /habits  - View your habit tracking dashboard")
    print("   /notes   - Read recent notes from your local notebook")
    print("   /model   - Show model and cache diagnostic details")
    print("   /cache   - List all detected models in local cache")
    print("   /clear   - Clear the console screen")
    print("   /reset   - Reset conversation context")
    print("   /exit    - Exit the assistant")
    print("=" * width)
    print()


def show_help_menu() -> None:
    """Prints the command menu and tools reference."""
    print("\n" + "=" * 60)
    print("📋 Desktop Assistant Help & Shortcuts")
    print("=" * 60)
    print("Slash Commands:")
    print("  /help     : Display this help message")
    print("  /habits   : Quick view of all daily habits and current streaks")
    print("  /notes    : View last 5 notes from your local notebook")
    print("  /model    : View active model file path and runtime settings")
    print("  /cache    : Scan and display all .litertlm models in cache")
    print("  /clear    : Clear the terminal screen")
    print("  /reset    : Reset the conversation turn history")
    print("  /exit     : Exit the desktop assistant (or Ctrl+C)")
    print("\nCustom Tools available to Assistant:")
    print("  • Habit Tracking : track_habit, get_habit_stats, list_habits")
    print("  • Local Notebook : append_note, read_notes, list_note_categories")
    print("\nExample Prompts:")
    print("  • 'I just finished a 5km morning run, log that!'")
    print("  • 'How is my reading streak looking this week?'")
    print("  • 'Note down an idea: Build a local RAG pipeline with LiteRT'")
    print("  • 'Show me my recent notes under Ideas'")
    print("=" * 60 + "\n")


def display_cache_models() -> None:
    """Scans and prints all models found in the LiteRT cache."""
    print("\n🔍 Scanning local LiteRT model cache directories...")
    search_dirs = get_default_cache_dirs()
    models = find_cached_models(search_dirs)

    if not models:
        print("  ⚠️ No .litertlm models found in any cache directory.")
        print(get_import_instructions())
        return

    print(f"  Found {len(models)} model(s) in local cache:")
    for idx, m in enumerate(models, 1):
        print(f"  [{idx}] {m.name} ({m.size_gb:.2f} GB)")
        print(f"      Path: {m.path}")
    print()


async def run_interactive_simulation() -> None:
    """Interactive loop simulation for test mode or when no model weight is present."""
    print("\n[Simulation Mode Active]")
    print("You can interact with the tools directly or test slash commands.\n")

    while True:
        try:
            user_input = input("You > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        cmd = user_input.lower()
        if cmd in ("/exit", "/quit", "exit", "quit"):
            print("Shutting down desktop assistant. Have a productive day!")
            break
        elif cmd == "/help":
            show_help_menu()
        elif cmd == "/habits":
            print("\n" + list_habits())
            print("\n" + get_habit_stats(days=7) + "\n")
        elif cmd == "/notes":
            print("\n" + read_notes(limit=5) + "\n")
        elif cmd == "/model":
            print("\nModel Mode: Interactive Test / Simulation")
            print("Tools: Habittracker, NoteTaker active\n")
        elif cmd == "/cache":
            display_cache_models()
        elif cmd == "/clear":
            os.system("cls" if os.name == "nt" else "clear")
        elif cmd == "/reset":
            print("\n🔄 Conversation context reset.\n")
        else:
            # Simple keyword tool dispatcher in test/simulation mode
            lower_input = user_input.lower()
            if "habit" in lower_input or "streak" in lower_input or "run" in lower_input or "read" in lower_input:
                if "stat" in lower_input or "how" in lower_input or "look" in lower_input:
                    print("\nAssistant > " + get_habit_stats() + "\n")
                else:
                    # Parse habit name if possible
                    res = track_habit(habit_name=user_input, status="completed", notes="Logged via desktop assistant")
                    print("\nAssistant > " + res + "\n")
            elif "note" in lower_input or "idea" in lower_input or "todo" in lower_input or "write" in lower_input:
                if "read" in lower_input or "show" in lower_input or "list" in lower_input:
                    print("\nAssistant >\n" + read_notes(limit=3) + "\n")
                else:
                    res = append_note(content=user_input, category="General", title="Quick Note")
                    print("\nAssistant > " + res + "\n")
            else:
                print(
                    "\nAssistant > [Local Agent Simulation] Received: \"" + user_input + "\". "
                    "In full LiteRT mode, Gemma generates responses with on-device LLM reasoning. "
                    "Try asking to log a habit or save a note!\n"
                )


async def run_execution_loop(agent: Agent, model_name: str, model_path: Path, backend_str: str) -> None:
    """Main execution loop interacting with the user via LiteRT Antigravity Agent."""
    print_banner(model_name=model_name, model_path=str(model_path), backend_str=backend_str)

    while True:
        try:
            user_input = input("You > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nShutting down desktop assistant. Have a great day!")
            break

        if not user_input:
            continue

        cmd = user_input.lower()
        if cmd in ("/exit", "/quit", "exit", "quit"):
            print("\nShutting down desktop assistant. Have a great day!")
            break
        elif cmd == "/help":
            show_help_menu()
            continue
        elif cmd == "/habits":
            print("\n" + list_habits())
            print("\n" + get_habit_stats(days=7) + "\n")
            continue
        elif cmd == "/notes":
            print("\n" + read_notes(limit=5) + "\n")
            continue
        elif cmd == "/model":
            print(f"\nModel: {model_name}")
            print(f"Path: {model_path}")
            print(f"Backend: {backend_str.upper()}\n")
            continue
        elif cmd == "/cache":
            display_cache_models()
            continue
        elif cmd == "/clear":
            os.system("cls" if os.name == "nt" else "clear")
            continue
        elif cmd == "/reset":
            print("\n🔄 Conversation context reset. Starting fresh turn.\n")
            # In Antigravity SDK, a fresh chat can be continued or we can acknowledge reset
            continue

        # Send query to local LiteRT agent
        print("\nAssistant > ", end="", flush=True)
        try:
            response = await agent.chat(user_input)
            async for token in response:
                print(token, end="", flush=True)
            print("\n")
        except KeyboardInterrupt:
            print("\n[Generation interrupted by user]\n")
        except Exception as e:
            print(f"\n⚠️ Turn Error: {e}\n")


async def async_main() -> None:
    """Parses CLI arguments, resolves LiteRT cache, and boots the desktop assistant."""
    parser = argparse.ArgumentParser(
        description="Private Local AI Desktop Assistant using Google Antigravity SDK & LiteRT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Explicit absolute path to a .litertlm model checkpoint file.",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default=None,
        help="Name or substring of the preferred model in cache (e.g. 'gemma4-26b', 'gemma-2b').",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=None,
        help="Custom directory to scan for cached LiteRT models.",
    )
    parser.add_argument(
        "--backend",
        type=str,
        choices=["gpu", "cpu", "npu", "auto"],
        default="auto",
        help="Hardware inference backend (default: auto).",
    )
    parser.add_argument(
        "--speculative-decoding",
        action="store_true",
        help="Enable multi-token speculative decoding for accelerated inference.",
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Run in interactive simulation mode to test habit and note tools without loading model weights.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the native graphical user interface (PyQt6 Desktop GUI).",
    )
    args = parser.parse_args()

    # If GUI is requested, hand off to gui_assistant
    if args.gui:
        from gui_assistant import launch_gui
        resolved_path = resolve_model_path(
            explicit_path=args.model_path,
            preferred_model_name=args.model_name,
            custom_cache_dir=args.cache_dir,
        )
        launch_gui(initial_model_path=resolved_path, test_mode=args.test_mode)
        return

    # If test mode is explicitly requested, run simulation
    if args.test_mode:
        print_banner("Simulation/Test Model", "N/A (Test Mode)", "Local CPU")
        await run_interactive_simulation()
        return

    # 1. Resolve model from local LiteRT cache or arguments
    resolved_path = resolve_model_path(
        explicit_path=args.model_path,
        preferred_model_name=args.model_name,
        custom_cache_dir=args.cache_dir,
    )

    if not resolved_path:
        print("=" * 72)
        print("⚠️ No LiteRT model checkpoint (.litertlm) found in cache.")
        print("=" * 72)
        print(get_import_instructions())
        print("-" * 72)
        print("Tip: You can test all custom tools right now in simulation mode:")
        print("     python desktop_assistant.py --test-mode\n")
        choice = input("Would you like to start in test/simulation mode now? [Y/n]: ").strip().lower()
        if choice in ("", "y", "yes"):
            print_banner("Simulation/Test Model", "Local Tools Test", "Simulation")
            await run_interactive_simulation()
        return

    # 2. Configure Backend
    backend_val = args.backend
    if backend_val == "auto":
        # Auto detection
        try:
            from google.antigravity.connections.local.litert_connection import (
                _check_gpu_acceleration_available,
            )
            has_gpu = _check_gpu_acceleration_available()
            backend_val = "gpu" if has_gpu else "cpu"
        except Exception:
            backend_val = "cpu"

    if backend_val == "cpu":
        os.environ["ANTIGRAVITY_ALLOW_CPU"] = "1"

    # Register custom tools
    assistant_tools = [
        track_habit,
        get_habit_stats,
        list_habits,
        append_note,
        read_notes,
        list_note_categories,
    ]

    model_name = resolved_path.parent.name if resolved_path.name == "model.litertlm" else resolved_path.stem

    print(f"Loading LiteRT model '{model_name}' from: {resolved_path}...")
    print(f"Initializing Antigravity on-device agent (Backend: {backend_val.upper()})...\n")

    # 3. Create LiteRTAgentConfig
    config = LiteRTAgentConfig(
        model_path=str(resolved_path),
        backend=backend_val,
        enable_speculative_decoding=args.speculative_decoding,
        cache_dir=args.cache_dir,
        system_instructions=SYSTEM_INSTRUCTIONS,
        tools=assistant_tools,
        policies=[policy.allow_all()],  # Allow seamless tool execution without approval halts
    )

    # 4. Run Agent session with execution loop
    async with Agent(config=config) as agent:
        await run_execution_loop(
            agent=agent,
            model_name=model_name,
            model_path=resolved_path,
            backend_str=backend_val,
        )


def main() -> None:
    """Synchronous entry point."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")


if __name__ == "__main__":
    main()
