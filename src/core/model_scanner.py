import logging
import os
from pathlib import Path
from typing import Any, cast

import gguf

from src.core.model import Model, ScanResult

logger = logging.getLogger(__name__)


def read_model_metadata(path: str | Path) -> Model | None:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")

    try:
        reader = gguf.GGUFReader(path)
    except (OSError, ValueError) as e:
        return None

    try:
        file_size = os.path.getsize(path)
    except OSError:
        file_size = None

    def _get_field(key: str) -> Any:
        field_obj = reader.get_field(key)
        if field_obj is None:
            return None
        try:
            return field_obj.contents(0)
        except (IndexError, AttributeError):
            return None

    return Model(
        name=cast(str | None, _get_field("general.name")),
        architecture=cast(str | None, _get_field("general.architecture")),
        context_length=cast(int | None, _get_field("llama.context_length")),
        parameter_count=cast(int | None, _get_field("general.parameter_count")),
        quantization=cast(int | None, _get_field("general.quantization_version")),
        file_size=file_size,
        filename=path.name,
        full_path=str(path),
    )


def scan_models(directory: str | Path) -> ScanResult:
    result = ScanResult()
    directory = Path(directory)

    for root, _dirs, files in os.walk(directory):
        for filename in files:
            if not filename.lower().endswith(".gguf"):
                continue

            filepath = Path(root) / filename
            try:
                meta = read_model_metadata(filepath)
            except FileNotFoundError:
                continue
            except (OSError, ValueError) as e:
                result.errors.append(f"InvalidModel: {filepath}: {e}")
                continue

            if meta is None:
                result.errors.append(f"InvalidModel: {filepath}: unreadable GGUF data")
                continue

            result.models.append(meta)

    return result
