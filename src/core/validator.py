import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.core.model import Model

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.valid = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def __bool__(self) -> bool:
        return self.valid

    def __and__(self, other: "ValidationResult") -> "ValidationResult":
        combined = ValidationResult(valid=(self.valid and other.valid))
        combined.errors = self.errors + other.errors
        combined.warnings = self.warnings + other.warnings
        return combined


def _type_check(value: Any, expected_type: str, path: str) -> bool:
    type_map = {
        "str": str,
        "int": int,
        "float": (int, float),
        "bool": bool,
        "list": list,
        "dict": dict,
    }
    if expected_type not in type_map:
        return True
    expected = type_map[expected_type]
    if not isinstance(value, expected):
        return False
    if expected_type == "int" and isinstance(value, bool):
        return False
    return True


def validate_config(
    config_dict: dict[str, Any],
    options_cache: dict[str, list[dict[str, Any]]] | None = None,
    known_models: list[Model] | None = None,
) -> ValidationResult:
    result = ValidationResult(valid=True)

    if not isinstance(config_dict, dict):
        result.add_error("Config must be a YAML mapping (dict)")
        return result

    errors_before = len(result.errors)

    # Validate top-level llama-swap config keys
    _validate_top_level(config_dict, result)

    # Validate models section (required)
    _validate_models(config_dict.get("models"), result, options_cache, known_models)

    # Validate matrix section
    _validate_matrix(config_dict.get("matrix"), config_dict.get("models"), result)

    # Validate hooks section
    _validate_hooks(config_dict.get("hooks"), config_dict.get("models"), result)

    # Validate peers section
    _validate_peers(config_dict.get("peers"), result)

    if errors_before != len(result.errors):
        logger.warning("Validation found %d errors", len(result.errors))

    return result


def _validate_top_level(config: dict[str, Any], result: ValidationResult) -> None:
    for key in config:
        if key in ("models", "matrix", "hooks", "peers", "macros"):
            continue
        value = config[key]
        if value is not None and not isinstance(value, (str, int, bool, float)):
            result.add_error(f"'{key}' must be a scalar value (str, int, bool, float)")


def _validate_models(
    models: Any,
    result: ValidationResult,
    options_cache: dict[str, list[dict[str, Any]]] | None,
    known_models: list[Model] | None,
) -> None:
    if models is None:
        result.add_error("Missing required 'models' section")
        return
    if not isinstance(models, dict):
        result.add_error("'models' must be a dictionary of model configurations")
        return

    model_ids = list(models.keys())
    known_paths = set()
    known_filenames = set()
    if known_models:
        known_paths = {m.full_path for m in known_models if m.full_path}
        known_filenames = {m.filename for m in known_models if m.filename}

    server_opts = {}
    swap_opts = {}
    if options_cache:
        for opt in options_cache.get("llama-server", []):
            if opt.get("flag"):
                server_opts[opt["flag"]] = opt
        for opt in options_cache.get("llama-swap", []):
            if opt.get("flag"):
                swap_opts[opt["flag"]] = opt

    for model_id, entry in models.items():
        if not isinstance(entry, dict):
            result.add_error(f"Model '{model_id}' must be a mapping")
            continue
        _validate_model_entry(
            model_id, entry, server_opts, known_paths, known_filenames, result
        )


