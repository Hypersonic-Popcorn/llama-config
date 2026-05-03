import json
import re
from pathlib import Path
from typing import Any

from src.settings import settings


def parse_server_markdown(md_path: str | Path) -> list[dict[str, Any]]:
    path = Path(md_path)
    try:
        lines = path.read_text().splitlines()
    except (OSError, FileNotFoundError):
        return []

    options: list[dict[str, Any]] = []
    in_table = False
    header_found = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("#"):
            if stripped.lower().endswith("params"):
                in_table = True
                header_found = False
                continue

        if in_table:
            if stripped.startswith("| "):
                inner = stripped.strip("| ")
                # Find the first pipe surrounded by spaces (the column separator)
                sep_idx = inner.find(" | ")
                if sep_idx == -1:
                    continue

                arg_raw = inner[:sep_idx].strip()
                explanation_raw = inner[sep_idx + 3 :].strip()

                if not header_found:
                    if arg_raw == "Argument" and explanation_raw == "Explanation":
                        header_found = True
                    continue

                if arg_raw.startswith("-") and explanation_raw.startswith("-"):
                    continue

                arg = arg_raw.strip("`")
                explanation = explanation_raw.strip("`")
                option = _parse_server_option(arg, explanation)
                if option is not None:
                    options.append(option)
            elif stripped and not stripped.startswith("|"):
                in_table = False

    return options


def _parse_server_option(arg: str, explanation: str) -> dict[str, Any] | None:
    is_flag = False
    default: str | int | float | bool | None = None
    env_var: str | None = None
    valid_values: list[str] | None = None

    args = explanation.lower()

    if (
        "default: enabled" in args
        or "default: false" in args
        or "default: true" in args
    ):
        is_flag = True
    elif "default:" in args:
        default_match = re.search(r"default:\s+([^)]+)", explanation)
        if default_match:
            default = _parse_default(default_match.group(1))

    if "enabled" in args or "disabled" in args:
        if "allowed values:" in args:
            val_match = re.search(r"allowed values:\s+([^\)]+)", args)
            if val_match:
                valid_values = [v.strip() for v in val_match.group(1).split(",")]
            else:
                valid_values = ["enabled", "disabled"]
        else:
            valid_values = ["enabled", "disabled"]

    env_match = re.search(r"\(env:\s+([^)]+)\)", explanation)
    if env_match:
        env_var = env_match.group(1)

    clean_explanation = re.sub(r"<br/?>", "", explanation)
    clean_explanation = re.sub(r"\s+", " ", clean_explanation).strip()
    clean_explanation = clean_explanation.strip("()")

    # Extract valid_values from bracketed type hint like [on\|off\|auto]
    if valid_values is None and "[" in arg:
        bracket_match = re.search(r"\[(.*?)\]", arg)
        if bracket_match:
            raw = bracket_match.group(1)
            valid_values = [
                v.strip().strip("\\").strip("'") for v in raw.split("\\|") if v.strip()
            ]

    short = None
    long_flag = None

    parts = [p.strip() for p in arg.split(",")]
    for part in parts:
        part = part.strip()
        flag_part = re.sub(r"\s+\[.*\]", "", part)
        flag_part = re.sub(r"\s+[A-Z]+\.?[A-Z]*$", "", flag_part)
        if flag_part.startswith("--") and long_flag is None:
            long_flag = flag_part
        if (
            flag_part.startswith("-")
            and not flag_part.startswith("--")
            and short is None
        ):
            short = flag_part

    if long_flag is None and short:
        long_name = short.lstrip("-").replace("-", "_")
        long_flag = f"--{long_name}"

    flag_type = "str"
    if is_flag:
        flag_type = "bool"
    elif "fname" in arg.lower() or "path" in arg.lower():
        flag_type = "file"
    elif "n" in arg.lower():
        if "float" in explanation.lower():
            flag_type = "float"
        else:
            flag_type = "int"

    return {
        "flag": long_flag or (short or ""),
        "short": short,
        "type": flag_type,
        "default": default,
        "description": clean_explanation,
        "valid_values": valid_values,
        "is_flag": is_flag,
        "env_var": env_var,
    }


def _parse_default(value: str) -> str | int | float | bool | None:
    value = value.strip()
    value = value.strip("'\"")

    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if value.lower() == "none":
        return None

    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        pass

    return value


def parse_swap_config_doc(md_path: str | Path) -> list[dict[str, Any]]:
    path = Path(md_path)
    try:
        lines = path.read_text().splitlines()
    except (OSError, FileNotFoundError):
        return []

    config_keys: dict[str, dict[str, Any]] = {}
    current_key: str | None = None

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("# ") and not stripped.startswith("# -"):
            colon = stripped.find(":")
            if colon > 3:
                key_name = stripped[2:colon].strip()
                description = stripped[colon + 1 :].strip().strip("-")
                config_keys[key_name] = {
                    "flag": key_name,
                    "short": None,
                    "type": "str",
                    "default": None,
                    "description": description,
                    "valid_values": None,
                    "is_flag": False,
                    "env_var": None,
                }
                current_key = key_name

        elif current_key and (stripped.startswith("# -") or stripped.startswith("-")):
            option_line = stripped.lstrip("# -")
            desc_lower = option_line.lower()

            if "default:" in desc_lower:
                def_match = re.search(r"default:\s+([^,\n]+)", desc_lower)
                if def_match:
                    config_keys[current_key]["default"] = _parse_default(
                        def_match.group(1)
                    )

            if "valid" in desc_lower and (
                "level" in desc_lower or "values" in desc_lower
            ):
                val_match = re.search(
                    r"(?:valid|levels|values)[^:]*:\s*(.+)",
                    desc_lower,
                )
                if val_match:
                    values = [
                        v.strip().strip('"').strip("'")
                        for v in val_match.group(1).split(",")
                        if v.strip()
                    ]
                    config_keys[current_key]["valid_values"] = values

    return list(config_keys.values())


def build_options_cache() -> dict[str, list[dict[str, Any]]]:
    docs_dir = settings.docs_dir

    server_opts: list[dict[str, Any]] = []
    swap_opts: list[dict[str, Any]] = []

    server_md = docs_dir / "server.md"
    if server_md.exists():
        server_opts = parse_server_markdown(server_md)

    swap_md = docs_dir / "swap.md"
    if swap_md.exists():
        swap_opts = parse_swap_config_doc(swap_md)

    cache = {"llama-server": server_opts, "llama-swap": swap_opts}

    cache_path = settings.backup_dir / "options_cache.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2))

    return cache


def load_options_cache(
    force_rebuild: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    cache_path = settings.backup_dir / "options_cache.json"

    if not force_rebuild and cache_path.exists():
        try:
            content = cache_path.read_text()
            return json.loads(content)
        except (OSError, json.JSONDecodeError):
            pass

    return build_options_cache()
