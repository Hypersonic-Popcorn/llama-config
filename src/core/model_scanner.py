import logging
import os
from pathlib import Path
from typing import Any, cast

import numpy as np

import gguf
from gguf import GGUFValueType

from src.core.model import Model, ScanResult

logger = logging.getLogger(__name__)


def _get_field_value(reader: gguf.GGUFReader, key: str) -> Any:
    field_obj = reader.get_field(key)
    if field_obj is None:
        return None
    parts = field_obj.parts
    val_type = int(parts[2][0])

    if val_type == GGUFValueType.STRING.value:
        return bytes(parts[4]).decode("utf-8")
    if val_type == GGUFValueType.FLOAT32.value:
        return float(np.frombuffer(bytes(parts[3]), dtype="float32")[0])
    if val_type == GGUFValueType.FLOAT64.value:
        return float(np.frombuffer(bytes(parts[3]), dtype="float64")[0])
    if val_type == GGUFValueType.INT32.value:
        return int(parts[3][0])
    if val_type == GGUFValueType.UINT32.value:
        return int(parts[3][0])
    if val_type == GGUFValueType.UINT64.value:
        return int(parts[3][0])
    if val_type == GGUFValueType.INT64.value:
        return int(parts[3][0])
    if val_type == GGUFValueType.BOOL.value:
        return bool(int(bytes(parts[3])[0]))
    return None


def read_model_metadata(path: str | Path) -> Model | None:
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

    def get(key: str) -> Any:
        try:
            return _get_field_value(reader, key)
        except Exception:
            return None

    arch = get("general.architecture")
    ctx_len = get("general.context_length") or get(f"{arch}.context_length") if arch else None

    return Model(
        name=get("general.name"),
        architecture=arch,
        basename=get("general.basename"),
        context_length=cast(int | None, ctx_len),
        parameter_count=cast(int | None, get("general.parameter_count")),
        quantization_version=cast(int | None, get("general.quantization_version")),
        finetune=get("general.finetune"),
        license=get("general.license"),
        license_link=get("general.license.link"),
        sampling_temp=cast(float | None, get("general.sampling.temp")),
        sampling_top_k=cast(int | None, get("general.sampling.top_k")),
        sampling_top_p=cast(float | None, get("general.sampling.top_p")),
        size_label=get("general.size_label"),
        model_type=get("general.type"),
        block_count=cast(int | None, get(f"{arch}.block_count")) if arch else None,
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