def _validate_model_entry(
    model_id: str,
    entry: dict[str, Any],
    server_opts: dict[str, Any],
    known_paths: set[str],
    known_filenames: set[str],
    result: ValidationResult,
) -> None:
    # cmd is required
    if "cmd" not in entry:
        result.add_error(f"Model '{model_id}': missing required 'cmd' field")
    elif not isinstance(entry["cmd"], str):
        result.add_error(f"Model '{model_id}': 'cmd' must be a string")

    # Check model file paths from cmd
    if "cmd" in entry and isinstance(entry["cmd"], str):
        _check_model_files_in_cmd(
            model_id, entry["cmd"], known_paths, known_filenames, result
        )

    # Optional fields validation
    if "name" in entry and not isinstance(entry["name"], str):
        result.add_error(f"Model '{model_id}': 'name' must be a string")

    if "description" in entry and not isinstance(entry["description"], str):
        result.add_error(f"Model '{model_id}': 'description' must be a string")

    if "proxy" in entry:
        if not isinstance(entry["proxy"], str):
            result.add_error(f"Model '{model_id}': 'proxy' must be a string URL")
        elif not re.match(r"https?://", entry["proxy"]):
            result.add_error(
                f"Model '{model_id}': 'proxy' must be a valid http/https URL"
            )

    if "checkEndpoint" in entry and not isinstance(entry["checkEndpoint"], str):
        result.add_error(f"Model '{model_id}': 'checkEndpoint' must be a string")

    # ttl validation
    if "ttl" in entry:
        ttl = entry["ttl"]
        if not isinstance(ttl, (int, float)) or isinstance(ttl, bool):
            result.add_error(f"Model '{model_id}': 'ttl' must be a number")
        elif ttl < -1:
            result.add_error(f"Model '{model_id}': 'ttl' must be >= -1")

    # globalTTL override
    if "globalTTL" in entry:
        global_ttl = entry["globalTTL"]
        if not isinstance(global_ttl, int) or isinstance(global_ttl, bool):
            result.add_error(f"Model '{model_id}': 'globalTTL' must be an integer")
        elif global_ttl < 0:
            result.add_error(f"Model '{model_id}': 'globalTTL' must be >= 0")

    # aliases validation
    if "aliases" in entry:
        aliases = entry["aliases"]
        if not isinstance(aliases, list):
            result.add_error(f"Model '{model_id}': 'aliases' must be a list")
        elif aliases:
            for a in aliases:
                if not isinstance(a, str) or not a.strip():
                    result.add_error(
                        f"Model '{model_id}': alias entries must be non-empty strings"
                    )

    # env validation
    if "env" in entry:
        env = entry["env"]
        if not isinstance(env, list):
            result.add_error(f"Model '{model_id}': 'env' must be a list of strings")
        elif env:
            for e in env:
                if not isinstance(e, str):
                    result.add_error(f"Model '{model_id}': env entries must be strings")

    # macros validation
    if "macros" in entry:
        macros = entry["macros"]
        if not isinstance(macros, dict):
            result.add_error(f"Model '{model_id}': 'macros' must be a dictionary")

    # metadata validation
    if "metadata" in entry:
        metadata = entry["metadata"]
        if not isinstance(metadata, dict):
            result.add_error(f"Model '{model_id}': 'metadata' must be a dictionary")

    # concurrencyLimit validation
    if "concurrencyLimit" in entry:
        cl = entry["concurrencyLimit"]
        if not isinstance(cl, int) or isinstance(cl, bool):
            result.add_error(
                f"Model '{model_id}': 'concurrencyLimit' must be an integer"
            )

    # unlisted validation
    if "unlisted" in entry:
        if not isinstance(entry["unlisted"], bool):
            result.add_error(f"Model '{model_id}': 'unlisted' must be a boolean")

    # sendLoadingState validation
    if "sendLoadingState" in entry:
        if not isinstance(entry["sendLoadingState"], bool):
            result.add_error(
                f"Model '{model_id}': 'sendLoadingState' must be a boolean"
            )

    # useModelName validation
    if "useModelName" in entry:
        if not isinstance(entry["useModelName"], str):
            result.add_error(f"Model '{model_id}': 'useModelName' must be a string")

    # cmdStop validation
    if "cmdStop" in entry:
        if not isinstance(entry["cmdStop"], str):
            result.add_error(f"Model '{model_id}': 'cmdStop' must be a string")

    # timeouts validation
    if "timeouts" in entry:
        _validate_timeouts(model_id, entry["timeouts"], result)

    # filters validation
    if "filters" in entry:
        _validate_filters(model_id, entry["filters"], result)

    # Validate llama-server flags in cmd against options cache
    _validate_flags_in_cmd(model_id, entry.get("cmd"), server_opts, result)


def _check_model_files_in_cmd(
    model_id: str,
    cmd: str,
    known_paths: set[str],
    known_filenames: set[str],
    result: ValidationResult,
) -> None:
    gguf_pattern = re.compile(r'--model\s+[\'"]?([^\s\'"]+\.gguf)[\'"]?')
    matches = gguf_pattern.findall(cmd)
    for match in matches:
        basename = Path(match).name
        if basename not in known_filenames and match not in known_paths:
            result.add_warning(
                f"Model '{model_id}': referenced model file '{basename}' "
                f"not found in scanned models"
            )


def _validate_flags_in_cmd(
    model_id: str,
    cmd: str | None,
    server_opts: dict[str, Any],
    result: ValidationResult,
) -> None:
    if not cmd or not server_opts:
        return
    flag_pattern = re.compile(r"(?:^|\s|--|-)(-{1,2})(\w[\w\-]*)")
    found_flags = set()
    for match in flag_pattern.finditer(cmd):
        prefix = match.group(1)
        name = match.group(2)
        if prefix == "--":
            found_flags.add(f"--{name}")
        elif prefix == "-":
            found_flags.add(f"-{name}")

    unknown_flags = found_flags - set(server_opts.keys()) - {"--model"}
    for flag in sorted(unknown_flags):
        result.add_warning(
            f"Model '{model_id}': unknown flag '{flag}' not found in "
            f"llama-server options cache"
        )


def _validate_timeouts(model_id: str, timeouts: Any, result: ValidationResult) -> None:
    valid_timeout_keys = {
        "connect",
        "keepalive",
        "responseHeader",
        "tlsHandshake",
        "idleConn",
    }
    if not isinstance(timeouts, dict):
        result.add_error(f"Model '{model_id}': 'timeouts' must be a dictionary")
        return
    for key in timeouts:
        if key not in valid_timeout_keys:
            result.add_error(f"Model '{model_id}': unknown timeout key '{key}'")
    value = timeouts
    for k, v in value.items():
        if not isinstance(v, int) or isinstance(v, bool):
            result.add_error(f"Model '{model_id}': timeout '{k}' must be an integer")


