# Parsing GGUF Metadata

## Overview

GGUF files store model weights along with key-value metadata. The Python `gguf` library provides a `GGUFReader` class that exposes this metadata through internal structures.

## Fields to Parse

Only **general.* keys**, **<arch>.block_count**, and **<arch>.context_length** are needed. Everything else can be skipped.

The 3 useful GGUF fields that map to llama-server CLI flags:

| llama-server flag | GGUF field | Example values |
|---|---|---|
| `-c, --ctx-size N` | `<arch>.context_length` | 262144 / 1048576 |
| `--temperature N` | `general.sampling.temp` | 1.0 |
| `--top-k N` | `general.sampling.top_k` | 64 / 20 |
| `--top-p N` | `general.sampling.top_p` | 0.95 |

> [!NOTE]
> `context_length` is stored under the architecture-specific key (e.g. `gemma4.context_length`), not `general.context_length`. Always fall back to `<arch>.context_length` when `general.context_length` is not found.

`--rope-freq-base` and `--swa-full` were considered but are not useful — rope freq base is loaded from the model anyway, and swa-full is a boolean that doesn't benefit from metadata parsing.

## Core API

```python
import gguf

reader = gguf.GGUFReader("model.gguf")

# All KV fields are available via the `fields` property
# Keys are strings, values are ReaderField objects
for key in reader.fields:
    field = reader.get_field(key)
```

## ReaderField Structure

Each `ReaderField` contains a `parts` attribute — a list of numpy memmap arrays. The structure varies by field type:

### Key fields (GGUF.* prefix)

These are internal GGUF metadata and should be skipped:

```python
# GGUF.version, GGUF.tensor_count, GGUF.kv_count
# These have only 1 part: the raw value
# parts[0] = value directly
```

### Regular KV fields

Fields with the standard KV structure have multiple parts:

```python
field = reader.get_field("general.name")
# parts[0] = key name length (uint64)
# parts[1] = key bytes (uint8 array)
# parts[2] = value type (uint32, a GGUFValueType enum)
# parts[3] = value data (depends on type)
# parts[4] = value data (for STRING type only)
```

## Value Type Decoding

The `GGUFValueType` enum maps integer codes to types:

```python
from gguf import GGUFValueType

print(GGUFValueType(4).name)  # UINT32
print(GGUFValueType(5).name)  # INT32
print(GGUFValueType(7).name)  # BOOL
print(GGUFValueType(8).name)  # STRING
print(GGUFValueType(9).name)  # ARRAY
```

### Decoding by type

```python
import numpy as np

def decode_field(field):
    val_type = int(field.parts[2][0])

    # STRING — value bytes are in parts[4]
    if val_type == GGUFValueType.STRING.value:
        return bytes(field.parts[4]).decode("utf-8")

    # Simple scalars — value bytes are in parts[3]
    if val_type == GGUFValueType.FLOAT32.value:
        return float(np.frombuffer(bytes(field.parts[3]), dtype="float32")[0])
    if val_type == GGUFValueType.FLOAT64.value:
        return float(np.frombuffer(bytes(field.parts[3]), dtype="float64")[0])
    if val_type == GGUFValueType.INT32.value:
        return int(field.parts[3][0])
    if val_type == GGUFValueType.UINT32.value:
        return int(field.parts[3][0])
    if val_type == GGUFValueType.BOOL.value:
        return bool(int(bytes(field.parts[3])[0]))

    # ARRAY — parts[3] = array length, parts[4+] = items
    # Arrays have a variable-length structure and may span multiple parts
    if val_type == GGUFValueType.ARRAY.value:
        inner_type = field.types[1].name
        return f"<{inner_type} array>"

    return f"<type {val_type}>"
```

## Filtering

Skip keys:

```python
skip_keys = {
    "GGUF.version",
    "GGUF.tensor_count",
    "GGUF.kv_count",
    "quantize.imatrix.dataset",
    "quantize.imatrix.file",
    "tokenizer.chat_template",  # very large string
}
```

## Field Selection

Only parse these patterns:

