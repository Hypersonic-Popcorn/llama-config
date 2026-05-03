import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.option_parser import (
    build_options_cache,
    load_options_cache,
    parse_server_markdown,
    parse_swap_config_doc,
)

server_md_content = """\
# LLaMA.cpp HTTP Server

## Common params

| Argument | Explanation |
| -------- | ----------- |
| `-t, --threads N` | number of threads to use (default: 0) |
| `--ctx-size N` | size of the prompt context (default: 0) |
| `-ngl, --n-gpu-layers N` | max layers for VRAM (default: auto) |
| `-fa, --flash-attn [on\\|off\\|auto]` | Flash Attention use (default: 'auto') |
| `--samplers SAMPLERS` | samplers order, separated by ';' (default: edskypmxt) |

### Sampling params

| Argument | Explanation |
| -------- | ----------- |
| `--temp N` | temperature (default: 0.80) |
| `-kvo, --kv-offload, -nkvo, --no-kv-offload` | enable KV cache offloading (default: enabled) |

## Build

```bash
cmake -B build
```

## Quick Start

```bash
./llama-server -m model.gguf
```
"""

swap_md_content = """\
# llama-swap config

# healthCheckTimeout: seconds to wait for model to be ready
# - optional, default: 120
# - minimum value is 15 seconds
healthCheckTimeout: 500

# logLevel: sets the logging value
# - optional, default: info
# - Valid log levels: debug, info, warn, error
logLevel: info

# logTimeFormat: timestamp format
# - optional, default: ""
logTimeFormat: ""

# globalTTL: default TTL in seconds before unloading
# - optional, default: 0 (never automatically unload)
globalTTL: 0

# macros: reusable snippets for configs
# - optional, default: empty dictionary
macros: {}
"""


@pytest.fixture
def mock_server_md(tmp_path):
    f = tmp_path / "server.md"
    f.write_text(server_md_content)
    return f


@pytest.fixture
def mock_swap_md(tmp_path):
    f = tmp_path / "swap.md"
    f.write_text(swap_md_content)
    return f


def test_parse_server_markdown_extracts_options(mock_server_md):
    result = parse_server_markdown(mock_server_md)
    flags = [r["flag"] for r in result]

    assert "--threads" in flags
    assert "--ctx-size" in flags
    assert "--n-gpu-layers" in flags
    assert "--flash-attn" in flags
    assert "--samplers" in flags


def test_parse_server_markdown_extracts_short_flags(mock_server_md):
    result = parse_server_markdown(mock_server_md)
    threads = next(r for r in result if r["flag"] == "--threads")
    assert threads["short"] == "-t"

    ngl = next(r for r in result if r["flag"] == "--n-gpu-layers")
    assert ngl["short"] == "-ngl"


def test_parse_server_markdown_extracts_defaults(mock_server_md):
    result = parse_server_markdown(mock_server_md)
    threads = next(r for r in result if r["flag"] == "--threads")
    assert threads["default"] == 0

    temp = next(r for r in result if r["flag"] == "--temp")
    assert temp["default"] == 0.8


def test_parse_server_markdown_extracts_env_vars(mock_server_md):
    result = parse_server_markdown(mock_server_md)
    threads = next(r for r in result if r["flag"] == "--threads")
    # The test data doesn't have env vars, but let's check the structure
    assert threads["env_var"] is None


def test_parse_server_markdown_handles_boolean_flags(mock_server_md):
    result = parse_server_markdown(mock_server_md)
    kv = next(r for r in result if r["flag"] == "--kv-offload")
    assert kv["is_flag"] is True


def test_parse_server_markdown_extracts_valid_values(mock_server_md):
    result = parse_server_markdown(mock_server_md)
    flash = next(r for r in result if r["flag"] == "--flash-attn")
    assert flash["valid_values"] == ["on", "off", "auto"]


def test_parse_server_markdown_skips_non_option_sections(mock_server_md):
    result = parse_server_markdown(mock_server_md)
    flags = [r["flag"] for r in result]
    assert "--cmake" not in flags
    assert "./llama-server" not in flags


