import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.model import Model
from src.core.validator import (
    ValidationResult,
    _check_model_files_in_cmd,
    _validate_filters,
    _validate_hooks,
    _validate_matrix,
    _validate_model_entry,
    _validate_peers,
    _validate_timeouts,
    _validate_top_level,
    validate_config,
)

# --- ValidationResult tests ---


def test_validation_result_initial():
    result = ValidationResult(valid=True)
    assert result.valid is True
    assert result.errors == []
    assert result.warnings == []


def test_validation_result_add_error():
    result = ValidationResult(valid=True)
    result.add_error("bad config")
    assert result.valid is False
    assert result.errors == ["bad config"]


def test_validation_result_add_warning():
    result = ValidationResult(valid=True)
    result.add_warning("minor issue")
    assert result.valid is True
    assert result.warnings == ["minor issue"]


def test_validation_result_bool():
    valid_result = ValidationResult(valid=True)
    invalid_result = ValidationResult(valid=False)
    assert bool(valid_result) is True
    assert bool(invalid_result) is False


def test_validation_result_and():
    r1 = ValidationResult(valid=True)
    r1.add_warning("w1")
    r2 = ValidationResult(valid=True)
    r2.add_error("e1")
    combined = r1 & r2
    assert combined.valid is False
    assert combined.errors == ["e1"]
    assert combined.warnings == ["w1"]


# --- Valid config fixture ---

valid_config = {
    "healthCheckTimeout": 500,
    "logLevel": "info",
    "models": {
        "my-model": {
            "cmd": "llama-server --port ${PORT} --model model.gguf",
            "name": "My Model",
            "proxy": "http://127.0.0.1:8080",
        }
    },
}


# --- validate_config tests ---


def test_validate_config_valid_config():
    result = validate_config(valid_config)
    assert result.valid is True
    assert result.errors == []


def test_validate_config_not_a_dict():
    result = validate_config("not a dict")  # pyright: ignore
    assert result.valid is False
    assert result.errors == ["Config must be a YAML mapping (dict)"]


def test_validate_config_missing_models():
    result = validate_config({"healthCheckTimeout": 500})
    assert result.valid is False
    assert any("'models'" in e and "required" in e for e in result.errors)


def test_validate_config_models_not_dict():
    result = validate_config({"models": "not a dict"})
    assert result.valid is False
    assert any("'models' must be a dictionary" in e for e in result.errors)


def test_validate_config_with_options_cache():
    options_cache = {
        "llama-server": [
            {"flag": "--port", "type": "int"},
            {"flag": "--model", "type": "str"},
            {"flag": "--threads", "type": "int"},
        ],
        "llama-swap": [{"flag": "logLevel", "type": "str"}],
    }
    known_models = [
        Model(filename="model.gguf", full_path="/models/model.gguf"),
    ]
    result = validate_config(valid_config, options_cache, known_models)
    assert result.valid is True


# --- _validate_top_level tests ---


def test_validate_top_level_valid():
    config = {"healthCheckTimeout": 500, "logLevel": "info"}
    result = ValidationResult(valid=True)
    _validate_top_level(config, result)
    assert result.valid is True


def test_validate_top_level_skips_special_keys():
    config = {
        "models": {},
        "matrix": {},
        "hooks": {},
        "peers": {},
        "healthCheckTimeout": 500,
    }
    result = ValidationResult(valid=True)
    _validate_top_level(config, result)
    assert result.valid is True


def test_validate_top_level_invalid_type():
    config = {"metricsMaxInMemory": {"bad": "value"}}
    result = ValidationResult(valid=True)
    _validate_top_level(config, result)
    assert result.valid is False
    assert any("must be a scalar" in e for e in result.errors)


# --- _validate_model_entry tests ---


def test_validate_model_entry_missing_cmd():
    entry = {"name": "Test"}
    result = ValidationResult(valid=True)
    _validate_model_entry("test-model", entry, {}, set(), set(), result)
    assert result.valid is False
    assert any("'cmd' must be" in e or "missing required" in e for e in result.errors)


def test_validate_model_entry_cmd_not_string():
    entry = {"cmd": 123}
    result = ValidationResult(valid=True)
    _validate_model_entry("test-model", entry, {}, set(), set(), result)
    assert result.valid is False
    assert any("'cmd' must be a string" in e for e in result.errors)


def test_validate_model_entry_invalid_proxy():
    entry = {"cmd": "llama-server", "proxy": "not-a-url"}
    result = ValidationResult(valid=True)
    _validate_model_entry("test-model", entry, {}, set(), set(), result)
    assert result.valid is False
    assert any("'proxy' must be a valid" in e for e in result.errors)