def _validate_filters(model_id: str, filters: Any, result: ValidationResult) -> None:
    valid_filter_keys = {"stripParams", "setParams", "setParamsByID"}
    if not isinstance(filters, dict):
        result.add_error(f"Model '{model_id}': 'filters' must be a dictionary")
        return
    for key in filters:
        if key not in valid_filter_keys:
            result.add_error(f"Model '{model_id}': unknown filter key '{key}'")
    if "setParams" in filters and not isinstance(filters["setParams"], dict):
        result.add_error(f"Model '{model_id}': 'setParams' must be a dictionary")
    if "setParamsByID" in filters and not isinstance(filters["setParamsByID"], dict):
        result.add_error(f"Model '{model_id}': 'setParamsByID' must be a dictionary")


def _validate_matrix(matrix: Any, models: Any, result: ValidationResult) -> None:
    if matrix is None:
        return
    if not isinstance(matrix, dict):
        result.add_error("'matrix' must be a dictionary")
        return

    valid_matrix_keys = {"vars", "evict_costs", "sets"}
    for key in matrix:
        if key not in valid_matrix_keys:
            result.add_error(f"'matrix': unknown key '{key}'")

    # vars: maps short name -> model ID
    vars_map = matrix.get("vars")
    if vars_map is not None:
        if not isinstance(vars_map, dict):
            result.add_error("'matrix.vars' must be a dictionary")
        else:
            for short_name, model_ref in vars_map.items():
                if not isinstance(short_name, str) or len(short_name) > 8:
                    result.add_error(
                        f"'matrix.vars': key '{short_name}' must be 8 chars or fewer"
                    )
                if not isinstance(model_ref, str):
                    result.add_error(
                        f"'matrix.vars': value for '{short_name}' must be a model ID string"
                    )

    # sets: must be dict with string values
    sets = matrix.get("sets")
    if sets is not None:
        if not isinstance(sets, dict):
            result.add_error("'matrix.sets' must be a dictionary")
        else:
            for set_name, expression in sets.items():
                if not isinstance(expression, str):
                    result.add_error(
                        f"'matrix.sets.{set_name}' must be a string expression"
                    )

    # evict_costs: dict of name -> number
    evict_costs = matrix.get("evict_costs")
    if evict_costs is not None:
        if not isinstance(evict_costs, dict):
            result.add_error("'matrix.evict_costs' must be a dictionary")
        else:
            for name, cost in evict_costs.items():
                if not isinstance(cost, (int, float)) or isinstance(cost, bool):
                    result.add_error(f"'matrix.evict_costs.{name}' must be a number")


def _validate_hooks(hooks: Any, models: Any, result: ValidationResult) -> None:
    if hooks is None:
        return
    if not isinstance(hooks, dict):
        result.add_error("'hooks' must be a dictionary")
        return

    if "on_startup" in hooks:
        on_startup = hooks["on_startup"]
        if not isinstance(on_startup, dict):
            result.add_error("'hooks.on_startup' must be a dictionary")
        else:
            preload = on_startup.get("preload")
            if preload is not None:
                if not isinstance(preload, list):
                    result.add_error("'hooks.on_startup.preload' must be a list")
                elif models and isinstance(models, dict):
                    valid_ids = set(models.keys())
                    for item in preload:
                        if not isinstance(item, str):
                            result.add_error(
                                f"'hooks.on_startup.preload' entries must be strings"
                            )
                        elif item not in valid_ids:
                            result.add_warning(
                                f"'hooks.on_startup.preload': '{item}' is not a "
                                f"known model ID"
                            )


def _validate_peers(peers: Any, result: ValidationResult) -> None:
    if peers is None:
        return
    if not isinstance(peers, dict):
        result.add_error("'peers' must be a dictionary")
        return

    for peer_id, peer_conf in peers.items():
        if not isinstance(peer_conf, dict):
            result.add_error(f"Peer '{peer_id}' must be a dictionary")
            continue

        if "proxy" not in peer_conf:
            result.add_error(f"Peer '{peer_id}': missing required 'proxy' field")
        elif not isinstance(peer_conf["proxy"], str):
            result.add_error(f"Peer '{peer_id}': 'proxy' must be a string URL")
        elif not re.match(r"https?://", peer_conf["proxy"]):
            result.add_error(
                f"Peer '{peer_id}': 'proxy' must be a valid http/https URL"
            )

        if "models" not in peer_conf:
            result.add_error(f"Peer '{peer_id}': missing required 'models' field")
        elif not isinstance(peer_conf["models"], list):
            result.add_error(f"Peer '{peer_id}': 'models' must be a list")

        if "apiKey" in peer_conf:
            if not isinstance(peer_conf["apiKey"], str):
                result.add_error(f"Peer '{peer_id}': 'apiKey' must be a string")

        if "timeouts" in peer_conf:
            _validate_timeouts(peer_id, peer_conf["timeouts"], result)

        if "filters" in peer_conf:
            if not isinstance(peer_conf["filters"], dict):
                result.add_error(f"Peer '{peer_id}': 'filters' must be a dictionary")