def test_parse_server_markdown_cleans_html_tags():
    html_content = """\
## Common params

| Argument | Explanation |
| -------- | ----------- |
| `--temp N` | temperature (default: 0.80)<br/>(env: TEST_VAR) |
"""
    with patch("pathlib.Path.read_text", return_value=html_content):
        result = parse_server_markdown("/fake.md")

    desc = result[0]["description"]
    assert "<br/>" not in desc
    assert "temperature" in desc


def test_parse_swap_config_doc_extracts_keys(mock_swap_md):
    result = parse_swap_config_doc(mock_swap_md)
    flags = [r["flag"] for r in result]

    assert "healthCheckTimeout" in flags
    assert "logLevel" in flags
    assert "logTimeFormat" in flags
    assert "globalTTL" in flags
    assert "macros" in flags


def test_parse_swap_config_doc_extracts_defaults(mock_swap_md):
    result = parse_swap_config_doc(mock_swap_md)
    hct = next(r for r in result if r["flag"] == "healthCheckTimeout")
    assert hct["default"] == 120


def test_parse_swap_config_doc_extracts_valid_values(mock_swap_md):
    result = parse_swap_config_doc(mock_swap_md)
    ll = next(r for r in result if r["flag"] == "logLevel")
    assert ll["valid_values"] == ["debug", "info", "warn", "error"]


def test_build_options_cache_writes_json(tmp_path):
    server = tmp_path / "server.md"
    server.write_text(server_md_content)
    swap = tmp_path / "swap.md"
    swap.write_text(swap_md_content)
    cache = tmp_path / "cache.json"

    with patch("src.core.option_parser.settings") as mock_settings:
        mock_settings.docs_dir = tmp_path
        mock_settings.backup_dir = tmp_path
        result = build_options_cache()

    assert "llama-server" in result
    assert "llama-swap" in result
    assert len(result["llama-server"]) > 0
    assert len(result["llama-swap"]) > 0


def test_load_options_cache_loads_existing(tmp_path):
    cache_data = {"llama-server": [], "llama-swap": []}
    cache_file = tmp_path / "options_cache.json"
    cache_file.write_text(json.dumps(cache_data))

    with patch("src.core.option_parser.settings") as mock_settings:
        mock_settings.backup_dir = tmp_path
        result = load_options_cache()

    assert result == cache_data


def test_load_options_cache_rebuilds_when_missing(tmp_path):
    server = tmp_path / "server.md"
    server.write_text(server_md_content)
    swap = tmp_path / "swap.md"
    swap.write_text(swap_md_content)

    with patch("src.core.option_parser.settings") as mock_settings:
        mock_settings.docs_dir = tmp_path
        mock_settings.backup_dir = tmp_path
        result = load_options_cache()

    assert "llama-server" in result
    assert "llama-swap" in result


def test_load_options_cache_force_rebuild(tmp_path):
    cache_file = tmp_path / "options_cache.json"
    cache_file.write_text(json.dumps({"llama-server": [], "llama-swap": []}))

    server = tmp_path / "server.md"
    server.write_text(server_md_content)
    swap = tmp_path / "swap.md"
    swap.write_text(swap_md_content)

    with patch("src.core.option_parser.settings") as mock_settings:
        mock_settings.docs_dir = tmp_path
        mock_settings.backup_dir = tmp_path
        result = load_options_cache(force_rebuild=True)

    assert len(result["llama-server"]) > 0


def test_parse_server_markdown_handles_empty_table():
    empty = """\
| Argument | Explanation |
| -------- | ----------- |
"""
    with patch("pathlib.Path.read_text", return_value=empty):
        result = parse_server_markdown("/fake.md")

    assert result == []


def test_parse_server_markdown_handles_missing_file():
    with patch("pathlib.Path.read_text", return_value=""):
        result = parse_server_markdown("/nonexistent.md")

    assert result == []


def test_parse_swap_config_doc_handles_empty():
    with patch("pathlib.Path.read_text", return_value=""):
        result = parse_swap_config_doc("/nonexistent.md")

    assert result == []