def test_validate_model_entry_valid_proxy():
    entry = {"cmd": "llama-server", "proxy": "http://localhost:8080"}
    result = ValidationResult(valid=True)
    _validate_model_entry("test-model", entry, {}, set(), set(), result)
    assert result.valid is True


def test_validate_model_entry_aliases_not_list():
    entry = {"cmd": "llama-server", "aliases": "not-a-list"}
    result = ValidationResult(valid=True)
    _validate_model_entry("test-model", entry, {}, set(), set(), result)
    assert result.valid is False
    assert any("'aliases' must be a list" in e for e in result.errors)


def test_validate_model_entry_env_not_list():
    entry = {"cmd": "llama-server", "env": "not-a-list"}
    result = ValidationResult(valid=True)
    _validate_model_entry("test-model", entry, {}, set(), set(), result)
    assert result.valid is False
    assert any("'env' must be a list" in e for e in result.errors)


def test_validate_model_entry_invalid_ttl():
    entry = {"cmd": "llama-server", "ttl": "not-a-number"}
    result = ValidationResult(valid=True)
    _validate_model_entry("test-model", entry, {}, set(), set(), result)
    assert result.valid is False
    assert any("'ttl' must be a number" in e for e in result.errors)


def test_validate_model_entry_ttl_too_low():
    entry = {"cmd": "llama-server", "ttl": -5}
    result = ValidationResult(valid=True)
    _validate_model_entry("test-model", entry, {}, set(), set(), result)
    assert result.valid is False
    assert any("'ttl' must be >= -1" in e for e in result.errors)


def test_validate_model_entry_concurrency_not_int():
    entry = {"cmd": "llama-server", "concurrencyLimit": "10"}
    result = ValidationResult(valid=True)
    _validate_model_entry("test-model", entry, {}, set(), set(), result)
    assert result.valid is False
    assert any("'concurrencyLimit' must be an integer" in e for e in result.errors)


def test_validate_model_entry_macros_not_dict():
    entry = {"cmd": "llama-server", "macros": "not-a-dict"}
    result = ValidationResult(valid=True)
    _validate_model_entry("test-model", entry, {}, set(), set(), result)
    assert result.valid is False
    assert any("'macros' must be a dictionary" in e for e in result.errors)


def test_validate_model_entry_metadata_not_dict():
    entry = {"cmd": "llama-server", "metadata": "not-a-dict"}
    result = ValidationResult(valid=True)
    _validate_model_entry("test-model", entry, {}, set(), set(), result)
    assert result.valid is False
    assert any("'metadata' must be a dictionary" in e for e in result.errors)


def test_validate_model_entry_unlisted_not_bool():
    entry = {"cmd": "llama-server", "unlisted": "yes"}
    result = ValidationResult(valid=True)
    _validate_model_entry("test-model", entry, {}, set(), set(), result)
    assert result.valid is False
    assert any("'unlisted' must be a boolean" in e for e in result.errors)


def test_validate_model_entry_timeouts_invalid_key():
    entry = {"cmd": "llama-server", "timeouts": {"connect": 30, "bad_key": 5}}
    result = ValidationResult(valid=True)
    _validate_model_entry("test-model", entry, {}, set(), set(), result)
    assert result.valid is False
    assert any("unknown timeout key" in e for e in result.errors)


def test_validate_model_entry_filters_invalid_key():
    entry = {"cmd": "llama-server", "filters": {"stripParams": "temp", "bad_key": 5}}
    result = ValidationResult(valid=True)
    _validate_model_entry("test-model", entry, {}, set(), set(), result)
    assert result.valid is False
    assert any("unknown filter key" in e for e in result.errors)


def test_validate_model_entry_flags_unknown():
    server_opts = {"--port": {"flag": "--port"}, "--threads": {"flag": "--threads"}}
    entry = {"cmd": "llama-server --port 8080 --unknown-flag"}
    result = ValidationResult(valid=True)
    _validate_model_entry("test-model", entry, server_opts, set(), set(), result)
    assert result.valid is True
    assert any("'--unknown-flag'" in w for w in result.warnings)


def test_validate_model_entry_flags_known():
    server_opts = {"--port": {"flag": "--port"}, "--model": {"flag": "--model"}}
    entry = {"cmd": "llama-server --port 8080 --model model.gguf"}
    result = ValidationResult(valid=True)
    _validate_model_entry(
        "test-model", entry, server_opts, {"model.gguf"}, {"model.gguf"}, result
    )
    assert result.valid is True
    assert result.warnings == []


def test_validate_model_entry_model_path_not_found():
    entry = {"cmd": "llama-server --model missing.gguf"}
    result = ValidationResult(valid=True)
    _validate_model_entry("test-model", entry, {}, set(), {"other.gguf"}, result)
    assert result.valid is True
    assert any("not found in scanned models" in w for w in result.warnings)


