import os
from pathlib import Path
from typing import Any

import gguf


def _get_field_value(reader: gguf.GGUFReader, key: str) -> str | int | float | None:
    field = reader.get_field(key)
    if field is None:
        return None
    try:
        return field.contents(0)
    except (IndexError, AttributeError):
        return None


def read_model_metadata(path: str | Path) -> dict[str, Any] | None:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")

    try:
        reader = gguf.GGUFReader(path)
    except (OSError, ValueError):
        return None

    try:
        file_size = os.path.getsize(path)
    except OSError:
        file_size = None

    return {
        "name": _get_field_value(reader, "general.name"),
        "architecture": _get_field_value(reader, "general.architecture"),
        "context_length": _get_field_value(reader, "llama.context_length"),
        "parameter_count": _get_field_value(reader, "general.parameter_count"),
        "quantization": _get_field_value(reader, "general.quantization_version"),
        "file_size": file_size,
        "filename": path.name,
        "full_path": str(path),
    }


def scan_models(directory: str | Path) -> list[dict[str, Any]]:
    directory = Path(directory)
    models: list[dict[str, Any]] = []

    for root, _dirs, files in os.walk(directory):
        for filename in files:
            if not filename.lower().endswith(".gguf"):
                continue

            filepath = Path(root) / filename
            try:
                meta = read_model_metadata(filepath)
            except FileNotFoundError:
                continue

            if meta is None:
                continue

            models.append(meta)

    return models