- `general.*` — any general metadata key
- `<arch>.block_count` — architecture-specific block count (e.g. `gemma4.block_count`, `qwen35.block_count`)
- `<arch>.context_length` — architecture-specific context length (e.g. `gemma4.context_length`, `nemotron_h.context_length`)

Everything else should be skipped.

## Full Example

```python
import numpy as np
import gguf
from gguf import GGUFValueType


def decode_field(field):
    val_type = int(field.parts[2][0])

    if val_type == GGUFValueType.STRING.value:
        return bytes(field.parts[4]).decode("utf-8")

    if val_type in (GGUFValueType.FLOAT32.value, GGUFValueType.FLOAT64.value):
        dtype = "float32" if val_type == GGUFValueType.FLOAT32.value else "float64"
        return float(np.frombuffer(bytes(field.parts[3]), dtype=dtype)[0])

    if val_type in (GGUFValueType.INT32.value, GGUFValueType.UINT32.value):
        return int(field.parts[3][0])

    if val_type == GGUFValueType.BOOL.value:
        return bool(int(bytes(field.parts[3])[0]))

    if val_type == GGUFValueType.ARRAY.value:
        inner_type = field.types[1].name
        return f"<{inner_type} array>"

    return f"<type {val_type}>"


def should_parse_key(key):
    if key.startswith("GGUF."):
        return False
    skip_keys = {
        "quantize.imatrix.dataset",
        "quantize.imatrix.file",
        "tokenizer.chat_template",
        "general.tags",
    }
    if key in skip_keys:
        return False
    if key.startswith("general."):
        return True
    parts = key.split(".")
    if len(parts) >= 2 and parts[-1] in ("block_count", "context_length"):
        return True
    return False


def read_metadata(path):
    reader = gguf.GGUFReader(path)

    for key in sorted(reader.fields.keys()):
        if not should_parse_key(key):
            continue
        field = reader.get_field(key)
        try:
            val = decode_field(field)
        except Exception:
            val = "<error reading value>"
        print(f"{key}: {val}")
```

## Useful Keys vs Skipped Keys

### Keys that are parsed

| Key pattern | Purpose |
|---|---|
| `general.name` | Human-readable model name |
| `general.basename` | Model base name |
| `general.architecture` | Architecture identifier |
| `general.file_type` | Quantization format code |
| `general.license` | License identifier |
| `general.license.link` | License URL |
| `general.finetune` | Fine-tune variant |
| `general.quantization_version` | GGUF quantization version |
| `general.sampling.temp` | Default temperature |
| `general.sampling.top_k` | Default top-k |
| `general.sampling.top_p` | Default top-p |
| `general.size_label` | Model size label |
| `general.type` | Model type (model, mmproj, etc.) |
| `<arch>.block_count` | Number of transformer blocks |
| `<arch>.context_length` | Trained context window size (not `general.context_length`) |

### Keys that are skipped

- `GGUF.*` — internal GGUF struct fields (version, tensor_count, kv_count)
- `quantize.imatrix.dataset` / `quantize.imatrix.file` — quantization dataset info
- `tokenizer.chat_template` — very large string
- `general.tags` — array field, not useful for scanning
- All other keys — architecture-specific attention params, tokenizer vocab, embeddings, etc.

## Scanning Strategy

Scanning GGUF files is time consuming. The `llama-config` system should:

1. **Store results on disk** — `scan_models.py` writes parsed metadata to `local_test/models.md`
2. **Pass results to `model_scanner.py`** — when called, `model_scanner.py` reads `models.md` as cached data
3. **Only rescan when necessary** — skip scanning if fresh data is available on disk

## SHA256 Checksums

`model_scanner.py` should compute a SHA256 hash for each `.gguf` file and store it alongside the parsed metadata. This enables incremental rescanning:

- On a normal scan, `model_scanner.py` compares stored SHA256 values with the current file hashes
- If the hash matches, skip rescanning that file
- If the hash differs, rescan that file and update the stored hash

## Full Rescan Flag

Implement a `--rescan` (or `--force`) flag for `model_scanner.py`:

- When the flag is set, rescan all files regardless of cached SHA256 values
- Update all stored hashes after scanning
- This is useful when the user explicitly requests a rescan (e.g., after new models are added to disk)
```