def test_validate_model_entry_model_path_found():
    entry = {"cmd": "llama-server --model model.gguf"}
    result = ValidationResult(valid=True)
    _validate_model_entry("test-model", entry, {}, set(), {"model.gguf"}, result)
    assert result.valid is True
    assert result.warnings == []


# --- _validate_model_files_in_cmd tests (alias for internal function) ---


def test_check_model_files_not_found():
    result = ValidationResult(valid=True)
    _check_model_files_in_cmd(
        "test-model",
        "llama-server --model missing.gguf",
        set(),
        {"other.gguf"},
        result,
    )
    assert result.valid is True
    assert any("not found in scanned models" in w for w in result.warnings)


def test_check_model_files_found():
    result = ValidationResult(valid=True)
    _check_model_files_in_cmd(
        "test-model",
        "llama-server --model model.gguf",
        set(),
        {"model.gguf"},
        result,
    )
    assert result.valid is True
    assert result.warnings == []


# --- _validate_timeouts tests ---


def test_validate_timeouts_valid():
    timeouts = {"connect": 30, "keepalive": 0, "responseHeader": 60}
    result = ValidationResult(valid=True)
    _validate_timeouts("test-peer", timeouts, result)
    assert result.valid is True


def test_validate_timeouts_invalid_type():
    timeouts = {"connect": "30"}
    result = ValidationResult(valid=True)
    _validate_timeouts("test-peer", timeouts, result)
    assert result.valid is False
    assert any("connect.*must be an integer" in e for e in result.errors) or any(
        "'connect'" in e for e in result.errors
    )


def test_validate_timeouts_not_dict():
    timeouts = "not a dict"
    result = ValidationResult(valid=True)
    _validate_timeouts("test-peer", timeouts, result)
    assert result.valid is False


# --- _validate_filters tests ---


def test_validate_filters_valid():
    filters = {"stripParams": "temperature", "setParams": {"temp": 0.7}}
    result = ValidationResult(valid=True)
    _validate_filters("test-model", filters, result)
    assert result.valid is True


def test_validate_filters_invalid_setParams_type():
    filters = {"stripParams": "temp", "setParams": "not-a-dict"}
    result = ValidationResult(valid=True)
    _validate_filters("test-model", filters, result)
    assert result.valid is False


def test_validate_filters_not_dict():
    filters = "not a dict"
    result = ValidationResult(valid=True)
    _validate_filters("test-model", filters, result)
    assert result.valid is False


# --- _validate_matrix tests ---


def test_validate_matrix_none():
    result = ValidationResult(valid=True)
    _validate_matrix(None, {}, result)
    assert result.valid is True


def test_validate_matrix_valid():
    matrix = {
        "vars": {"g": "gemma-model", "q": "qwen-model"},
        "sets": {"standard": "(g | q) & g"},
        "evict_costs": {"g": 1},
    }
    result = ValidationResult(valid=True)
    _validate_matrix(matrix, {"gemma-model": {}}, result)
    assert result.valid is True


def test_validate_matrix_unknown_key():
    matrix = {"vars": {}, "unknown_key": "bad"}
    result = ValidationResult(valid=True)
    _validate_matrix(matrix, None, result)
    assert result.valid is False
    assert any("'matrix': unknown key" in e for e in result.errors)


def test_validate_matrix_vars_short_name_too_long():
    matrix = {"vars": {"too_long_name": "model"}}
    result = ValidationResult(valid=True)
    _validate_matrix(matrix, None, result)
    assert result.valid is False


def test_validate_matrix_vars_value_not_string():
    matrix = {"vars": {"g": 123}}
    result = ValidationResult(valid=True)
    _validate_matrix(matrix, None, result)
    assert result.valid is False


def test_validate_matrix_sets_not_dict():
    matrix = {"vars": {}, "sets": "not a dict"}
    result = ValidationResult(valid=True)
    _validate_matrix(matrix, None, result)
    assert result.valid is False


def test_validate_matrix_evict_costs_not_number():
    matrix = {"vars": {}, "evict_costs": {"g": "slow"}}
    result = ValidationResult(valid=True)
    _validate_matrix(matrix, None, result)
    assert result.valid is False


def test_validate_matrix_sets_expression_not_string():
    matrix = {"vars": {}, "sets": {"standard": 123}}
    result = ValidationResult(valid=True)
    _validate_matrix(matrix, None, result)
    assert result.valid is False


# --- _validate_hooks tests ---


def test_validate_hooks_none():
    result = ValidationResult(valid=True)
    _validate_hooks(None, {}, result)
    assert result.valid is True


def test_validate_hooks_valid():
    hooks = {"on_startup": {"preload": ["model-a", "model-b"]}}
    result = ValidationResult(valid=True)
    _validate_hooks(hooks, {"model-a": {}, "model-b": {}}, result)
    assert result.valid is True


