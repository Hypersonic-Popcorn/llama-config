import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Any

import pytest

from src.core.model_scanner import read_model_metadata, scan_models

gguf_patch = "src.core.model_scanner.gguf.GGUFReader"


def _make_reader(field_values: dict[str, Any] | None = None):
    reader = MagicMock()
    if field_values is None:
        reader.get_field.return_value = None
    else:

        def get_field(key):
            val = field_values.get(key)
            if val is not None:
                field = MagicMock()
                field.contents.return_value = val
                return field
            return None

        reader.get_field.side_effect = None
        reader.get_field = get_field
    return reader


def test_read_model_metadata_returns_metadata():
    metadata = {
        "general.name": "llama-2-7b",
        "general.architecture": "llama",
        "llama.context_length": 4096,
        "general.parameter_count": 6_738_000_000,
        "general.quantization_version": 2,
    }

    with patch(gguf_patch, return_value=_make_reader(metadata)):
        with patch.object(Path, "exists", return_value=True):
            with patch("os.path.getsize", return_value=4_200_000_000):
                result = read_model_metadata("/fake/model.gguf")

    assert result is not None
    assert result["name"] == "llama-2-7b"
    assert result["architecture"] == "llama"
    assert result["context_length"] == 4096
    assert result["parameter_count"] == 6_738_000_000
    assert result["quantization"] == 2
    assert result["file_size"] == 4_200_000_000
    assert result["filename"] == "model.gguf"
    assert result["full_path"] == "/fake/model.gguf"


def test_read_model_metadata_returns_dict_keys():
    with patch(gguf_patch, return_value=_make_reader()):
        with patch.object(Path, "exists", return_value=True):
            with patch("os.path.getsize", return_value=100_000):
                result = read_model_metadata("/fake/empty.gguf")

    assert result is not None
    expected_keys = {
        "name",
        "architecture",
        "context_length",
        "parameter_count",
        "quantization",
        "file_size",
        "filename",
        "full_path",
    }

    assert set(result.keys()) == expected_keys


def test_read_model_metadata_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        read_model_metadata("/nonexistent/path/model.gguf")


def test_read_model_metadata_returns_none_for_corrupt_file():
    with patch(gguf_patch, side_effect=OSError("bad file")):
        with patch.object(Path, "exists", return_value=True):
            result = read_model_metadata("/fake/corrupt.gguf")

    assert result is None


def test_read_model_metadata_returns_none_for_value_error():
    with patch(gguf_patch, side_effect=OSError("corrupt")):
        with patch.object(Path, "exists", return_value=True):
            result = read_model_metadata("/fake/invalid.gguf")

    assert result is None


def test_scan_models_returns_list_of_models(tmp_path):
    model_a = tmp_path / "model_a.gguf"
    model_a.write_text("dummy")
    model_b = tmp_path / "model_b.gguf"
    model_b.write_text("dummy")

    metadata_a = {
        "general.name": "model-a",
        "general.architecture": "llama",
    }
    metadata_b = {
        "general.name": "model-b",
        "general.architecture": "mistral",
    }

    reader_a = _make_reader(metadata_a)
    reader_b = _make_reader(metadata_b)

    def mock_reader_side_effect(p):
        if "model_a" in str(p):
            return reader_a
        return reader_b

    with patch(gguf_patch, side_effect=mock_reader_side_effect):
        with patch("os.path.getsize", return_value=1_000_000):
            result = scan_models(tmp_path)

    assert len(result) == 2
    assert {m["name"] for m in result} == {"model-a", "model-b"}


def test_scan_models_skips_non_gguf_files(tmp_path):
    gguf_file = tmp_path / "model.gguf"
    gguf_file.write_text("dummy")
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("hello")

    with patch(gguf_patch, return_value=_make_reader({"general.name": "model"})):
        with patch("os.path.getsize", return_value=1_000):
            result = scan_models(tmp_path)

    assert len(result) == 1


def test_scan_models_skips_corrupt_gguf_files(tmp_path):
    good = tmp_path / "good.gguf"
    good.write_text("dummy")
    bad = tmp_path / "bad.gguf"
    bad.write_text("dummy")

    def mock_reader_side_effect(p):
        if "good" in str(p):
            return _make_reader({"general.name": "good"})
        raise OSError("corrupt")

    with patch(gguf_patch, side_effect=mock_reader_side_effect):
        with patch("os.path.getsize", return_value=1_000):
            result = scan_models(tmp_path)

    assert len(result) == 1
    assert result[0]["name"] == "good"


def test_scan_models_handles_empty_directory(tmp_path):
    with patch(gguf_patch, return_value=_make_reader({"general.name": "dummy"})):
        with patch("os.path.getsize", return_value=1_000):
            result = scan_models(tmp_path)

    assert result == []


def test_scan_models_recurses_into_subdirectories(tmp_path):
    subdir = tmp_path / "subdir"
    subdir.mkdir()

    root_model = tmp_path / "root.gguf"
    root_model.write_text("dummy")
    sub_model = subdir / "sub.gguf"
    sub_model.write_text("dummy")

    def mock_reader_side_effect(p):
        if "root" in str(p):
            return _make_reader({"general.name": "root-model"})
        return _make_reader({"general.name": "sub-model"})

    with patch(gguf_patch, side_effect=mock_reader_side_effect):
        with patch("os.path.getsize", return_value=1_000):
            result = scan_models(tmp_path)

    assert len(result) == 2
    names = {m["name"] for m in result}
    assert names == {"root-model", "sub-model"}


def test_scan_models_handles_permission_error_in_subdir(tmp_path):
    inaccessible_dir = tmp_path / "noaccess"
    inaccessible_dir.mkdir()
    inaccessible_model = inaccessible_dir / "noaccess.gguf"
    inaccessible_model.write_text("dummy")

    good = tmp_path / "good.gguf"
    good.write_text("dummy")

    def mock_reader_side_effect(p):
        if "noaccess" in str(p):
            raise OSError("permission denied")
        return _make_reader({"general.name": "good"})

    with patch(gguf_patch, side_effect=mock_reader_side_effect):
        with patch("os.path.getsize", return_value=1_000):
            result = scan_models(tmp_path)

    assert len(result) == 1
    assert result[0]["name"] == "good"


def test_read_model_metadata_handles_field_index_error():
    reader = MagicMock()
    field = MagicMock()
    field.contents.side_effect = IndexError("out of bounds")
    reader.get_field.return_value = field

    with patch(gguf_patch, return_value=reader):
        with patch.object(Path, "exists", return_value=True):
            with patch("os.path.getsize", return_value=100):
                result = read_model_metadata("/fake/model.gguf")

    assert result is not None
    assert result["name"] is None


def test_read_model_metadata_handles_field_attribute_error():
    reader = MagicMock()
    field = MagicMock()
    field.contents.side_effect = AttributeError("bad field")
    reader.get_field.return_value = field

    with patch(gguf_patch, return_value=reader):
        with patch.object(Path, "exists", return_value=True):
            with patch("os.path.getsize", return_value=100):
                result = read_model_metadata("/fake/model.gguf")

    assert result is not None
    assert result["name"] is None


def test_read_model_metadata_handles_getsize_oserror():
    reader = MagicMock()
    reader.get_field.return_value = None

    with patch(gguf_patch, return_value=reader):
        with patch.object(Path, "exists", return_value=True):
            with patch("os.path.getsize", side_effect=OSError("cannot stat")):
                result = read_model_metadata("/fake/model.gguf")

    assert result is not None
    assert result["file_size"] is None
