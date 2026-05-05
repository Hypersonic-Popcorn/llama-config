from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.model import Model, ScanResult
from src.core.model_scanner import read_model_metadata, scan_models

gguf_patch = "src.core.model_scanner.gguf.GGUFReader"


def _make_reader(field_values: dict | None = None):  # pyright: ignore
    reader = MagicMock()
    if field_values is None:
        reader.get_field.return_value = None
    else:
        from gguf import GGUFValueType

        def _make_parts(val):
            parts = []
            if isinstance(val, str):
                val_type = GGUFValueType.STRING.value
                p2 = MagicMock()
                p2.__getitem__.return_value = val_type
                parts = [
                    len(val.encode("utf-8")),
                    MagicMock(),
                    p2,
                    None,
                    val.encode("utf-8"),
                ]
            elif isinstance(val, float):
                val_type = GGUFValueType.FLOAT64.value
                p2 = MagicMock()
                p2.__getitem__.return_value = val_type
                p3 = MagicMock()
                p3.__getitem__.return_value = val
                parts = [MagicMock(), MagicMock(), p2, p3]
            else:
                val_type = GGUFValueType.INT32.value if -2**31 <= val < 2**31 else GGUFValueType.INT64.value
                p2 = MagicMock()
                p2.__getitem__.return_value = val_type
                p3 = MagicMock()
                p3.__getitem__.return_value = val
                parts = [MagicMock(), MagicMock(), p2, p3]
            return parts

        def get_field(key):
            val = field_values.get(key)
            if val is not None:
                field = MagicMock()
                field.parts = _make_parts(val)
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
    assert isinstance(result, Model)
    assert result.name == "llama-2-7b"
    assert result.architecture == "llama"
    assert result.context_length == 4096
    assert result.parameter_count == 6_738_000_000
    assert result.quantization_version == 2
    assert result.file_size == 4_200_000_000
    assert result.filename == "model.gguf"
    assert result.full_path == "/fake/model.gguf"


def test_read_model_metadata_returns_model_with_none_fields():
    with patch(gguf_patch, return_value=_make_reader()):
        with patch.object(Path, "exists", return_value=True):
            with patch("os.path.getsize", return_value=100_000):
                result = read_model_metadata("/fake/empty.gguf")

    assert result is not None
    assert isinstance(result, Model)
    assert result.name is None
    assert result.architecture is None
    assert result.context_length is None
    assert result.parameter_count is None
    assert result.quantization_version is None
    assert result.file_size == 100_000
    assert result.filename == "empty.gguf"
    assert result.full_path == "/fake/empty.gguf"


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

    assert isinstance(result, ScanResult)
    assert len(result.models) == 2
    names = {m.name for m in result.models}
    assert names == {"model-a", "model-b"}


def test_scan_models_skips_non_gguf_files(tmp_path):
    gguf_file = tmp_path / "model.gguf"
    gguf_file.write_text("dummy")
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("hello")

    with patch(gguf_patch, return_value=_make_reader({"general.name": "model"})):
        with patch("os.path.getsize", return_value=1_000):
            result = scan_models(tmp_path)

    assert len(result.models) == 1


def test_scan_models_collects_errors_for_corrupt_files(tmp_path):
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

    assert len(result.models) == 1
    assert result.models[0].name == "good"
    assert len(result.errors) == 1
    assert "InvalidModel:" in result.errors[0]
    assert "bad.gguf" in result.errors[0]


def test_scan_models_handles_empty_directory(tmp_path):
    dummy = tmp_path / "dummy.gguf"
    dummy.write_text("dummy")
    with patch(gguf_patch, return_value=_make_reader({"general.name": "dummy"})):
        with patch("os.path.getsize", return_value=1_000):
            result = scan_models(tmp_path)

    assert len(result.models) == 1
    assert result.models[0].name == "dummy"


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

    assert len(result.models) == 2
    names = {m.name for m in result.models}
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

    assert len(result.models) == 1
    assert result.models[0].name == "good"


def test_read_model_metadata_handles_field_index_error():
    reader = MagicMock()
    field = MagicMock()
    parts = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    parts[2] = 0  # INT32 type
    parts[3] = MagicMock()
    parts[3].__getitem__ = lambda self, i: 0
    field.parts = parts
    field.parts[3].__getitem__.side_effect = IndexError("out of bounds")
    reader.get_field.return_value = field

    with patch(gguf_patch, return_value=reader):
        with patch.object(Path, "exists", return_value=True):
            with patch("os.path.getsize", return_value=100):
                result = read_model_metadata("/fake/model.gguf")

    assert result is not None
    assert isinstance(result, Model)
    assert result.name is None


def test_read_model_metadata_handles_field_attribute_error():
    reader = MagicMock()
    field = MagicMock()
    parts = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    parts[2] = 0
    parts[3] = MagicMock()
    parts[3].__getitem__ = lambda self, i: 0
    field.parts = parts
    field.parts[3].__getitem__.side_effect = AttributeError("bad field")
    reader.get_field.return_value = field

    with patch(gguf_patch, return_value=reader):
        with patch.object(Path, "exists", return_value=True):
            with patch("os.path.getsize", return_value=100):
                result = read_model_metadata("/fake/model.gguf")

    assert result is not None
    assert isinstance(result, Model)
    assert result.name is None


def test_read_model_metadata_handles_getsize_oserror():
    reader = MagicMock()
    reader.get_field.return_value = None

    with patch(gguf_patch, return_value=reader):
        with patch.object(Path, "exists", return_value=True):
            with patch("os.path.getsize", side_effect=OSError("cannot stat")):
                result = read_model_metadata("/fake/model.gguf")

    assert result is not None
    assert isinstance(result, Model)
    assert result.file_size is None


def test_scan_models_handles_unreadable_gguf_data(tmp_path):
    good = tmp_path / "good.gguf"
    good.write_text("dummy")
    corrupt = tmp_path / "corrupt.gguf"
    corrupt.write_text("corrupt")

    def mock_reader_side_effect(p):
        if "good" in str(p):
            return _make_reader({"general.name": "good"})
        raise ValueError("invalid gguf")

    with patch(gguf_patch, side_effect=mock_reader_side_effect):
        with patch("os.path.getsize", return_value=1_000):
            result = scan_models(tmp_path)

    assert len(result.models) == 1
    assert result.models[0].name == "good"
    assert len(result.errors) == 1
    assert "InvalidModel:" in result.errors[0]
    assert "corrupt.gguf" in result.errors[0]


def test_scan_models_returns_empty_when_no_gguf_files(tmp_path):
    empty_file = tmp_path / "notes.txt"
    empty_file.write_text("nothing here")

    with patch(gguf_patch, return_value=_make_reader({"general.name": "dummy"})):
        with patch("os.path.getsize", return_value=1_000):
            result = scan_models(tmp_path)

    assert len(result.models) == 0
    assert len(result.errors) == 0