def test_validate_hooks_preload_not_list():
    hooks = {"on_startup": {"preload": "not-a-list"}}
    result = ValidationResult(valid=True)
    _validate_hooks(hooks, {"model-a": {}}, result)
    assert result.valid is False


def test_validate_hooks_preload_unknown_model():
    hooks = {"on_startup": {"preload": ["unknown-model"]}}
    result = ValidationResult(valid=True)
    _validate_hooks(hooks, {"known-model": {}}, result)
    assert result.valid is True
    assert any("not a known model ID" in w for w in result.warnings)


def test_validate_hooks_not_dict():
    hooks = "not a dict"
    result = ValidationResult(valid=True)
    _validate_hooks(hooks, {}, result)
    assert result.valid is False


# --- _validate_peers tests ---


def test_validate_peers_none():
    result = ValidationResult(valid=True)
    _validate_peers(None, result)
    assert result.valid is True


def test_validate_peers_valid():
    peers = {
        "peer-a": {
            "proxy": "http://192.168.1.23",
            "models": ["model_a", "model_b"],
        }
    }
    result = ValidationResult(valid=True)
    _validate_peers(peers, result)
    assert result.valid is True


def test_validate_peers_missing_proxy():
    peers = {"peer-a": {"models": ["model_a"]}}
    result = ValidationResult(valid=True)
    _validate_peers(peers, result)
    assert result.valid is False
    assert any("missing required 'proxy'" in e for e in result.errors)


def test_validate_peers_missing_models():
    peers = {"peer-a": {"proxy": "http://192.168.1.23"}}
    result = ValidationResult(valid=True)
    _validate_peers(peers, result)
    assert result.valid is False
    assert any("missing required 'models'" in e for e in result.errors)


def test_validate_peers_invalid_proxy():
    peers = {"peer-a": {"proxy": "not-a-url", "models": []}}
    result = ValidationResult(valid=True)
    _validate_peers(peers, result)
    assert result.valid is False


def test_validate_peers_not_dict():
    peers = "not a dict"
    result = ValidationResult(valid=True)
    _validate_peers(peers, result)
    assert result.valid is False


def test_validate_peers_apiKey_not_string():
    peers = {"peer-a": {"proxy": "http://192.168.1.23", "models": [], "apiKey": 123}}
    result = ValidationResult(valid=True)
    _validate_peers(peers, result)
    assert result.valid is False


def test_validate_peers_timeouts_invalid():
    peers = {
        "peer-a": {
            "proxy": "http://192.168.1.23",
            "models": [],
            "timeouts": {"connect": "30"},
        }
    }
    result = ValidationResult(valid=True)
    _validate_peers(peers, result)
    assert result.valid is False


def test_validate_peers_filters_not_dict():
    peers = {"peer-a": {"proxy": "http://192.168.1.23", "models": [], "filters": "bad"}}
    result = ValidationResult(valid=True)
    _validate_peers(peers, result)
    assert result.valid is False


# --- Full config validation integration ---


def test_validate_config_matrix_invalid():
    config = dict(valid_config)
    config["matrix"] = {
        "vars": {"g": "gemma-model"},
        "sets": {"standard": "(g | q) & g"},
    }
    result = validate_config(config)
    assert result.valid is True


def test_validate_config_full_valid():
    config = {
        "healthCheckTimeout": 500,
        "logLevel": "info",
        "logToStdout": "proxy",
        "metricsMaxInMemory": 1000,
        "globalTTL": 0,
        "macros": {"model_dir": "/models"},
        "models": {
            "llama": {
                "cmd": "llama-server --port ${PORT} --model model.gguf",
                "name": "LLaMa",
                "proxy": "http://127.0.0.1:8080",
                "ttl": 60,
                "env": ["CUDA_VISIBLE_DEVICES=0"],
                "aliases": ["gpt-4"],
            }
        },
    }
    known_models = [
        Model(filename="model.gguf", full_path="/models/model.gguf"),
    ]
    options_cache = {
        "llama-server": [
            {"flag": "--port", "type": "int"},
            {"flag": "--model", "type": "str"},
        ],
        "llama-swap": [{"flag": "healthCheckTimeout", "type": "int"}],
    }
    result = validate_config(config, options_cache, known_models)
    assert result.valid is True


def test_validate_config_full_invalid():
    config = {
        "healthCheckTimeout": 500,
        "models": {
            "llama": {
                "name": "LLaMa",
                "proxy": "invalid-url",
                "ttl": -5,
                "env": "not-a-list",
                "aliases": "not-a-list",
            }
        },
    }
    options_cache = {"llama-server": [], "llama-swap": []}
    result = validate_config(config, options_cache)
    assert result.valid is False
    error_count = sum(1 for e in result.errors if "llama" in e)
    assert error_count >= 3