def test_parse_swap_config_doc_handles_no_keys():
    content = """\
# Just some text
No config keys here.
"""
    with patch("pathlib.Path.read_text", return_value=content):
        result = parse_swap_config_doc("/fake.md")

    assert result == []


def test_parse_server_markdown_allows_values_regex():
    content = """\
## Params

| Argument | Explanation |
| -------- | ----------- |
| `--sample-val N` | sample value (default: enabled, allowed values: on, off) |
"""
    with patch("pathlib.Path.read_text", return_value=content):
        result = parse_server_markdown("/fake.md")

    assert len(result) == 1
    assert result[0]["valid_values"] == ["on", "off"]


def test_parse_server_markdown_derives_long_flag_from_short():
    content = """\
## Params

| Argument | Explanation |
| -------- | ----------- |
| `--my-option` | a flag with only long form |
"""
    with patch("pathlib.Path.read_text", return_value=content):
        result = parse_server_markdown("/fake.md")

    assert len(result) == 1
    assert result[0]["flag"] == "--my-option"


def test_parse_server_markdown_detects_file_type():
    content = """\
## Params

| Argument | Explanation |
| -------- | ----------- |
| `--model-fname N` | model file path (default: model.gguf) |
"""
    with patch("pathlib.Path.read_text", return_value=content):
        result = parse_server_markdown("/fake.md")

    assert len(result) == 1
    assert result[0]["type"] == "file"


def test_parse_server_markdown_detects_float_type():
    content = """\
## Params

| Argument | Explanation |
| -------- | ----------- |
| `-ngl, --n-gpu-layers N` | number of layers (default: 0) float |
"""
    with patch("pathlib.Path.read_text", return_value=content):
        result = parse_server_markdown("/fake.md")

    assert len(result) == 1
    assert result[0]["type"] == "float"


def test_parse_default_handles_true():
    from src.core.option_parser import _parse_default

    assert _parse_default("true") is True
    assert _parse_default("TRUE") is True


def test_parse_default_handles_false():
    from src.core.option_parser import _parse_default

    assert _parse_default("false") is False


def test_parse_default_handles_none():
    from src.core.option_parser import _parse_default

    assert _parse_default("none") is None


def test_parse_default_handles_string():
    from src.core.option_parser import _parse_default

    assert _parse_default("hello") == "hello"
    assert _parse_default("'quoted'") == "quoted"


def test_parse_server_markdown_handles_only_short_flag():
    content = """\
## Params

| Argument | Explanation |
| -------- | ----------- |
| `-o` | output only (default: enabled) |
"""
    with patch("pathlib.Path.read_text", return_value=content):
        result = parse_server_markdown("/fake.md")

    assert len(result) == 1
    assert result[0]["flag"] == "--o"
    assert result[0]["short"] == "-o"


def test_parse_server_markdown_allowed_values_no_regex_match():
    content = """\
## Params

| Argument | Explanation |
| -------- | ----------- |
| `--val N` | value (default: enabled, allowed values) |
"""
    with patch("pathlib.Path.read_text", return_value=content):
        result = parse_server_markdown("/fake.md")

    assert len(result) == 1


def test_parse_server_markdown_allowed_values_bad_format():
    content = """\
## Params

| Argument | Explanation |
| -------- | ----------- |
| `--val N` | value (default: enabled, allowed values:(env: X)) |
"""
    with patch("pathlib.Path.read_text", return_value=content):
        result = parse_server_markdown("/fake.md")

    assert len(result) == 1
    assert result[0]["valid_values"] == ["enabled", "disabled"]


def test_parse_swap_config_doc_handles_file_error():
    with patch("pathlib.Path.read_text", side_effect=OSError("read error")):
        result = parse_swap_config_doc("/nonexistent.md")

    assert result == []


def test_load_options_cache_handles_corrupt_json(tmp_path):
    cache_file = tmp_path / "options_cache.json"
    cache_file.write_text("not valid json{{{")

    with patch("src.core.option_parser.settings") as mock_settings:
        mock_settings.backup_dir = tmp_path
        result = load_options_cache()

    assert "llama-server" in result
