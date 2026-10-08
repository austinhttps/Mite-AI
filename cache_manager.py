"""LiteRT Model Cache Manager for the Local AI Desktop Assistant.

Scans, inspects, and resolves local LiteRT model checkpoints (.litertlm)
from standard cache paths, environment variables, or custom directories.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, NamedTuple, Optional


class CachedModel(NamedTuple):
    """Metadata for a detected LiteRT model in cache."""
    name: str
    path: Path
    size_bytes: int
    size_gb: float
    directory: Path

    def __str__(self) -> str:
        return f"{self.name} ({self.size_gb:.2f} GB) at {self.path}"


def get_default_cache_dirs() -> List[Path]:
    """Returns candidate directories to search for LiteRT models."""
    candidates = []

    # 1. Environment variable if set
    env_cache = os.environ.get("LITERT_CACHE_DIR")
    if env_cache:
        candidates.append(Path(env_cache).expanduser().resolve())

    # 2. Standard litert-lm model cache (~/.litert-lm/models)
    home_litert = Path.home() / ".litert-lm" / "models"
    candidates.append(home_litert.resolve())

    # 3. Alternative home cache (~/.cache/litert-lm)
    alt_litert = Path.home() / ".cache" / "litert-lm"
    candidates.append(alt_litert.resolve())

    # 4. Local project models directory (./models)
    local_models = Path(__file__).resolve().parent / "models"
    candidates.append(local_models.resolve())

    # Filter duplicates while preserving order
    unique_dirs: List[Path] = []
    for d in candidates:
        if d not in unique_dirs:
            unique_dirs.append(d)

    return unique_dirs


def find_cached_models(search_dirs: Optional[List[Path]] = None) -> List[CachedModel]:
    """Recursively searches for .litertlm model files in the specified or default cache dirs.

    Args:
        search_dirs: Optional list of directory paths to scan.

    Returns:
        List of detected CachedModel objects sorted by model name.
    """
    if search_dirs is None:
        search_dirs = get_default_cache_dirs()

    found_models: List[CachedModel] = []
    seen_paths = set()

    for directory in search_dirs:
        if not directory.exists() or not directory.is_dir():
            continue

        try:
            # Look for *.litertlm files
            for file_path in directory.rglob("*.litertlm"):
                resolved = file_path.resolve()
                if resolved in seen_paths or not resolved.is_file():
                    continue
                seen_paths.add(resolved)

                size = resolved.stat().st_size
                # Deduce clean model name from parent dir or file stem
                model_name = resolved.parent.name if resolved.name == "model.litertlm" else resolved.stem
                found_models.append(
                    CachedModel(
                        name=model_name,
                        path=resolved,
                        size_bytes=size,
                        size_gb=size / (1024 ** 3),
                        directory=resolved.parent,
                    )
                )
        except (PermissionError, OSError):
            continue

    return sorted(found_models, key=lambda m: m.name)


def resolve_model_path(
    explicit_path: Optional[str] = None,
    preferred_model_name: Optional[str] = None,
    custom_cache_dir: Optional[str] = None,
) -> Optional[Path]:
    """Resolves the best matching LiteRT model path.

    Resolution Priority:
    1. explicit_path (e.g. from CLI --model-path)
    2. LITERT_MODEL_PATH environment variable
    3. Matching model by preferred_model_name in custom or default caches
    4. First model found in custom or default caches

    Returns:
        Path to the resolved model file, or None if no valid model is found.
    """
    # 1. Check explicit parameter
    if explicit_path:
        p = Path(explicit_path).expanduser().resolve()
        if p.exists() and p.is_file():
            return p

    # 2. Check LITERT_MODEL_PATH environment variable
    env_path = os.environ.get("LITERT_MODEL_PATH")
    if env_path:
        p = Path(env_path).expanduser().resolve()
        if p.exists() and p.is_file():
            return p

    # 3. Search in cache directories
    search_dirs = get_default_cache_dirs()
    if custom_cache_dir:
        custom_path = Path(custom_cache_dir).expanduser().resolve()
        if custom_path not in search_dirs:
            search_dirs.insert(0, custom_path)

    available = find_cached_models(search_dirs)
    if not available:
        return None

    # Try matching preferred model name
    if preferred_model_name:
        pref = preferred_model_name.lower().strip()
        for m in available:
            if pref in m.name.lower() or pref in str(m.path).lower():
                return m.path

    # Return first available model
    return available[0].path


def get_import_instructions() -> str:
    """Returns helpful instructions for obtaining and caching LiteRT models."""
    return """
💡 No LiteRT model (.litertlm) found in your local cache.

To download and register a local model into your LiteRT cache:

1. Gemma 4 26B (Recommended for powerful workstations with 24GB+ VRAM/RAM):
   litert-lm import \\
     --from-huggingface-repo=litert-community/gemma-4-26B-A4B-it-litert-lm \\
     gemma-4-26B-A4B-it-web.litertlm \\
     gemma4-26b

2. Gemma 2 2B / 9B (Lightweight for fast laptops and CPU/integrated GPU):
   litert-lm import \\
     --from-huggingface-repo=litert-community/gemma-2-2b-it-litert-lm \\
     gemma-2-2b-it-cpu.litertlm \\
     gemma-2b

Default cache location:
   ~/.litert-lm/models/<model_name>/model.litertlm

You can also pass an explicit path using:
   python desktop_assistant.py --model-path "C:/path/to/model.litertlm"
"""
